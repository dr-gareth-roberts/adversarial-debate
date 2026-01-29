"""Tests for OpenAI provider."""

import pytest

from adversarial_debate.providers.base import ModelTier, ProviderConfig


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_import_error_without_package(self, monkeypatch):
        """Test that ImportError is raised without openai package."""
        import sys

        # Remove openai from modules if present
        openai_modules = [k for k in sys.modules if k.startswith("openai")]
        for mod in openai_modules:
            monkeypatch.delitem(sys.modules, mod, raising=False)

        # Mock the import to fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "openai" or name.startswith("openai."):
                raise ImportError("No module named 'openai'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Clear the cached module to force reimport
        monkeypatch.delitem(sys.modules, "adversarial_debate.providers.openai", raising=False)

        # This should work - the module imports but sets HAS_OPENAI = False
        # The actual error comes when instantiating
        try:
            from adversarial_debate.providers.openai import OpenAIProvider

            with pytest.raises(ImportError, match="openai package not installed"):
                OpenAIProvider()
        except ImportError:
            # If we can't even import, that's also acceptable
            pass

    def test_provider_name(self):
        """Test provider name property."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)
        assert provider.name == "openai"

    def test_default_model(self):
        """Test default model."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)
        assert provider._default_model() == "gpt-4o"

    def test_model_for_tier(self):
        """Test model selection by tier."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.openai import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        assert provider.get_model_for_tier(ModelTier.LOCAL_SMALL) == "gpt-4o-mini"
        assert provider.get_model_for_tier(ModelTier.HOSTED_SMALL) == "gpt-4o-mini"
        assert provider.get_model_for_tier(ModelTier.HOSTED_LARGE) == "gpt-4o"

    def test_config_from_env(self, monkeypatch):
        """Test that API key can come from environment."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.openai import OpenAIProvider

        monkeypatch.setenv("OPENAI_API_KEY", "env-test-key")
        provider = OpenAIProvider()
        assert provider.config.api_key == "env-test-key"
