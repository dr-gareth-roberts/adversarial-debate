"""Exception hierarchy for adversarial-debate.

This module defines a comprehensive exception hierarchy for the package,
making error handling consistent and informative across all components.

All exceptions include:
- A descriptive error message
- Optional details dictionary
- A suggestion property for recommended fixes
"""

from typing import Any


class AdversarialDebateError(Exception):
    """Base exception for all adversarial-debate errors.

    All custom exceptions in this package inherit from this class,
    making it easy to catch all package-specific errors.
    """

    # Default suggestion (override in subclasses)
    _suggestion: str | None = None

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self._custom_suggestion = suggestion

    @property
    def suggestion(self) -> str | None:
        """Get a suggested fix for this error."""
        return self._custom_suggestion or self._suggestion

    def __str__(self) -> str:
        parts = [self.message]
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)

    def format_short(self) -> str:
        """Format error message without details."""
        if self.suggestion:
            return f"{self.message}\n  → {self.suggestion}"
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
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.agent_name = agent_name


class AgentExecutionError(AgentError):
    """Raised when an agent fails to execute its task."""

    _suggestion = "Check the agent logs for more details. Verify the input code is valid."


class AgentParseError(AgentError):
    """Raised when an agent fails to parse LLM response."""

    _suggestion = (
        "The LLM response was not in the expected format. "
        "Try running again or use a different model."
    )

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        raw_response: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, agent_name, details, suggestion)
        self.raw_response = raw_response


class AgentTimeoutError(AgentError):
    """Raised when an agent operation times out."""

    _suggestion = "Increase the timeout with --timeout or reduce the code size."

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        timeout_seconds: float | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, agent_name, details, suggestion)
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
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.provider_name = provider_name


class ProviderRateLimitError(ProviderError):
    """Raised when the LLM provider rate limits the request."""

    _suggestion = (
        "You've hit API rate limits. Wait a few seconds and try again, "
        "or reduce parallel agent count with --parallel."
    )

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        retry_after_seconds: float | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, provider_name, details, suggestion)
        self.retry_after_seconds = retry_after_seconds

        # Dynamic suggestion based on retry time
        if retry_after_seconds:
            self._custom_suggestion = (
                f"Rate limited. Wait {retry_after_seconds:.0f} seconds before retrying."
            )


class ProviderConnectionError(ProviderError):
    """Raised when unable to connect to the LLM provider."""

    _suggestion = (
        "Check your internet connection and verify the API endpoint is reachable. "
        "If using a custom base_url, ensure it's correct."
    )


class ProviderAuthenticationError(ProviderError):
    """Raised when authentication with the provider fails."""

    @property
    def suggestion(self) -> str:
        """Get provider-specific authentication suggestion."""
        if self._custom_suggestion:
            return self._custom_suggestion

        suggestions = {
            "anthropic": (
                "Set ANTHROPIC_API_KEY environment variable or provide api_key in config. "
                "Get a key at: https://console.anthropic.com/settings/keys"
            ),
            "openai": (
                "Set OPENAI_API_KEY environment variable or provide api_key in config. "
                "Get a key at: https://platform.openai.com/api-keys"
            ),
            "azure": (
                "Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables. "
                "Ensure your Azure OpenAI resource is properly configured."
            ),
            "ollama": ("Ensure Ollama is running locally. Start with: ollama serve"),
        }
        return suggestions.get(
            self.provider_name or "", "Check your API key and provider configuration."
        )


# =============================================================================
# Sandbox Errors
# =============================================================================


class SandboxError(AdversarialDebateError):
    """Base class for sandbox execution errors."""

    _suggestion = "Check Docker is installed and running: docker info"


class SandboxExecutionError(SandboxError):
    """Raised when code execution in the sandbox fails."""

    _suggestion = (
        "The code failed to execute in the sandbox. "
        "Check the code for syntax errors or missing dependencies."
    )

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class SandboxTimeoutError(SandboxError):
    """Raised when sandbox execution times out."""

    _suggestion = (
        "The sandbox execution took too long. Check for infinite loops or increase the timeout."
    )

    def __init__(
        self,
        message: str,
        timeout_seconds: float | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.timeout_seconds = timeout_seconds


class SandboxSecurityError(SandboxError):
    """Raised when sandbox detects a security violation."""

    _suggestion = (
        "The sandbox blocked a potentially dangerous operation. "
        "This is expected for malicious code samples."
    )

    def __init__(
        self,
        message: str,
        violation_type: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.violation_type = violation_type


# =============================================================================
# Store Errors
# =============================================================================


class StoreError(AdversarialDebateError):
    """Base class for bead store errors."""

    _suggestion = "Check the bead ledger file for corruption or permission issues."


class BeadValidationError(StoreError):
    """Raised when a bead fails validation."""

    _suggestion = "The bead data is invalid. Check the bead structure and required fields."

    def __init__(
        self,
        message: str,
        bead_id: str | None = None,
        field: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.bead_id = bead_id
        self.field = field


class DuplicateBeadError(StoreError):
    """Raised when attempting to insert a duplicate bead."""

    _suggestion = (
        "A bead with this idempotency key already exists. "
        "This is expected during retries - the operation was already completed."
    )

    def __init__(
        self,
        message: str,
        idempotency_key: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.idempotency_key = idempotency_key


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigError(AdversarialDebateError):
    """Base class for configuration errors."""

    _suggestion = "Check your configuration file or environment variables."


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    _suggestion = (
        "The configuration value is invalid. Check the configuration schema for valid options."
    )

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.field = field
        self.value = value

        # Generate specific suggestion
        if field and value is not None:
            self._custom_suggestion = (
                f"Invalid value for '{field}': {value!r}. "
                f"See configuration schema for valid values."
            )


class ConfigNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""

    _suggestion = (
        "The configuration file was not found. "
        "Create the file or use --config to specify a different path."
    )

    def __init__(
        self,
        message: str,
        path: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, details, suggestion)
        self.path = path

        if path:
            self._custom_suggestion = (
                f"Configuration file not found: {path}\n"
                f"Create the file or run without --config to use defaults."
            )


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
