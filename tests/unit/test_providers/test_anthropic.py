"""Tests for the Anthropic provider.

The constructor/metadata tests mirror the other provider suites. The
``complete``/``stream`` tests inject a fake async client so the request
translation and response parsing are exercised without network access.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from adversarial_debate.providers.base import Message, ModelTier, ProviderConfig

pytest.importorskip("anthropic")

from adversarial_debate.providers.anthropic import AnthropicProvider  # noqa: E402


def _provider() -> AnthropicProvider:
    return AnthropicProvider(ProviderConfig(api_key="test-key"))


class TestMetadata:
    def test_name(self) -> None:
        assert _provider().name == "anthropic"

    def test_supports_streaming(self) -> None:
        assert _provider().supports_streaming is True

    def test_default_model(self) -> None:
        assert _provider()._default_model() == "claude-sonnet-4-20250514"

    def test_model_for_tier(self) -> None:
        provider = _provider()
        assert provider.get_model_for_tier(ModelTier.LOCAL_SMALL) == "claude-3-haiku-20240307"
        assert provider.get_model_for_tier(ModelTier.HOSTED_SMALL) == "claude-3-5-haiku-20241022"
        assert provider.get_model_for_tier(ModelTier.HOSTED_LARGE) == "claude-sonnet-4-20250514"

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        assert AnthropicProvider().config.api_key == "env-key"


class TestImportGuard:
    def test_instantiation_without_package_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import adversarial_debate.providers.anthropic as mod

        monkeypatch.setattr(mod, "HAS_ANTHROPIC", False)
        with pytest.raises(ImportError, match="anthropic package not installed"):
            mod.AnthropicProvider()


class _FakeUsage:
    input_tokens = 11
    output_tokens = 7


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    def __init__(self) -> None:
        self.content = [_FakeBlock("hello "), _FakeBlock("world")]
        self.model = "claude-sonnet-4-20250514"
        self.usage = _FakeUsage()
        self.stop_reason = "end_turn"


class TestComplete:
    async def test_translates_messages_and_parses_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = _provider()
        captured: dict[str, Any] = {}

        async def fake_create(**kwargs: Any) -> _FakeResponse:
            captured.update(kwargs)
            return _FakeResponse()

        # Replace the async messages.create method on the client.
        provider._client.messages = types.SimpleNamespace(create=fake_create)

        response = await provider.complete(
            [
                Message(role="system", content="be terse"),
                Message(role="user", content="hi"),
            ],
            model="claude-test",
            max_tokens=256,
            temperature=0.1,
        )

        # System message is pulled out of the messages list.
        assert captured["system"] == "be terse"
        assert captured["messages"] == [{"role": "user", "content": "hi"}]
        assert captured["model"] == "claude-test"

        # Text blocks are concatenated; usage is mapped through.
        assert response.content == "hello world"
        assert response.usage == {"input_tokens": 11, "output_tokens": 7}
        assert response.finish_reason == "end_turn"


class TestStream:
    async def test_yields_text_then_final_chunk(self) -> None:
        provider = _provider()

        class _FakeStream:
            async def __aenter__(self) -> _FakeStream:
                return self

            async def __aexit__(self, *exc: object) -> None:
                return None

            @property
            async def text_stream(self):  # type: ignore[no-untyped-def]
                for chunk in ("foo", "bar"):
                    yield chunk

            async def get_final_message(self) -> _FakeResponse:
                return _FakeResponse()

        def fake_stream(**kwargs: Any) -> _FakeStream:
            return _FakeStream()

        provider._client.messages = types.SimpleNamespace(stream=fake_stream)

        chunks = [c async for c in provider.stream([Message(role="user", content="go")])]

        text_chunks = [c for c in chunks if not c.is_final]
        final = [c for c in chunks if c.is_final]
        assert [c.content for c in text_chunks] == ["foo", "bar"]
        assert len(final) == 1
        assert final[0].usage == {"input_tokens": 11, "output_tokens": 7}


def test_no_leaked_anthropic_stub() -> None:
    # Guard: ensure we used the real package, not an accidental stub in sys.modules.
    assert not isinstance(sys.modules.get("anthropic"), types.SimpleNamespace)
