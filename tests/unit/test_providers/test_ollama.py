"""Tests for Ollama provider."""

import pytest

from adversarial_debate.providers.base import ModelTier, ProviderConfig
from adversarial_debate.providers.ollama import OllamaProvider


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_provider_name(self):
        """Test provider name property."""
        provider = OllamaProvider()
        assert provider.name == "ollama"

    def test_default_base_url(self):
        """Test default base URL."""
        provider = OllamaProvider()
        assert provider.config.base_url == "http://localhost:11434"

    def test_custom_base_url(self):
        """Test custom base URL."""
        config = ProviderConfig(base_url="http://custom:8080")
        provider = OllamaProvider(config)
        assert provider.config.base_url == "http://custom:8080"

    def test_base_url_from_env(self, monkeypatch):
        """Test base URL from environment."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://env-host:11434")
        provider = OllamaProvider()
        assert provider.config.base_url == "http://env-host:11434"

    def test_default_model(self):
        """Test default model."""
        provider = OllamaProvider()
        assert provider._default_model() == "llama3.1:8b"

    def test_model_for_tier(self):
        """Test model selection by tier."""
        provider = OllamaProvider()

        assert provider.get_model_for_tier(ModelTier.LOCAL_SMALL) == "llama3.2:3b"
        assert provider.get_model_for_tier(ModelTier.HOSTED_SMALL) == "llama3.2:3b"
        assert provider.get_model_for_tier(ModelTier.HOSTED_LARGE) == "llama3.1:70b"

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test that aiohttp session is created lazily."""
        provider = OllamaProvider()
        assert provider._session is None

        # Session should be created on first access
        session = await provider._get_session()
        assert session is not None
        assert provider._session is session

        # Same session should be reused
        session2 = await provider._get_session()
        assert session2 is session

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test session cleanup."""
        provider = OllamaProvider()
        session = await provider._get_session()
        assert not session.closed

        await provider.close()
        assert session.closed
