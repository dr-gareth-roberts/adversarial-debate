"""Base LLM provider abstraction."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelTier(str, Enum):
    """Model tier for routing decisions.

    Different agents may require different model capabilities:
    - LOCAL_SMALL: Fast, cheap - for normalization, linting, simple classification
    - HOSTED_SMALL: Balanced - for monitoring, routine planning
    - HOSTED_LARGE: Most capable - for deep analysis, strategic synthesis
    """
    LOCAL_SMALL = "local_small"
    HOSTED_SMALL = "hosted_small"
    HOSTED_LARGE = "hosted_large"


@dataclass
class Message:
    """A message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 120.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    usage: dict[str, int]  # input_tokens, output_tokens
    finish_reason: str | None = None
    raw_response: Any = None


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""
    content: str
    is_final: bool = False
    finish_reason: str | None = None
    usage: dict[str, int] | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implement this to add support for new LLM backends (OpenAI, Ollama, etc.)
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'anthropic', 'openai', 'ollama')."""
        ...

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses.

        Override to return True if streaming is implemented.
        """
        return False

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion from the model.

        Args:
            messages: Conversation history
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            json_mode: Request JSON output format

        Returns:
            LLMResponse with generated content
        """
        ...

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion from the model.

        Default implementation falls back to non-streaming complete().
        Override in subclasses for true streaming support.

        Args:
            messages: Conversation history
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Yields:
            StreamChunk objects with content fragments
        """
        # Default: fall back to non-streaming
        response = await self.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield StreamChunk(
            content=response.content,
            is_final=True,
            finish_reason=response.finish_reason,
            usage=response.usage,
        )

    @abstractmethod
    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get the appropriate model name for a given tier."""
        ...

    def _resolve_params(
        self,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> tuple[str, float, int]:
        """Resolve parameters with defaults."""
        return (
            model or self.config.model or self._default_model(),
            temperature if temperature is not None else self.config.temperature,
            max_tokens or self.config.max_tokens,
        )

    @abstractmethod
    def _default_model(self) -> str:
        """Default model for this provider."""
        ...
