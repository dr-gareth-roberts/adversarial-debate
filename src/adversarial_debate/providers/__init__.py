"""LLM provider abstraction for multi-provider support."""

from __future__ import annotations

from typing import Protocol

from .anthropic import AnthropicProvider
from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig
from .mock import MockProvider


# Lazy imports for optional providers
class _ProviderFactory(Protocol):
    def __call__(self, config: ProviderConfig | None = None) -> LLMProvider: ...


_openai_provider: _ProviderFactory | None = None
_azure_provider: _ProviderFactory | None = None
_ollama_provider: _ProviderFactory | None = None


def _get_openai_provider() -> _ProviderFactory:
    global _openai_provider
    if _openai_provider is None:
        from .openai import OpenAIProvider

        _openai_provider = OpenAIProvider
    assert _openai_provider is not None
    return _openai_provider


def _get_azure_provider() -> _ProviderFactory:
    global _azure_provider
    if _azure_provider is None:
        from .azure import AzureOpenAIProvider

        _azure_provider = AzureOpenAIProvider
    assert _azure_provider is not None
    return _azure_provider


def _get_ollama_provider() -> _ProviderFactory:
    global _ollama_provider
    if _ollama_provider is None:
        from .ollama import OllamaProvider

        _ollama_provider = OllamaProvider
    assert _ollama_provider is not None
    return _ollama_provider


def get_provider(name: str = "anthropic", config: ProviderConfig | None = None) -> LLMProvider:
    """Get an LLM provider by name.

    Args:
        name: Provider name ('anthropic', 'openai', 'azure', 'ollama', or 'mock')
        config: Optional provider configuration

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider name is unknown
        ImportError: If required package for provider is not installed
    """
    if name == "anthropic":
        return AnthropicProvider(config)
    if name == "mock":
        return MockProvider(config)
    if name == "openai":
        factory = _get_openai_provider()
        return factory(config)
    if name == "azure":
        factory = _get_azure_provider()
        return factory(config)
    if name == "ollama":
        factory = _get_ollama_provider()
        return factory(config)
    else:
        raise ValueError(
            f"Unknown provider: {name}. Available: anthropic, openai, azure, ollama, mock"
        )


def list_providers() -> list[str]:
    """List available provider names.

    Returns:
        List of provider names that can be used with get_provider()
    """
    return ["anthropic", "openai", "azure", "ollama", "mock"]


__all__ = [
    # Base classes
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ModelTier",
    "ProviderConfig",
    # Providers
    "AnthropicProvider",
    "MockProvider",
    # Factory functions
    "get_provider",
    "list_providers",
]
