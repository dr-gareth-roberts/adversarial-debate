"""LLM provider abstraction for multi-provider support."""

from .base import LLMProvider, LLMResponse, Message, ProviderConfig, ModelTier
from .anthropic import AnthropicProvider


def get_provider(name: str = "anthropic") -> LLMProvider:
    """Get an LLM provider by name.

    Args:
        name: Provider name ('anthropic', 'openai', etc.)

    Returns:
        Configured LLM provider instance
    """
    if name == "anthropic":
        return AnthropicProvider()
    else:
        raise ValueError(f"Unknown provider: {name}. Available: anthropic")


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ModelTier",
    "ProviderConfig",
    "AnthropicProvider",
    "get_provider",
]
