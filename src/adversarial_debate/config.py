"""Configuration management for adversarial-debate.

This module provides type-safe configuration loading from environment
variables and configuration files with validation.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ConfigNotFoundError, ConfigValidationError


@dataclass
class ProviderConfig:
    """Configuration for LLM providers.

    Attributes:
        provider: Provider name (anthropic, openai, etc.)
        api_key: API key for the provider (loaded from env if not set)
        model: Default model to use
        timeout_seconds: Request timeout
        max_retries: Maximum retry attempts
        temperature: Default temperature for generation
        max_tokens: Maximum tokens for response
    """

    provider: str = "anthropic"
    api_key: str | None = None
    model: str = "claude-sonnet-4-20250514"
    timeout_seconds: int = 120
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 4096

    def __post_init__(self) -> None:
        """Load API key from environment if not provided."""
        if self.api_key is None:
            env_var = f"{self.provider.upper()}_API_KEY"
            self.api_key = os.environ.get(env_var)

    def validate(self) -> None:
        """Validate the configuration."""
        if not self.provider:
            raise ConfigValidationError("Provider name is required", field="provider")
        if self.timeout_seconds <= 0:
            raise ConfigValidationError(
                "Timeout must be positive",
                field="timeout_seconds",
                value=self.timeout_seconds,
            )
        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigValidationError(
                "Temperature must be between 0.0 and 2.0",
                field="temperature",
                value=self.temperature,
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict (excludes api_key for safety)."""
        return {
            "provider": self.provider,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass
class LoggingConfig:
    """Configuration for logging.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format: Log format (json, text)
        file_path: Optional file path for log output
        include_timestamps: Include timestamps in logs
        include_agent_context: Include agent context in logs
    """

    level: str = "INFO"
    format: str = "text"
    file_path: str | None = None
    include_timestamps: bool = True
    include_agent_context: bool = True

    def validate(self) -> None:
        """Validate the configuration."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level.upper() not in valid_levels:
            raise ConfigValidationError(
                f"Invalid log level. Must be one of: {valid_levels}",
                field="level",
                value=self.level,
            )
        valid_formats = {"json", "text"}
        if self.format.lower() not in valid_formats:
            raise ConfigValidationError(
                f"Invalid log format. Must be one of: {valid_formats}",
                field="format",
                value=self.format,
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "level": self.level,
            "format": self.format,
            "file_path": self.file_path,
            "include_timestamps": self.include_timestamps,
            "include_agent_context": self.include_agent_context,
        }


@dataclass
class SandboxConfig:
    """Configuration for the sandbox executor.

    Attributes:
        enabled: Whether to use sandboxed execution
        timeout_seconds: Execution timeout
        memory_limit_mb: Memory limit in megabytes
        network_enabled: Allow network access
        docker_image: Docker image to use for sandboxing
    """

    enabled: bool = True
    timeout_seconds: int = 30
    memory_limit_mb: int = 512
    network_enabled: bool = False
    docker_image: str = "python:3.11-slim"

    def validate(self) -> None:
        """Validate the configuration."""
        if self.timeout_seconds <= 0:
            raise ConfigValidationError(
                "Timeout must be positive",
                field="timeout_seconds",
                value=self.timeout_seconds,
            )
        if self.memory_limit_mb <= 0:
            raise ConfigValidationError(
                "Memory limit must be positive",
                field="memory_limit_mb",
                value=self.memory_limit_mb,
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "memory_limit_mb": self.memory_limit_mb,
            "network_enabled": self.network_enabled,
            "docker_image": self.docker_image,
        }


@dataclass
class Config:
    """Main configuration container.

    This is the root configuration object that contains all subsystem
    configurations. It can be loaded from environment variables or files.
    """

    provider: ProviderConfig = field(default_factory=ProviderConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)

    # Additional settings
    debug: bool = False
    dry_run: bool = False
    output_dir: str = "./output"
    bead_ledger_path: str = "./beads/ledger.jsonl"

    def validate(self) -> None:
        """Validate all configuration sections."""
        self.provider.validate()
        self.logging.validate()
        self.sandbox.validate()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "provider": self.provider.to_dict(),
            "logging": self.logging.to_dict(),
            "sandbox": self.sandbox.to_dict(),
            "debug": self.debug,
            "dry_run": self.dry_run,
            "output_dir": self.output_dir,
            "bead_ledger_path": self.bead_ledger_path,
        }

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables.

        Environment variables:
            ADVERSARIAL_DEBUG: Enable debug mode
            ADVERSARIAL_DRY_RUN: Enable dry run mode
            ADVERSARIAL_OUTPUT_DIR: Output directory
            ADVERSARIAL_BEAD_LEDGER: Path to bead ledger
            ADVERSARIAL_LOG_LEVEL: Log level
            ADVERSARIAL_LOG_FORMAT: Log format (json/text)
            ANTHROPIC_API_KEY: Anthropic API key
            LLM_PROVIDER: LLM provider name
            LLM_MODEL: Model to use
            LLM_TIMEOUT: Request timeout in seconds
        """
        # Provider config from env
        provider = ProviderConfig(
            provider=os.environ.get("LLM_PROVIDER", "anthropic"),
            model=os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514"),
            timeout_seconds=int(os.environ.get("LLM_TIMEOUT", "120")),
        )

        # Logging config from env
        logging_config = LoggingConfig(
            level=os.environ.get("ADVERSARIAL_LOG_LEVEL", "INFO"),
            format=os.environ.get("ADVERSARIAL_LOG_FORMAT", "text"),
        )

        # Main config
        return cls(
            provider=provider,
            logging=logging_config,
            debug=os.environ.get("ADVERSARIAL_DEBUG", "").lower() in ("1", "true", "yes"),
            dry_run=os.environ.get("ADVERSARIAL_DRY_RUN", "").lower() in ("1", "true", "yes"),
            output_dir=os.environ.get("ADVERSARIAL_OUTPUT_DIR", "./output"),
            bead_ledger_path=os.environ.get("ADVERSARIAL_BEAD_LEDGER", "./beads/ledger.jsonl"),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        """Load configuration from a JSON file.

        Args:
            path: Path to the configuration file

        Returns:
            Config instance

        Raises:
            ConfigNotFoundError: If the file doesn't exist
            ConfigValidationError: If the file is invalid
        """
        path = Path(path)
        if not path.exists():
            raise ConfigNotFoundError(f"Configuration file not found: {path}", path=str(path))

        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(
                f"Invalid JSON in configuration file: {e}",
                details={"path": str(path)},
            ) from e

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance
        """
        provider_data = data.get("provider", {})
        logging_data = data.get("logging", {})
        sandbox_data = data.get("sandbox", {})

        return cls(
            provider=ProviderConfig(
                provider=provider_data.get("provider", "anthropic"),
                api_key=provider_data.get("api_key"),
                model=provider_data.get("model", "claude-sonnet-4-20250514"),
                timeout_seconds=provider_data.get("timeout_seconds", 120),
                max_retries=provider_data.get("max_retries", 3),
                temperature=provider_data.get("temperature", 0.7),
                max_tokens=provider_data.get("max_tokens", 4096),
            ),
            logging=LoggingConfig(
                level=logging_data.get("level", "INFO"),
                format=logging_data.get("format", "text"),
                file_path=logging_data.get("file_path"),
                include_timestamps=logging_data.get("include_timestamps", True),
                include_agent_context=logging_data.get("include_agent_context", True),
            ),
            sandbox=SandboxConfig(
                enabled=sandbox_data.get("enabled", True),
                timeout_seconds=sandbox_data.get("timeout_seconds", 30),
                memory_limit_mb=sandbox_data.get("memory_limit_mb", 512),
                network_enabled=sandbox_data.get("network_enabled", False),
                docker_image=sandbox_data.get("docker_image", "python:3.11-slim"),
            ),
            debug=data.get("debug", False),
            dry_run=data.get("dry_run", False),
            output_dir=data.get("output_dir", "./output"),
            bead_ledger_path=data.get("bead_ledger_path", "./beads/ledger.jsonl"),
        )


# Global configuration instance (lazy-loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance.

    Creates the configuration from environment on first call.

    Returns:
        Global Config instance
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance.

    Args:
        config: Config instance to use globally
    """
    global _config
    _config = config


__all__ = [
    "ProviderConfig",
    "LoggingConfig",
    "SandboxConfig",
    "Config",
    "get_config",
    "set_config",
]
