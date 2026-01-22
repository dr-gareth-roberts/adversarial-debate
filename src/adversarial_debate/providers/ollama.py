"""Ollama provider implementation for local LLM models."""

import os
from typing import Any

import aiohttp

from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM inference.

    Uses the Ollama API to access locally-running models. This enables
    offline security analysis without requiring external API keys.

    Default endpoint: http://localhost:11434
    """

    # Model mapping by tier (using common Ollama models)
    TIER_MODELS = {
        ModelTier.LOCAL_SMALL: "llama3.2:3b",
        ModelTier.HOSTED_SMALL: "llama3.2:3b",
        ModelTier.HOSTED_LARGE: "llama3.1:70b",
    }

    def __init__(self, config: ProviderConfig | None = None):
        config = config or ProviderConfig()
        config.base_url = config.base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        super().__init__(config)

        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def name(self) -> str:
        return "ollama"

    def _default_model(self) -> str:
        return "llama3.1:8b"

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

        # Convert messages to Ollama format
        api_messages: list[dict[str, str]] = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Build request
        request_body: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if json_mode:
            request_body["format"] = "json"

        session = await self._get_session()
        url = f"{self.config.base_url}/api/chat"

        async with session.post(url, json=request_body) as response:
            response.raise_for_status()
            data = await response.json()

        # Extract content
        content = data.get("message", {}).get("content", "")

        # Ollama provides token counts in eval_count and prompt_eval_count
        return LLMResponse(
            content=content,
            model=data.get("model", model),
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
            finish_reason=data.get("done_reason", "stop"),
            raw_response=data,
        )

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models in Ollama.

        Returns:
            List of model info dictionaries with name, size, etc.
        """
        session = await self._get_session()
        url = f"{self.config.base_url}/api/tags"

        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()

        return data.get("models", [])

    async def pull_model(self, model_name: str) -> None:
        """Pull a model from Ollama registry.

        Args:
            model_name: Name of the model to pull (e.g., 'llama3.1:8b')
        """
        session = await self._get_session()
        url = f"{self.config.base_url}/api/pull"

        async with session.post(url, json={"name": model_name, "stream": False}) as response:
            response.raise_for_status()

    async def is_available(self) -> bool:
        """Check if Ollama server is available.

        Returns:
            True if Ollama is running and responding
        """
        try:
            session = await self._get_session()
            url = f"{self.config.base_url}/api/tags"
            async with session.get(url) as response:
                return response.status == 200
        except (aiohttp.ClientError, OSError):
            return False
