"""Azure OpenAI provider implementation."""

import os
from typing import Any

from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider.

    Uses Azure's hosted OpenAI service for enterprise deployments.
    Requires:
    - AZURE_OPENAI_API_KEY: API key for Azure OpenAI
    - AZURE_OPENAI_ENDPOINT: Azure endpoint URL
    - AZURE_OPENAI_DEPLOYMENT: Deployment name (optional, defaults to model name)
    - AZURE_OPENAI_API_VERSION: API version (optional, defaults to 2024-02-01)
    """

    # Model mapping by tier (Azure uses deployment names, but these are common defaults)
    TIER_MODELS = {
        ModelTier.LOCAL_SMALL: "gpt-4o-mini",
        ModelTier.HOSTED_SMALL: "gpt-4o-mini",
        ModelTier.HOSTED_LARGE: "gpt-4o",
    }

    def __init__(self, config: ProviderConfig | None = None):
        try:
            import openai
        except ImportError as err:
            raise ImportError("openai package not installed. Run: pip install openai") from err

        config = config or ProviderConfig()
        config.api_key = config.api_key or os.getenv("AZURE_OPENAI_API_KEY")
        config.base_url = config.base_url or os.getenv("AZURE_OPENAI_ENDPOINT")

        if not config.base_url:
            raise ValueError(
                "Azure OpenAI endpoint required. Set AZURE_OPENAI_ENDPOINT "
                "environment variable or provide base_url in config."
            )

        azure_endpoint = config.base_url
        super().__init__(config)

        # Azure-specific settings from config.extra or environment
        deployment = config.extra.get("deployment")
        if deployment is None:
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        self._deployment = str(deployment) if deployment is not None else None

        api_version = config.extra.get("api_version")
        if api_version is None:
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self._api_version = str(api_version) if api_version is not None else "2024-02-01"

        self._client = openai.AsyncAzureOpenAI(
            api_key=self.config.api_key,
            azure_endpoint=azure_endpoint,
            api_version=self._api_version,
            timeout=self.config.timeout,
        )

    @property
    def name(self) -> str:
        return "azure"

    def _default_model(self) -> str:
        # For Azure, model name is typically the deployment name
        return self._deployment or "gpt-4o"

    def get_model_for_tier(self, tier: ModelTier) -> str:
        # If a specific deployment is set, use it for all tiers
        if self._deployment:
            return self._deployment
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
        model, temperature, max_tokens = self._resolve_params(model, temperature, max_tokens)

        # Convert messages to OpenAI format
        api_messages: list[dict[str, str]] = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        # Build request
        request_kwargs: dict[str, Any] = {
            "model": model,  # In Azure, this is the deployment name
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
