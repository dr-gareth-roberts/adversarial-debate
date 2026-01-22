"""Anthropic Claude provider implementation."""

import os
from collections.abc import AsyncIterator
from typing import Any

from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig, StreamChunk

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider.

    Uses the Anthropic API to access Claude models for security analysis.
    """

    # Model mapping by tier
    TIER_MODELS = {
        ModelTier.LOCAL_SMALL: "claude-3-haiku-20240307",
        ModelTier.HOSTED_SMALL: "claude-3-5-haiku-20241022",
        ModelTier.HOSTED_LARGE: "claude-sonnet-4-20250514",
    }

    def __init__(self, config: ProviderConfig | None = None):
        if not HAS_ANTHROPIC:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        config = config or ProviderConfig()
        config.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        super().__init__(config)

        self._client = anthropic.AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
        )

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def supports_streaming(self) -> bool:
        return True

    def _default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    def get_model_for_tier(self, tier: ModelTier) -> str:
        return self.TIER_MODELS.get(tier, self._default_model())

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        model, temperature, max_tokens = self._resolve_params(
            model, temperature, max_tokens
        )

        # Extract system message if present
        system_content: str | None = None
        api_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        # Build request
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_content:
            request_kwargs["system"] = system_content

        response = await self._client.messages.create(**request_kwargs)

        # Extract text content
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
            raw_response=response,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion from Claude.

        Yields content chunks as they arrive from the API.
        """
        model, temperature, max_tokens = self._resolve_params(
            model, temperature, max_tokens
        )

        # Extract system message if present
        system_content: str | None = None
        api_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        # Build request
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_content:
            request_kwargs["system"] = system_content

        async with self._client.messages.stream(**request_kwargs) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(content=text, is_final=False)

            # Get final message for usage stats
            final_message = await stream.get_final_message()
            yield StreamChunk(
                content="",
                is_final=True,
                finish_reason=final_message.stop_reason,
                usage={
                    "input_tokens": final_message.usage.input_tokens,
                    "output_tokens": final_message.usage.output_tokens,
                },
            )
