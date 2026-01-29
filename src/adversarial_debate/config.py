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
from .sandbox import SandboxConfig, SandboxSecurityError, validate_sandbox_config


@dataclass
class ProviderConfig:
    """Configuration for LLM providers.

    Attributes:
        provider: Provider name (anthropic, openai, etc.)
        api_key: API key for the provider (loaded from env if not set)
        base_url: Optional provider base URL override
        model: Default model to use
        timeout_seconds: Request timeout
        max_retries: Maximum retry attempts
        temperature: Default temperature for generation
        max_tokens: Maximum tokens for response
        extra: Provider-specific settings
    """

    provider: str = "anthropic"
    api_key: str | None = None
    base_url: str | None = None
    model: str = "claude-sonnet-4-20250514"
    timeout_seconds: int = 120
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 4096
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Load API key from environment if not provided."""
        if self.api_key is None:
            env_var = f"{self.provider.upper()}_API_KEY"
            self.api_key = os.environ.get(env_var)
            if self.api_key is None and self.provider == "azure":
                self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")

        if self.base_url is None:
            env_var = f"{self.provider.upper()}_BASE_URL"
            self.base_url = os.environ.get(env_var)
            if self.base_url is None and self.provider == "azure":
                self.base_url = os.environ.get("AZURE_OPENAI_ENDPOINT")

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
            "base_url": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "extra": self.extra,
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


def _parse_sandbox_config(data: dict[str, Any]) -> SandboxConfig:
    """Parse sandbox config, including legacy keys."""
    legacy_enabled = data.get("enabled")

    # Support both new keys (sandbox.SandboxConfig) and legacy keys (config.SandboxConfig).
    memory_limit: str | None = data.get("memory_limit")
    if memory_limit is None:
        memory_limit_mb = data.get("memory_limit_mb") or data.get("max_memory_mb")
        if isinstance(memory_limit_mb, int):
            memory_limit = f"{memory_limit_mb}m"

    cpu_limit = data.get("cpu_limit")
    timeout_seconds = data.get("timeout_seconds") or data.get("timeout")
    docker_image = data.get("docker_image") or data.get("image")

    use_docker = data.get("use_docker")
    use_subprocess = data.get("use_subprocess")
    if legacy_enabled is False:
        use_docker = False
        use_subprocess = False

    kwargs: dict[str, Any] = {}
    if memory_limit is not None:
        kwargs["memory_limit"] = str(memory_limit)
    if cpu_limit is not None:
        kwargs["cpu_limit"] = float(cpu_limit)
    if timeout_seconds is not None:
        kwargs["timeout_seconds"] = int(timeout_seconds)
    if data.get("max_output_size_bytes") is not None:
        kwargs["max_output_size_bytes"] = int(data["max_output_size_bytes"])
    if data.get("network_enabled") is not None:
        kwargs["network_enabled"] = bool(data["network_enabled"])
    if data.get("allowed_hosts") is not None:
        kwargs["allowed_hosts"] = [str(h) for h in data["allowed_hosts"]]
    if data.get("read_only") is not None:
        kwargs["read_only"] = bool(data["read_only"])
    if data.get("temp_size") is not None:
        kwargs["temp_size"] = str(data["temp_size"])
    if use_docker is not None:
        kwargs["use_docker"] = bool(use_docker)
    if docker_image is not None:
        kwargs["docker_image"] = str(docker_image)
    if use_subprocess is not None:
        kwargs["use_subprocess"] = bool(use_subprocess)
    if data.get("subprocess_timeout") is not None:
        kwargs["subprocess_timeout"] = int(data["subprocess_timeout"])

    return SandboxConfig(**kwargs)


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
        try:
            validate_sandbox_config(self.sandbox)
        except SandboxSecurityError as e:
            raise ConfigValidationError(str(e), field="sandbox") from e

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
                base_url=provider_data.get("base_url"),
                model=provider_data.get("model", "claude-sonnet-4-20250514"),
                timeout_seconds=provider_data.get("timeout_seconds", 120),
                max_retries=provider_data.get("max_retries", 3),
                temperature=provider_data.get("temperature", 0.7),
                max_tokens=provider_data.get("max_tokens", 4096),
                extra=dict(provider_data.get("extra", {})),
            ),
            logging=LoggingConfig(
                level=logging_data.get("level", "INFO"),
                format=logging_data.get("format", "text"),
                file_path=logging_data.get("file_path"),
                include_timestamps=logging_data.get("include_timestamps", True),
                include_agent_context=logging_data.get("include_agent_context", True),
            ),
            sandbox=_parse_sandbox_config(sandbox_data),
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
