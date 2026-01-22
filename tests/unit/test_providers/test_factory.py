"""Tests for provider factory functions."""

import pytest

from adversarial_debate.providers import get_provider, list_providers
from adversarial_debate.providers.mock import MockProvider


class TestGetProvider:
    """Tests for get_provider factory function."""

    def test_get_mock_provider(self):
        """Test getting mock provider."""
        provider = get_provider("mock")
        assert isinstance(provider, MockProvider)
        assert provider.name == "mock"

    def test_get_anthropic_provider(self, monkeypatch):
        """Test getting anthropic provider."""
        pytest.importorskip("anthropic")
        from adversarial_debate.providers import AnthropicProvider

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        provider = get_provider("anthropic")
        assert isinstance(provider, AnthropicProvider)

    def test_get_openai_provider(self, monkeypatch):
        """Test getting openai provider."""
        pytest.importorskip("openai")

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        provider = get_provider("openai")
        assert provider.name == "openai"

    def test_get_azure_provider(self, monkeypatch):
        """Test getting azure provider."""
        pytest.importorskip("openai")

        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
        provider = get_provider("azure")
        assert provider.name == "azure"

    def test_get_ollama_provider(self):
        """Test getting ollama provider."""
        provider = get_provider("ollama")
        assert provider.name == "ollama"

    def test_unknown_provider(self):
        """Test that unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            get_provider("unknown")

    def test_default_provider_is_anthropic(self, monkeypatch):
        """Test that default provider is anthropic."""
        pytest.importorskip("anthropic")
        from adversarial_debate.providers import AnthropicProvider

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        provider = get_provider()
        assert isinstance(provider, AnthropicProvider)


class TestListProviders:
    """Tests for list_providers function."""

    def test_list_providers(self):
        """Test listing available providers."""
        providers = list_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "azure" in providers
        assert "ollama" in providers
        assert "mock" in providers

    def test_list_providers_count(self):
        """Test that all expected providers are listed."""
        providers = list_providers()
        assert len(providers) == 5
