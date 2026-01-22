"""OpenAI GPT provider implementation."""

import os
from typing import Any

from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider.

    Uses the OpenAI API to access GPT models for security analysis.
    Supports both OpenAI and Azure OpenAI endpoints.
    """

    # Model mapping by tier
    TIER_MODELS = {
        ModelTier.LOCAL_SMALL: "gpt-4o-mini",
        ModelTier.HOSTED_SMALL: "gpt-4o-mini",
        ModelTier.HOSTED_LARGE: "gpt-4o",
    }

    def __init__(self, config: ProviderConfig | None = None):
        if not HAS_OPENAI:
            raise ImportError(
                "openai package not installed. Run: pip install openai"
            )

        config = config or ProviderConfig()
        config.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        super().__init__(config)

        client_kwargs: dict[str, Any] = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout,
        }

        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        self._client = openai.AsyncOpenAI(**client_kwargs)

    @property
    def name(self) -> str:
        return "openai"

    def _default_model(self) -> str:
        return "gpt-4o"

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

        # Convert messages to OpenAI format
        api_messages: list[dict[str, str]] = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Build request
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**request_kwargs)

        # Extract content
        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            finish_reason=response.choices[0].finish_reason,
            raw_response=response,
        )
