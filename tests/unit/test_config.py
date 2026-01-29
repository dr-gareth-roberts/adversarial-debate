"""Unit tests for configuration module."""

import json
from pathlib import Path

import pytest

from adversarial_debate.config import (
    Config,
    LoggingConfig,
    ProviderConfig,
    SandboxConfig,
    get_config,
    set_config,
)
from adversarial_debate.exceptions import ConfigNotFoundError, ConfigValidationError


class TestProviderConfig:
    """Tests for ProviderConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = ProviderConfig()
        assert config.provider == "anthropic"
        assert config.timeout_seconds == 120
        assert config.max_retries == 3
        assert config.temperature == 0.7

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key loaded from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
        config = ProviderConfig(provider="anthropic")
        assert config.api_key == "test-key-123"

    def test_explicit_api_key(self) -> None:
        """Test explicit API key overrides environment."""
        config = ProviderConfig(provider="anthropic", api_key="explicit-key")
        assert config.api_key == "explicit-key"

    def test_validate_success(self) -> None:
        """Test validation passes for valid config."""
        config = ProviderConfig(
            provider="anthropic",
            timeout_seconds=60,
            temperature=0.5,
        )
        config.validate()  # Should not raise

    def test_validate_invalid_timeout(self) -> None:
        """Test validation fails for invalid timeout."""
        config = ProviderConfig(timeout_seconds=0)
        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()
        assert exc_info.value.field == "timeout_seconds"

    def test_validate_invalid_temperature(self) -> None:
        """Test validation fails for invalid temperature."""
        config = ProviderConfig(temperature=3.0)
        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()
        assert exc_info.value.field == "temperature"

    def test_to_dict_excludes_api_key(self) -> None:
        """Test to_dict doesn't include API key."""
        config = ProviderConfig(api_key="secret-key")
        data = config.to_dict()
        assert "api_key" not in data
        assert "provider" in data


class TestLoggingConfig:
    """Tests for LoggingConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "text"
        assert config.include_timestamps is True

    def test_validate_success(self) -> None:
        """Test validation passes for valid config."""
        config = LoggingConfig(level="DEBUG", format="json")
        config.validate()  # Should not raise

    def test_validate_invalid_level(self) -> None:
        """Test validation fails for invalid log level."""
        config = LoggingConfig(level="VERBOSE")
        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()
        assert exc_info.value.field == "level"

    def test_validate_invalid_format(self) -> None:
        """Test validation fails for invalid format."""
        config = LoggingConfig(format="xml")
        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()
        assert exc_info.value.field == "format"


class TestSandboxConfig:
    """Tests for SandboxConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = SandboxConfig()
        assert config.timeout_seconds == 30
        assert config.memory_limit == "256m"
        assert config.network_enabled is False
        assert config.use_docker is True
        assert config.use_subprocess is True

    def test_validate_invalid_timeout(self) -> None:
        """Test invalid sandbox config is rejected by Config.validate()."""
        config = Config(sandbox=SandboxConfig(timeout_seconds=-1))
        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()
        assert exc_info.value.field == "sandbox"


class TestConfig:
    """Tests for main Config class."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = Config()
        assert config.debug is False
        assert config.dry_run is False
        assert isinstance(config.provider, ProviderConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.sandbox, SandboxConfig)

    def test_validate_all_sections(self) -> None:
        """Test validate calls all section validators."""
        config = Config(
            provider=ProviderConfig(timeout_seconds=-1),
        )
        with pytest.raises(ConfigValidationError):
            config.validate()

    def test_to_dict(self) -> None:
        """Test converting to dict."""
        config = Config(debug=True)
        data = config.to_dict()
        assert data["debug"] is True
        assert "provider" in data
        assert "logging" in data
        assert "sandbox" in data

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading from environment variables."""
        monkeypatch.setenv("ADVERSARIAL_DEBUG", "true")
        monkeypatch.setenv("ADVERSARIAL_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_TIMEOUT", "60")

        config = Config.from_env()
        assert config.debug is True
        assert config.logging.level == "DEBUG"
        assert config.provider.provider == "openai"
        assert config.provider.timeout_seconds == 60

    def test_from_file(self, temp_dir: Path) -> None:
        """Test loading from file."""
        config_path = temp_dir / "config.json"
        config_data = {
            "debug": True,
            "provider": {
                "provider": "openai",
                "model": "gpt-4",
            },
            "logging": {
                "level": "WARNING",
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        config = Config.from_file(config_path)
        assert config.debug is True
        assert config.provider.provider == "openai"
        assert config.provider.model == "gpt-4"
        assert config.logging.level == "WARNING"

    def test_from_file_not_found(self, temp_dir: Path) -> None:
        """Test error when file not found."""
        with pytest.raises(ConfigNotFoundError):
            Config.from_file(temp_dir / "nonexistent.json")

    def test_from_file_invalid_json(self, temp_dir: Path) -> None:
        """Test error when file contains invalid JSON."""
        config_path = temp_dir / "invalid.json"
        with open(config_path, "w") as f:
            f.write("not valid json")

        with pytest.raises(ConfigValidationError):
            Config.from_file(config_path)

    def test_from_dict(self) -> None:
        """Test creating from dict."""
        data = {
            "debug": True,
            "dry_run": True,
            "output_dir": "/custom/output",
            "provider": {
                "provider": "anthropic",
                "temperature": 0.3,
            },
        }
        config = Config.from_dict(data)
        assert config.debug is True
        assert config.dry_run is True
        assert config.output_dir == "/custom/output"
        assert config.provider.temperature == 0.3


class TestGlobalConfig:
    """Tests for global config functions."""

    def test_get_config_creates_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_config creates config from env."""
        # Reset global config
        import adversarial_debate.config as config_module

        config_module._config = None

        config = get_config()
        assert isinstance(config, Config)

    def test_set_config(self) -> None:
        """Test setting global config."""
        custom_config = Config(debug=True)
        set_config(custom_config)

        retrieved = get_config()
        assert retrieved.debug is True

        # Clean up
        import adversarial_debate.config as config_module

        config_module._config = None
