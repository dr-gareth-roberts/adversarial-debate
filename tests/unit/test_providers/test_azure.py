"""Tests for Azure OpenAI provider."""

import pytest

from adversarial_debate.providers.base import ModelTier, ProviderConfig


class TestAzureOpenAIProvider:
    """Tests for AzureOpenAIProvider."""

    def test_import_error_without_package(self, monkeypatch):
        """Test that ImportError is raised without openai package."""
        import sys
        import builtins

        # Mock the import to fail
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "openai" or name.startswith("openai."):
                raise ImportError("No module named 'openai'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        monkeypatch.delitem(
            sys.modules, "adversarial_debate.providers.azure", raising=False
        )

        try:
            from adversarial_debate.providers.azure import AzureOpenAIProvider
            with pytest.raises(ImportError, match="openai package not installed"):
                AzureOpenAIProvider(ProviderConfig(base_url="https://test.openai.azure.com"))
        except ImportError:
            pass

    def test_requires_endpoint(self):
        """Test that endpoint is required."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.azure import AzureOpenAIProvider

        with pytest.raises(ValueError, match="Azure OpenAI endpoint required"):
            AzureOpenAIProvider()

    def test_provider_name(self):
        """Test provider name property."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.azure import AzureOpenAIProvider

        config = ProviderConfig(
            api_key="test-key",
            base_url="https://test.openai.azure.com"
        )
        provider = AzureOpenAIProvider(config)
        assert provider.name == "azure"

    def test_config_from_env(self, monkeypatch):
        """Test that config can come from environment."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.azure import AzureOpenAIProvider

        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "env-key")
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://env.openai.azure.com")
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "my-deployment")
        monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-03-01")

        provider = AzureOpenAIProvider()
        assert provider.config.api_key == "env-key"
        assert provider.config.base_url == "https://env.openai.azure.com"
        assert provider._deployment == "my-deployment"
        assert provider._api_version == "2024-03-01"

    def test_deployment_used_for_all_tiers(self):
        """Test that deployment name is used for all tiers when set."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.azure import AzureOpenAIProvider

        config = ProviderConfig(
            api_key="test-key",
            base_url="https://test.openai.azure.com",
            extra={"deployment": "my-gpt4-deployment"}
        )
        provider = AzureOpenAIProvider(config)

        # All tiers should return the deployment name
        assert provider.get_model_for_tier(ModelTier.LOCAL_SMALL) == "my-gpt4-deployment"
        assert provider.get_model_for_tier(ModelTier.HOSTED_SMALL) == "my-gpt4-deployment"
        assert provider.get_model_for_tier(ModelTier.HOSTED_LARGE) == "my-gpt4-deployment"

    def test_tier_models_without_deployment(self):
        """Test tier model selection when no deployment is set."""
        pytest.importorskip("openai")
        from adversarial_debate.providers.azure import AzureOpenAIProvider

        config = ProviderConfig(
            api_key="test-key",
            base_url="https://test.openai.azure.com"
        )
        provider = AzureOpenAIProvider(config)

        assert provider.get_model_for_tier(ModelTier.LOCAL_SMALL) == "gpt-4o-mini"
        assert provider.get_model_for_tier(ModelTier.HOSTED_LARGE) == "gpt-4o"
