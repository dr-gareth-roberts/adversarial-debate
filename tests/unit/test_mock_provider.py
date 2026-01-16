"""Tests for MockProvider."""

from __future__ import annotations

import json

import pytest

from adversarial_debate.providers import Message, MockProvider, get_provider


def test_get_provider_mock() -> None:
    provider = get_provider("mock")
    assert isinstance(provider, MockProvider)


@pytest.mark.anyio
async def test_mock_provider_returns_json() -> None:
    provider = MockProvider()
    messages = [
        Message(role="system", content="You are the Arbiter - the final judge of security and quality findings."),
        Message(role="user", content="**File:** `example.py`"),
    ]
    response = await provider.complete(messages, json_mode=True)
    data = json.loads(response.content)
    assert data["decision"] in {"BLOCK", "WARN", "PASS"}
