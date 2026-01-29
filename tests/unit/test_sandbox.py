"""Unit tests for the sandbox execution module."""

from __future__ import annotations

import sys

import pytest

from adversarial_debate.sandbox import (
    MAX_CODE_SIZE,
    SandboxConfig,
    SandboxExecutor,
    SandboxSecurityError,
    validate_code_size,
    validate_identifier,
    validate_inputs,
    validate_sandbox_config,
)


class TestSandboxConfig:
    """Tests for SandboxConfig."""

    def test_default_config(self) -> None:
        config = SandboxConfig()

        assert config.memory_limit == "256m"
        assert config.cpu_limit == 0.5
        assert config.timeout_seconds == 30

        assert config.network_enabled is False
        assert config.allowed_hosts == []

        assert config.read_only is True
        assert config.temp_size == "64m"

        assert config.use_docker is True
        assert config.docker_image == "python:3.11-slim"

        assert config.use_subprocess is True
        assert config.subprocess_timeout == 10

    def test_config_validation_rejects_timeout_zero(self) -> None:
        config = SandboxConfig(timeout_seconds=0)
        with pytest.raises(SandboxSecurityError):
            validate_sandbox_config(config)

    def test_config_validation_rejects_invalid_memory_format(self) -> None:
        config = SandboxConfig(memory_limit="256mb")
        with pytest.raises(SandboxSecurityError):
            validate_sandbox_config(config)


class TestInputValidation:
    """Tests for input validation functions."""

    def test_validate_identifier_safe(self) -> None:
        safe_identifiers = [
            "variable",
            "my_var",
            "CamelCase",
            "var123",
            "_private",
            "__dunder__",
        ]

        for ident in safe_identifiers:
            validate_identifier(ident)

    def test_validate_identifier_dangerous(self) -> None:
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
            with pytest.raises(SandboxSecurityError):
                validate_identifier(ident)

    def test_validate_code_size_within_limit(self) -> None:
        code = "x = 1\n" * 100
        validate_code_size(code)

    def test_validate_code_size_exceeds_limit(self) -> None:
        code = "x" * (MAX_CODE_SIZE + 1)
        with pytest.raises(SandboxSecurityError):
            validate_code_size(code)

    def test_validate_inputs_within_limit(self) -> None:
        inputs = {
            "small": "data",
            "numbers": list(range(100)),
        }
        validate_inputs(inputs)

    def test_validate_inputs_single_value_exceeds(self) -> None:
        inputs = {
            "huge": "x" * (2 * 1024 * 1024),  # > MAX_INPUT_VALUE_SIZE (1MB)
        }
        with pytest.raises(SandboxSecurityError):
            validate_inputs(inputs)


class TestSandboxExecutor:
    """Tests for SandboxExecutor."""

    @pytest.fixture
    def executor(self) -> SandboxExecutor:
        config = SandboxConfig(
            use_docker=False,
            use_subprocess=True,
            timeout_seconds=5,
        )
        return SandboxExecutor(config)

    async def test_execute_simple_code(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_python(
            "print('Hello')",
            inputs={},
        )

        assert result.exit_code == 0
        assert result.success is True
        assert "Hello" in result.output
        assert result.error == ""
        assert result.timed_out is False

    async def test_execute_with_inputs(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_python(
            "print(x + y)",
            inputs={"x": 1, "y": 2},
        )

        assert result.exit_code == 0
        assert "3" in result.output

    async def test_execute_with_error(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_python(
            "raise ValueError('test error')",
            inputs={},
        )

        assert result.exit_code != 0
        assert "ValueError" in result.error
        assert "test error" in result.error

    async def test_execute_syntax_error(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_python(
            "def broken(",
            inputs={},
        )

        assert result.exit_code != 0
        assert "SyntaxError" in result.error

    async def test_execute_timeout(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_python(
            "import time; time.sleep(100)",
            timeout=1,
            inputs={},
        )

        assert result.timed_out is True
        assert result.exit_code != 0

    async def test_no_backend_available(self) -> None:
        config = SandboxConfig(use_docker=False, use_subprocess=False)
        executor = SandboxExecutor(config)

        result = await executor.execute_python(
            "print('should not run')",
            inputs={},
        )

        assert result.success is False
        assert result.exit_code == 0
        assert result.output == ""
        assert "No execution backend available" in result.error


class TestSandboxResourceLimits:
    """Tests for sandbox resource limiting."""

    async def test_memory_limit_enforcement(self) -> None:
        if sys.platform == "darwin":
            pytest.skip("Subprocess memory limits are not reliably enforceable on macOS")

        config = SandboxConfig(
            use_docker=False,
            use_subprocess=True,
            timeout_seconds=10,
            memory_limit="50m",
        )
        executor = SandboxExecutor(config)

        result = await executor.execute_python(
            code="""
data = bytearray(100 * 1024 * 1024)  # 100MB
print("Allocated")
""",
            inputs={},
        )

        # Exact behavior varies by platform/limits, but it should not cleanly succeed.
        assert result.exit_code != 0 or "Allocated" not in result.output

    async def test_output_size_limit(self) -> None:
        config = SandboxConfig(
            use_docker=False,
            use_subprocess=True,
            timeout_seconds=10,
            max_output_size_bytes=1000,
        )
        executor = SandboxExecutor(config)

        result = await executor.execute_python(
            code="print('x' * 10000)",  # 10KB output
            inputs={},
        )

        assert len(result.output) <= 1500  # Buffer for truncation marker
