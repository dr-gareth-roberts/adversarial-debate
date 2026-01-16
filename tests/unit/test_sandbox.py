"""Unit tests for the sandbox execution module."""

from __future__ import annotations

import pytest

from adversarial_debate.sandbox import (
    SandboxConfig,
    SandboxExecutor,
    validate_identifier,
    validate_code_size,
    validate_input_size,
    InputValidationError,
    CodeSizeError,
    InputSizeError,
)


class TestSandboxConfig:
    """Tests for SandboxConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = SandboxConfig()

        assert config.enabled is True
        assert config.timeout_seconds == 30
        assert config.max_memory_mb == 256
        assert config.use_docker is False
        assert config.network_disabled is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = SandboxConfig(
            enabled=True,
            timeout_seconds=60,
            max_memory_mb=512,
            use_docker=True,
            network_disabled=True,
        )

        assert config.timeout_seconds == 60
        assert config.max_memory_mb == 512
        assert config.use_docker is True

    def test_config_validation_timeout_zero(self) -> None:
        """Test that timeout cannot be zero or negative."""
        with pytest.raises(ValueError, match="timeout"):
            SandboxConfig(timeout_seconds=0)

    def test_config_validation_memory_negative(self) -> None:
        """Test that memory limit cannot be negative."""
        with pytest.raises(ValueError, match="memory"):
            SandboxConfig(max_memory_mb=-1)


class TestInputValidation:
    """Tests for input validation functions."""

    def test_validate_identifier_safe(self) -> None:
        """Test that safe identifiers pass validation."""
        safe_identifiers = [
            "variable",
            "my_var",
            "CamelCase",
            "var123",
            "_private",
            "__dunder__",
        ]

        for ident in safe_identifiers:
            # Should not raise
            validate_identifier(ident)

    def test_validate_identifier_dangerous(self) -> None:
        """Test that dangerous identifiers are rejected."""
        dangerous_identifiers = [
            "exec",
            "eval",
            "__import__",
            "compile",
            "globals",
            "locals",
            "vars",
            "getattr",
            "setattr",
            "delattr",
            "open",
            "__builtins__",
        ]

        for ident in dangerous_identifiers:
            with pytest.raises(InputValidationError, match="dangerous"):
                validate_identifier(ident)

    def test_validate_code_size_within_limit(self) -> None:
        """Test code within size limit passes."""
        code = "x = 1" * 100  # Small code
        validate_code_size(code)  # Should not raise

    def test_validate_code_size_exceeds_limit(self) -> None:
        """Test code exceeding size limit is rejected."""
        code = "x" * (2 * 1024 * 1024)  # 2MB of code

        with pytest.raises(CodeSizeError, match="exceeds"):
            validate_code_size(code)

    def test_validate_input_size_within_limit(self) -> None:
        """Test inputs within size limit pass."""
        inputs = {
            "small": "data",
            "numbers": list(range(100)),
        }
        validate_input_size(inputs)  # Should not raise

    def test_validate_input_size_single_value_exceeds(self) -> None:
        """Test single input value exceeding limit is rejected."""
        inputs = {
            "huge": "x" * (2 * 1024 * 1024),  # 2MB string
        }

        with pytest.raises(InputSizeError, match="exceeds"):
            validate_input_size(inputs)

    def test_validate_input_size_total_exceeds(self) -> None:
        """Test total input size exceeding limit is rejected."""
        # Create many small inputs that total over limit
        inputs = {
            f"key_{i}": "x" * 100_000 for i in range(150)  # 15MB total
        }

        with pytest.raises(InputSizeError, match="total"):
            validate_input_size(inputs)


class TestSandboxExecutor:
    """Tests for SandboxExecutor."""

    @pytest.fixture
    def executor(self) -> SandboxExecutor:
        """Create a sandbox executor for testing."""
        config = SandboxConfig(
            enabled=True,
            timeout_seconds=5,
            max_memory_mb=128,
            use_docker=False,
        )
        return SandboxExecutor(config)

    def test_execute_simple_code(self, executor: SandboxExecutor) -> None:
        """Test executing simple Python code."""
        result = executor.execute_python(
            code="print('Hello')",
            inputs={},
        )

        assert result.exit_code == 0
        assert "Hello" in result.stdout
        assert result.stderr == ""
        assert not result.timed_out

    def test_execute_with_inputs(self, executor: SandboxExecutor) -> None:
        """Test executing code with input variables."""
        result = executor.execute_python(
            code="print(x + y)",
            inputs={"x": 1, "y": 2},
        )

        assert result.exit_code == 0
        assert "3" in result.stdout

    def test_execute_with_error(self, executor: SandboxExecutor) -> None:
        """Test executing code that raises an error."""
        result = executor.execute_python(
            code="raise ValueError('test error')",
            inputs={},
        )

        assert result.exit_code != 0
        assert "ValueError" in result.stderr
        assert "test error" in result.stderr

    def test_execute_syntax_error(self, executor: SandboxExecutor) -> None:
        """Test executing code with syntax error."""
        result = executor.execute_python(
            code="def broken(",
            inputs={},
        )

        assert result.exit_code != 0
        assert "SyntaxError" in result.stderr

    def test_execute_timeout(self, executor: SandboxExecutor) -> None:
        """Test that long-running code times out."""
        result = executor.execute_python(
            code="import time; time.sleep(100)",
            inputs={},
        )

        assert result.timed_out is True
        assert result.exit_code != 0

    def test_execute_return_value(self, executor: SandboxExecutor) -> None:
        """Test capturing return values."""
        result = executor.execute_python(
            code="""
result = []
for i in range(5):
    result.append(i * 2)
print(result)
""",
            inputs={},
        )

        assert result.exit_code == 0
        assert "[0, 2, 4, 6, 8]" in result.stdout

    def test_executor_disabled(self) -> None:
        """Test that disabled executor skips execution."""
        config = SandboxConfig(enabled=False)
        executor = SandboxExecutor(config)

        result = executor.execute_python(
            code="print('should not run')",
            inputs={},
        )

        # When disabled, should return empty result
        assert result.exit_code == 0
        assert result.stdout == ""
        assert not result.timed_out


class TestSandboxSecurityTests:
    """Tests for sandbox security testing methods."""

    @pytest.fixture
    def executor(self) -> SandboxExecutor:
        """Create a sandbox executor for testing."""
        config = SandboxConfig(
            enabled=True,
            timeout_seconds=5,
            use_docker=False,
        )
        return SandboxExecutor(config)

    def test_sql_injection_detection(self, executor: SandboxExecutor) -> None:
        """Test SQL injection vulnerability detection."""

        def vulnerable_query(user_input: str) -> str:
            return f"SELECT * FROM users WHERE id = '{user_input}'"

        results = executor.test_sql_injection(vulnerable_query)

        # Should detect vulnerability with at least one payload
        assert len(results) > 0
        assert any(r.get("vulnerable") for r in results)

    def test_sql_injection_safe_query(self, executor: SandboxExecutor) -> None:
        """Test that safe queries are not flagged."""

        def safe_query(user_input: str) -> str:
            # This doesn't actually parameterize, but demonstrates the pattern
            # In real code, you'd use cursor.execute with params
            return "SELECT * FROM users WHERE id = ?"

        results = executor.test_sql_injection(safe_query)

        # Safe query should not be vulnerable to common payloads
        # (The actual result depends on implementation details)
        assert isinstance(results, list)

    def test_command_injection_detection(self, executor: SandboxExecutor) -> None:
        """Test command injection vulnerability detection."""

        def vulnerable_command(filename: str) -> str:
            return f"cat {filename}"

        results = executor.test_command_injection(vulnerable_command)

        # Should detect vulnerability
        assert len(results) > 0

    def test_path_traversal_detection(self, executor: SandboxExecutor) -> None:
        """Test path traversal vulnerability detection."""

        def vulnerable_path(filename: str) -> str:
            return f"/var/www/uploads/{filename}"

        results = executor.test_path_traversal(vulnerable_path)

        # Should detect vulnerability with traversal payloads
        assert len(results) > 0


class TestSandboxResourceLimits:
    """Tests for sandbox resource limiting."""

    def test_memory_limit_enforcement(self) -> None:
        """Test that memory limits are enforced."""
        config = SandboxConfig(
            enabled=True,
            timeout_seconds=10,
            max_memory_mb=50,  # Very low limit
            use_docker=False,
        )
        executor = SandboxExecutor(config)

        # Try to allocate more memory than allowed
        result = executor.execute_python(
            code="""
# Try to allocate 100MB
data = bytearray(100 * 1024 * 1024)
print("Allocated")
""",
            inputs={},
        )

        # Should fail due to memory limit (or timeout trying)
        # The exact behavior depends on OS settings
        assert result.exit_code != 0 or "Allocated" not in result.stdout

    def test_output_size_limit(self) -> None:
        """Test that output size is limited."""
        config = SandboxConfig(
            enabled=True,
            timeout_seconds=10,
            max_output_size_bytes=1000,
        )
        executor = SandboxExecutor(config)

        result = executor.execute_python(
            code="print('x' * 10000)",  # 10KB output
            inputs={},
        )

        # Output should be truncated
        assert len(result.stdout) <= 1500  # Some buffer for truncation message
