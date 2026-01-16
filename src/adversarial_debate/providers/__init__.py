"""LLM provider abstraction for multi-provider support."""

from .anthropic import AnthropicProvider
from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig
from .mock import MockProvider


def get_provider(name: str = "anthropic") -> LLMProvider:
    """Get an LLM provider by name.

    Args:
        name: Provider name ('anthropic' or 'mock')

    Returns:
        Configured LLM provider instance
    """
    if name == "anthropic":
        return AnthropicProvider()
    if name == "mock":
        return MockProvider()
    else:
        raise ValueError(f"Unknown provider: {name}. Available: anthropic, mock")


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ModelTier",
    "ProviderConfig",
    "AnthropicProvider",
    "MockProvider",
    "get_provider",
]
