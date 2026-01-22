"""LLM provider abstraction for multi-provider support."""

from .anthropic import AnthropicProvider
from .base import LLMProvider, LLMResponse, Message, ModelTier, ProviderConfig
from .mock import MockProvider

# Lazy imports for optional providers
_openai_provider = None
_azure_provider = None
_ollama_provider = None


def _get_openai_provider():
    global _openai_provider
    if _openai_provider is None:
        from .openai import OpenAIProvider
        _openai_provider = OpenAIProvider
    return _openai_provider


def _get_azure_provider():
    global _azure_provider
    if _azure_provider is None:
        from .azure import AzureOpenAIProvider
        _azure_provider = AzureOpenAIProvider
    return _azure_provider


def _get_ollama_provider():
    global _ollama_provider
    if _ollama_provider is None:
        from .ollama import OllamaProvider
        _ollama_provider = OllamaProvider
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
        OpenAIProvider = _get_openai_provider()
        return OpenAIProvider(config)
    if name == "azure":
        AzureOpenAIProvider = _get_azure_provider()
        return AzureOpenAIProvider(config)
    if name == "ollama":
        OllamaProvider = _get_ollama_provider()
        return OllamaProvider(config)
    else:
        raise ValueError(
            f"Unknown provider: {name}. "
            f"Available: anthropic, openai, azure, ollama, mock"
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
