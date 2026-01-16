"""Unit tests for exception hierarchy."""

import pytest

from adversarial_debate.exceptions import (
    AdversarialDebateError,
    AgentError,
    AgentExecutionError,
    AgentParseError,
    AgentTimeoutError,
    ProviderError,
    ProviderRateLimitError,
    ProviderConnectionError,
    ProviderAuthenticationError,
    SandboxError,
    SandboxExecutionError,
    SandboxTimeoutError,
    SandboxSecurityError,
    StoreError,
    BeadValidationError,
    DuplicateBeadError,
    ConfigError,
    ConfigValidationError,
    ConfigNotFoundError,
)


class TestAdversarialDebateError:
    """Tests for base exception."""

    def test_message_only(self) -> None:
        """Test exception with message only."""
        exc = AdversarialDebateError("Something went wrong")
        assert str(exc) == "Something went wrong"
        assert exc.message == "Something went wrong"
        assert exc.details == {}

    def test_with_details(self) -> None:
        """Test exception with details."""
        exc = AdversarialDebateError(
            "Error occurred",
            details={"file": "test.py", "line": 42},
        )
        assert "test.py" in str(exc)
        assert exc.details["file"] == "test.py"

    def test_inheritance(self) -> None:
        """Test exception inheritance."""
        exc = AdversarialDebateError("test")
        assert isinstance(exc, Exception)


class TestAgentErrors:
    """Tests for agent error hierarchy."""

    def test_agent_error(self) -> None:
        """Test base agent error."""
        exc = AgentError("Agent failed", agent_name="ExploitAgent")
        assert exc.agent_name == "ExploitAgent"
        assert "Agent failed" in str(exc)

    def test_agent_execution_error(self) -> None:
        """Test agent execution error."""
        exc = AgentExecutionError(
            "Execution failed",
            agent_name="BreakAgent",
            details={"context_id": "ctx-123"},
        )
        assert isinstance(exc, AgentError)
        assert isinstance(exc, AdversarialDebateError)

    def test_agent_parse_error(self) -> None:
        """Test agent parse error."""
        exc = AgentParseError(
            "Failed to parse response",
            agent_name="Arbiter",
            raw_response="invalid json",
        )
        assert exc.raw_response == "invalid json"
        assert exc.agent_name == "Arbiter"

    def test_agent_timeout_error(self) -> None:
        """Test agent timeout error."""
        exc = AgentTimeoutError(
            "Operation timed out",
            agent_name="ChaosAgent",
            timeout_seconds=30.0,
        )
        assert exc.timeout_seconds == 30.0


class TestProviderErrors:
    """Tests for provider error hierarchy."""

    def test_provider_error(self) -> None:
        """Test base provider error."""
        exc = ProviderError("API error", provider_name="anthropic")
        assert exc.provider_name == "anthropic"

    def test_rate_limit_error(self) -> None:
        """Test rate limit error."""
        exc = ProviderRateLimitError(
            "Rate limited",
            provider_name="openai",
            retry_after_seconds=60.0,
        )
        assert exc.retry_after_seconds == 60.0
        assert isinstance(exc, ProviderError)

    def test_connection_error(self) -> None:
        """Test connection error."""
        exc = ProviderConnectionError(
            "Failed to connect",
            provider_name="anthropic",
        )
        assert isinstance(exc, ProviderError)

    def test_authentication_error(self) -> None:
        """Test authentication error."""
        exc = ProviderAuthenticationError(
            "Invalid API key",
            provider_name="anthropic",
        )
        assert isinstance(exc, ProviderError)


class TestSandboxErrors:
    """Tests for sandbox error hierarchy."""

    def test_sandbox_error(self) -> None:
        """Test base sandbox error."""
        exc = SandboxError("Sandbox failed")
        assert isinstance(exc, AdversarialDebateError)

    def test_execution_error(self) -> None:
        """Test sandbox execution error."""
        exc = SandboxExecutionError(
            "Code execution failed",
            exit_code=1,
            stdout="output",
            stderr="error message",
        )
        assert exc.exit_code == 1
        assert exc.stdout == "output"
        assert exc.stderr == "error message"

    def test_sandbox_timeout_error(self) -> None:
        """Test sandbox timeout error."""
        exc = SandboxTimeoutError(
            "Execution timed out",
            timeout_seconds=10.0,
        )
        assert exc.timeout_seconds == 10.0

    def test_security_error(self) -> None:
        """Test sandbox security error."""
        exc = SandboxSecurityError(
            "Security violation detected",
            violation_type="file_system_access",
        )
        assert exc.violation_type == "file_system_access"


class TestStoreErrors:
    """Tests for store error hierarchy."""

    def test_store_error(self) -> None:
        """Test base store error."""
        exc = StoreError("Store operation failed")
        assert isinstance(exc, AdversarialDebateError)

    def test_bead_validation_error(self) -> None:
        """Test bead validation error."""
        exc = BeadValidationError(
            "Invalid bead",
            bead_id="B-123",
            field="confidence",
        )
        assert exc.bead_id == "B-123"
        assert exc.field == "confidence"

    def test_duplicate_bead_error(self) -> None:
        """Test duplicate bead error."""
        exc = DuplicateBeadError(
            "Bead already exists",
            idempotency_key="IK-test-001",
        )
        assert exc.idempotency_key == "IK-test-001"


class TestConfigErrors:
    """Tests for config error hierarchy."""

    def test_config_error(self) -> None:
        """Test base config error."""
        exc = ConfigError("Configuration error")
        assert isinstance(exc, AdversarialDebateError)

    def test_config_validation_error(self) -> None:
        """Test config validation error."""
        exc = ConfigValidationError(
            "Invalid value",
            field="timeout",
            value=-1,
        )
        assert exc.field == "timeout"
        assert exc.value == -1

    def test_config_not_found_error(self) -> None:
        """Test config not found error."""
        exc = ConfigNotFoundError(
            "Config file not found",
            path="/path/to/config.json",
        )
        assert exc.path == "/path/to/config.json"


class TestExceptionHierarchy:
    """Tests for exception hierarchy relationships."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test all exceptions inherit from AdversarialDebateError."""
        exceptions = [
            AgentError("test"),
            AgentExecutionError("test"),
            AgentParseError("test"),
            AgentTimeoutError("test"),
            ProviderError("test"),
            ProviderRateLimitError("test"),
            ProviderConnectionError("test"),
            ProviderAuthenticationError("test"),
            SandboxError("test"),
            SandboxExecutionError("test"),
            SandboxTimeoutError("test"),
            SandboxSecurityError("test"),
            StoreError("test"),
            BeadValidationError("test"),
            DuplicateBeadError("test"),
            ConfigError("test"),
            ConfigValidationError("test"),
            ConfigNotFoundError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, AdversarialDebateError)
            assert isinstance(exc, Exception)

    def test_can_catch_specific(self) -> None:
        """Test catching specific exception types."""
        with pytest.raises(AgentParseError):
            raise AgentParseError("test")

    def test_can_catch_parent(self) -> None:
        """Test catching parent exception type."""
        with pytest.raises(AgentError):
            raise AgentParseError("test")

    def test_can_catch_base(self) -> None:
        """Test catching base exception type."""
        with pytest.raises(AdversarialDebateError):
            raise ConfigNotFoundError("test")
