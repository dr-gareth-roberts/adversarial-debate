"""Exception hierarchy for adversarial-debate.

This module defines a comprehensive exception hierarchy for the package,
making error handling consistent and informative across all components.
"""

from typing import Any


class AdversarialDebateError(Exception):
    """Base exception for all adversarial-debate errors.

    All custom exceptions in this package inherit from this class,
    making it easy to catch all package-specific errors.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(AdversarialDebateError):
    """Base class for agent-related errors."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.agent_name = agent_name


class AgentExecutionError(AgentError):
    """Raised when an agent fails to execute its task."""

    pass


class AgentParseError(AgentError):
    """Raised when an agent fails to parse LLM response."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        raw_response: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, agent_name, details)
        self.raw_response = raw_response


class AgentTimeoutError(AgentError):
    """Raised when an agent operation times out."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        timeout_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, agent_name, details)
        self.timeout_seconds = timeout_seconds


# =============================================================================
# Provider Errors
# =============================================================================


class ProviderError(AdversarialDebateError):
    """Base class for LLM provider errors."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.provider_name = provider_name


class ProviderRateLimitError(ProviderError):
    """Raised when the LLM provider rate limits the request."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        retry_after_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, provider_name, details)
        self.retry_after_seconds = retry_after_seconds


class ProviderConnectionError(ProviderError):
    """Raised when unable to connect to the LLM provider."""

    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when authentication with the provider fails."""

    pass


# =============================================================================
# Sandbox Errors
# =============================================================================


class SandboxError(AdversarialDebateError):
    """Base class for sandbox execution errors."""

    pass


class SandboxExecutionError(SandboxError):
    """Raised when code execution in the sandbox fails."""

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class SandboxTimeoutError(SandboxError):
    """Raised when sandbox execution times out."""

    def __init__(
        self,
        message: str,
        timeout_seconds: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.timeout_seconds = timeout_seconds


class SandboxSecurityError(SandboxError):
    """Raised when sandbox detects a security violation."""

    def __init__(
        self,
        message: str,
        violation_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.violation_type = violation_type


# =============================================================================
# Store Errors
# =============================================================================


class StoreError(AdversarialDebateError):
    """Base class for bead store errors."""

    pass


class BeadValidationError(StoreError):
    """Raised when a bead fails validation."""

    def __init__(
        self,
        message: str,
        bead_id: str | None = None,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.bead_id = bead_id
        self.field = field


class DuplicateBeadError(StoreError):
    """Raised when attempting to insert a duplicate bead."""

    def __init__(
        self,
        message: str,
        idempotency_key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.idempotency_key = idempotency_key


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigError(AdversarialDebateError):
    """Base class for configuration errors."""

    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.field = field
        self.value = value


class ConfigNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""

    def __init__(
        self,
        message: str,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.path = path


__all__ = [
    # Base
    "AdversarialDebateError",
    # Agent
    "AgentError",
    "AgentExecutionError",
    "AgentParseError",
    "AgentTimeoutError",
    # Provider
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderConnectionError",
    "ProviderAuthenticationError",
    # Sandbox
    "SandboxError",
    "SandboxExecutionError",
    "SandboxTimeoutError",
    "SandboxSecurityError",
    # Store
    "StoreError",
    "BeadValidationError",
    "DuplicateBeadError",
    # Config
    "ConfigError",
    "ConfigValidationError",
    "ConfigNotFoundError",
]
