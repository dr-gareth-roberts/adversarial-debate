"""Sandbox executor for safely running adversarial proofs-of-concept.

This module provides isolated execution environments for testing exploits
without risking the host system.

Security hardening applied:
- Input validation for variable names and sizes
- Path validation to prevent traversal/injection
- Symlink detection before volume mounts
- Config value validation with regex patterns
- Atomic temp file handling
- SIGKILL for reliable process termination
"""

import asyncio
import contextlib
import json
import os
import re
import secrets
import signal
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..exceptions import SandboxSecurityError

__all__ = [
    "ExecutionResult",
    "SandboxConfig",
    "SandboxExecutor",
    "SandboxSecurityError",
    "validate_sandbox_config",
]

# =============================================================================
# SECURITY CONSTANTS AND VALIDATORS
# =============================================================================

# Maximum allowed sizes to prevent memory exhaustion
MAX_CODE_SIZE = 1024 * 1024  # 1MB
MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB total for all inputs
MAX_INPUT_KEY_LENGTH = 64
MAX_INPUT_VALUE_SIZE = 1024 * 1024  # 1MB per value

# Valid Python identifier pattern (prevents code injection via variable names)
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Valid Docker resource limit patterns
MEMORY_LIMIT_PATTERN = re.compile(r"^\d+[kmgKMG]?$")
TEMP_SIZE_PATTERN = re.compile(r"^\d+[kmgKMG]?$")
DOCKER_IMAGE_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]*:[a-zA-Z0-9._-]+$")


def _parse_size_bytes(value: str) -> int:
    """Parse sizes like '256m' / '1g' into bytes."""
    match = re.fullmatch(r"(\d+)([kmgKMG]?)", value.strip())
    if not match:
        raise ValueError(f"Invalid size format: {value!r}")
    amount = int(match.group(1))
    unit = match.group(2).lower()
    multiplier = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[unit]
    return amount * multiplier


async def _read_stream_limited(
    stream: asyncio.StreamReader | None, limit_bytes: int
) -> tuple[bytes, bool]:
    """Read a stream fully but retain at most limit_bytes."""
    if stream is None:
        return b"", False

    data = bytearray()
    truncated = False

    while True:
        chunk = await stream.read(65536)
        if not chunk:
            break

        if len(data) < limit_bytes:
            remaining = limit_bytes - len(data)
            data.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True
        else:
            truncated = True
            # Drain without buffering.

    return bytes(data), truncated


def _decode_and_mark(
    data: bytes,
    truncated: bool,
    *,
    stream_name: str,
    prefix: str = "",
) -> str:
    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += f"\n[{stream_name} truncated]\n"
    return f"{prefix}{text}" if prefix else text


def validate_identifier(name: str, context: str = "identifier") -> None:
    """Validate that a string is a safe Python identifier.

    Args:
        name: The identifier to validate
        context: Description for error messages

    Raises:
        SandboxSecurityError: If validation fails
    """
    if not name:
        raise SandboxSecurityError(f"Empty {context} not allowed")
    if len(name) > MAX_INPUT_KEY_LENGTH:
        raise SandboxSecurityError(f"{context} too long: {len(name)} > {MAX_INPUT_KEY_LENGTH}")
    if not SAFE_IDENTIFIER_PATTERN.match(name):
        raise SandboxSecurityError(
            f"Invalid {context}: must be valid Python identifier, got {name!r}"
        )
    # Block Python keywords and builtins that could be dangerous
    dangerous_names = {
        "exec",
        "eval",
        "compile",
        "open",
        "input",
        "__import__",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        "__builtins__",
        "__name__",
        "__file__",
    }
    if name in dangerous_names:
        raise SandboxSecurityError(f"Dangerous {context} name: {name!r}")


def validate_code_size(code: str) -> None:
    """Validate code is within size limits.

    Args:
        code: The code string to validate

    Raises:
        SandboxSecurityError: If code exceeds size limit
    """
    if len(code.encode("utf-8")) > MAX_CODE_SIZE:
        raise SandboxSecurityError(
            f"Code too large: {len(code.encode('utf-8'))} > {MAX_CODE_SIZE} bytes"
        )


def validate_inputs(inputs: dict[str, Any] | None) -> None:
    """Validate input dictionary for safety.

    Args:
        inputs: Dictionary of inputs to inject

    Raises:
        SandboxSecurityError: If validation fails
    """
    if inputs is None:
        return

    total_size = 0
    for key, value in inputs.items():
        # Validate key is safe identifier
        validate_identifier(key, "input key")

        # Validate value size
        try:
            serialized = json.dumps(value)
            value_size = len(serialized.encode("utf-8"))
            if value_size > MAX_INPUT_VALUE_SIZE:
                raise SandboxSecurityError(
                    f"Input value for '{key}' too large: {value_size} > {MAX_INPUT_VALUE_SIZE}"
                )
            total_size += value_size
        except (TypeError, ValueError) as e:
            raise SandboxSecurityError(f"Input value for '{key}' not JSON serializable: {e}") from e

    if total_size > MAX_INPUT_SIZE:
        raise SandboxSecurityError(f"Total input size too large: {total_size} > {MAX_INPUT_SIZE}")


def validate_path_for_mount(path: Path) -> None:
    """Validate a path is safe for Docker volume mount.

    Checks:
    - Path exists and is a regular file
    - Path is not a symlink (prevents symlink attacks)
    - Path is absolute
    - Path doesn't contain suspicious characters

    Args:
        path: Path to validate

    Raises:
        SandboxSecurityError: If validation fails
    """
    if not path.is_absolute():
        raise SandboxSecurityError(f"Path must be absolute: {path}")

    # Check for path traversal attempts in the string
    path_str = str(path)
    if ".." in path_str:
        raise SandboxSecurityError(f"Path traversal detected: {path}")

    # Check for shell metacharacters that could enable injection
    dangerous_chars = set(";&|`$(){}[]<>\\'\"")
    if any(c in path_str for c in dangerous_chars):
        raise SandboxSecurityError(f"Dangerous characters in path: {path}")

    # Check path exists
    if not path.exists():
        raise SandboxSecurityError(f"Path does not exist: {path}")

    # Check it's a regular file, not a symlink
    if path.is_symlink():
        raise SandboxSecurityError(f"Symlinks not allowed: {path}")

    if not path.is_file():
        raise SandboxSecurityError(f"Path is not a regular file: {path}")


def validate_test_params(
    function_name: str | None = None,
    param_name: str | None = None,
    argument_name: str | None = None,
) -> None:
    """Validate parameters used in test methods.

    These parameters are interpolated into executable code strings,
    so they must be valid Python identifiers to prevent code injection.

    Args:
        function_name: Name of function to test
        param_name: Name of parameter to inject
        argument_name: Name of argument to inject

    Raises:
        SandboxSecurityError: If any parameter is invalid
    """
    if function_name is not None:
        validate_identifier(function_name, "function_name")
    if param_name is not None:
        validate_identifier(param_name, "param_name")
    if argument_name is not None:
        validate_identifier(argument_name, "argument_name")


def generate_secure_temp_name(prefix: str = "sandbox") -> str:
    """Generate a secure random temp filename.

    Uses cryptographically secure randomness instead of predictable
    values like pid or object id.

    Args:
        prefix: Prefix for the filename

    Returns:
        Secure filename like 'sandbox_a1b2c3d4e5f6.py'
    """
    random_part = secrets.token_hex(8)  # 16 hex chars = 64 bits of randomness
    return f"{prefix}_{random_part}.py"


def validate_sandbox_config(config: "SandboxConfig") -> None:
    """Validate SandboxConfig values are safe.

    Args:
        config: Configuration to validate

    Raises:
        SandboxSecurityError: If validation fails
    """
    # Validate memory limit format
    if not MEMORY_LIMIT_PATTERN.match(config.memory_limit):
        raise SandboxSecurityError(f"Invalid memory_limit format: {config.memory_limit}")

    # Validate temp size format
    if not TEMP_SIZE_PATTERN.match(config.temp_size):
        raise SandboxSecurityError(f"Invalid temp_size format: {config.temp_size}")

    # Validate CPU limit range
    if not 0.0 < config.cpu_limit <= 16.0:
        raise SandboxSecurityError(f"cpu_limit must be in (0, 16], got {config.cpu_limit}")

    # Validate timeout range
    if not 1 <= config.timeout_seconds <= 300:
        raise SandboxSecurityError(
            f"timeout_seconds must be in [1, 300], got {config.timeout_seconds}"
        )

    if not 1 <= config.subprocess_timeout <= 60:
        raise SandboxSecurityError(
            f"subprocess_timeout must be in [1, 60], got {config.subprocess_timeout}"
        )

    # Validate Docker image format (prevent injection)
    if config.use_docker and not DOCKER_IMAGE_PATTERN.match(config.docker_image):
        raise SandboxSecurityError(f"Invalid docker_image format: {config.docker_image}")

    # Validate allowed hosts don't contain injection attempts
    for host in config.allowed_hosts:
        if not re.match(r"^[a-zA-Z0-9.-]+$", host):
            raise SandboxSecurityError(f"Invalid allowed_host format: {host}")

    # Avoid a false sense of safety: allowlisting is not enforced.
    if config.network_enabled and config.allowed_hosts:
        raise SandboxSecurityError(
            "allowed_hosts is not enforced when network_enabled=True; "
            "either disable network or leave allowed_hosts empty"
        )

    if config.max_output_size_bytes <= 0:
        raise SandboxSecurityError(
            f"max_output_size_bytes must be > 0, got {config.max_output_size_bytes}"
        )


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    # Resource limits
    memory_limit: str = "256m"
    cpu_limit: float = 0.5
    timeout_seconds: int = 30
    max_output_size_bytes: int = 1024 * 1024  # 1MB per stream (stdout/stderr)

    # Network policy
    network_enabled: bool = False
    allowed_hosts: list[str] = field(default_factory=list)

    # Filesystem
    read_only: bool = True
    temp_size: str = "64m"

    # Docker settings (if using Docker)
    use_docker: bool = True
    docker_image: str = "python:3.11-slim"

    # Fallback settings (if Docker not available)
    use_subprocess: bool = True
    subprocess_timeout: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "timeout_seconds": self.timeout_seconds,
            "max_output_size_bytes": self.max_output_size_bytes,
            "network_enabled": self.network_enabled,
            "allowed_hosts": self.allowed_hosts,
            "read_only": self.read_only,
            "temp_size": self.temp_size,
            "use_docker": self.use_docker,
            "docker_image": self.docker_image,
            "use_subprocess": self.use_subprocess,
            "subprocess_timeout": self.subprocess_timeout,
        }


@dataclass
class ExecutionResult:
    """Result from sandbox execution."""

    success: bool
    output: str
    error: str = ""
    exit_code: int = 0
    timed_out: bool = False
    resource_exceeded: bool = False
    execution_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "resource_exceeded": self.resource_exceeded,
            "execution_time_ms": self.execution_time_ms,
        }


class SandboxExecutor:
    """Execute code and exploits in isolated sandbox environments.

    Supports multiple execution backends:
    1. Docker (preferred) - Full isolation
    2. Subprocess (fallback) - Limited isolation but no Docker required

    Security measures:
    - All inputs validated before use
    - Paths checked for symlinks and traversal
    - Resource limits enforced
    - Process termination uses SIGKILL
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        # Validate config on creation to fail fast
        validate_sandbox_config(self.config)
        self._docker_available: bool | None = None

    def is_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
        if self._docker_available is not None:
            return self._docker_available

        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=5,
            )
            self._docker_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._docker_available = False

        return self._docker_available

    async def execute_python(
        self,
        code: str,
        *,
        timeout: int | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute Python code in sandbox.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            inputs: Variables to inject into execution context

        Returns:
            ExecutionResult with output and status

        Raises:
            SandboxSecurityError: If input validation fails
        """
        # Validate inputs BEFORE any execution
        try:
            validate_code_size(code)
            validate_inputs(inputs)
        except SandboxSecurityError as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Security validation failed: {e}",
            )

        timeout = timeout or self.config.timeout_seconds

        if self.config.use_docker and self.is_docker_available():
            return await self._execute_docker_python(code, timeout, inputs)
        elif self.config.use_subprocess:
            return await self._execute_subprocess_python(code, timeout, inputs)
        else:
            return ExecutionResult(
                success=False,
                output="",
                error="No execution backend available",
            )

    async def execute_exploit(
        self,
        target_code: str,
        exploit_code: str,
        *,
        timeout: int | None = None,
    ) -> ExecutionResult:
        """Execute an exploit against target code.

        This creates a combined script that:
        1. Defines the target code
        2. Runs the exploit against it
        3. Captures the result

        Args:
            target_code: The code being tested
            exploit_code: The exploit to run
            timeout: Execution timeout

        Returns:
            ExecutionResult indicating if exploit succeeded
        """
        combined_code = f"""
# Target code
{target_code}

# Exploit
try:
    {exploit_code}
    print("EXPLOIT_SUCCESS")
except Exception as e:
    print(f"EXPLOIT_FAILED: {{e}}")
"""
        return await self.execute_python(combined_code, timeout=timeout)

    async def verify_finding(
        self,
        target_code: str,
        poc_code: str,
        expected_behavior: str,
    ) -> tuple[bool, str]:
        """Verify a finding by running its proof-of-concept.

        Args:
            target_code: The vulnerable code
            poc_code: Proof of concept code
            expected_behavior: What should happen if vulnerable

        Returns:
            Tuple of (verified: bool, explanation: str)
        """
        result = await self.execute_exploit(target_code, poc_code)

        if result.timed_out:
            return False, "PoC timed out - may indicate DoS vulnerability"

        if "EXPLOIT_SUCCESS" in result.output:
            return True, f"Vulnerability confirmed: {result.output}"

        if "EXPLOIT_FAILED" in result.output:
            return False, f"Exploit did not succeed: {result.output}"

        # Check for indicators of vulnerability
        vulnerability_indicators = [
            "Error",
            "Exception",
            "Traceback",
            "overflow",
            "segfault",
            "killed",
        ]

        for indicator in vulnerability_indicators:
            if indicator.lower() in result.output.lower():
                return True, f"Potential vulnerability indicated by: {indicator}"

        return False, f"Could not verify vulnerability. Output: {result.output[:500]}"

    async def _execute_docker_python(
        self,
        code: str,
        timeout: int,
        inputs: dict[str, Any] | None,
    ) -> ExecutionResult:
        """Execute Python code in Docker container.

        Security hardening:
        - Atomic temp file creation in secure directory
        - Path validation before volume mount (symlink detection)
        - SIGKILL for reliable process termination
        - Secure temp file permissions (0600)
        """
        import time

        start_time = time.monotonic()
        temp_file = None

        try:
            # Create temp file atomically with restricted permissions
            # Use os.open for atomic creation with secure permissions
            fd = None
            try:
                # Create in system temp directory with secure random name
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, generate_secure_temp_name("docker"))

                # O_CREAT | O_EXCL ensures atomic creation (fails if exists)
                # O_WRONLY for write-only
                # 0o600 = owner read/write only
                fd = os.open(temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                temp_file = temp_path

                # Write content via file descriptor
                content_lines = []
                if inputs:
                    for key, value in inputs.items():
                        # Keys already validated by validate_inputs
                        content_lines.append(f"{key} = {json.dumps(value)}")
                content_lines.append(code)
                content = "\n".join(content_lines)

                os.write(fd, content.encode("utf-8"))
            finally:
                if fd is not None:
                    os.close(fd)

            # Validate path BEFORE using in Docker command
            # This catches symlink attacks and path traversal
            temp_path_obj = Path(temp_file)
            validate_path_for_mount(temp_path_obj)

            # Build docker command - all values have been validated
            cmd = [
                "docker",
                "run",
                "--rm",
                f"--memory={self.config.memory_limit}",
                f"--cpus={self.config.cpu_limit}",
                "--network=none" if not self.config.network_enabled else "",
                "--read-only" if self.config.read_only else "",
                f"--tmpfs=/tmp:size={self.config.temp_size}",
                "--security-opt=no-new-privileges",
                # Use absolute path for volume mount (already validated)
                "-v",
                f"{temp_file}:/code/script.py:ro",
                self.config.docker_image,
                "python",
                "/code/script.py",
            ]
            # Filter out empty strings
            cmd = [c for c in cmd if c]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_task = asyncio.create_task(
                _read_stream_limited(proc.stdout, self.config.max_output_size_bytes)
            )
            stderr_task = asyncio.create_task(
                _read_stream_limited(proc.stderr, self.config.max_output_size_bytes)
            )

            timed_out = False
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except TimeoutError:
                # Use SIGKILL for reliable termination (SIGTERM may be ignored)
                with contextlib.suppress(ProcessLookupError):
                    proc.send_signal(signal.SIGKILL)
                await proc.wait()
                timed_out = True

            stdout, stdout_truncated = await stdout_task
            stderr, stderr_truncated = await stderr_task
            elapsed = int((time.monotonic() - start_time) * 1000)

            if timed_out:
                return ExecutionResult(
                    success=False,
                    output=_decode_and_mark(stdout, stdout_truncated, stream_name="stdout"),
                    error=_decode_and_mark(
                        stderr,
                        stderr_truncated,
                        stream_name="stderr",
                        prefix=f"Execution timed out after {timeout}s\n",
                    ),
                    exit_code=-1,
                    timed_out=True,
                    execution_time_ms=elapsed,
                )

            return ExecutionResult(
                success=proc.returncode == 0,
                output=_decode_and_mark(stdout, stdout_truncated, stream_name="stdout"),
                error=_decode_and_mark(stderr, stderr_truncated, stream_name="stderr"),
                exit_code=proc.returncode or 0,
                timed_out=False,
                execution_time_ms=elapsed,
            )

        except SandboxSecurityError as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Security validation failed: {e}",
            )
        finally:
            # Clean up temp file securely
            if temp_file:
                with contextlib.suppress(OSError):
                    os.unlink(temp_file)

    async def _execute_subprocess_python(
        self,
        code: str,
        timeout: int,
        inputs: dict[str, Any] | None,
    ) -> ExecutionResult:
        """Execute Python code in subprocess (less isolated fallback).

        Security hardening:
        - Atomic temp file creation with secure permissions
        - Input validation already performed by caller
        - SIGKILL for reliable process termination
        - Resource limits via setrlimit
        """
        import time

        start_time = time.monotonic()
        temp_file = None

        try:
            # Create temp file atomically with restricted permissions
            fd = None
            try:
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, generate_secure_temp_name("subprocess"))

                # O_CREAT | O_EXCL ensures atomic creation (fails if exists)
                fd = os.open(temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                temp_file = temp_path

                # Write content via file descriptor
                content_lines = []
                if inputs:
                    for key, value in inputs.items():
                        # Keys already validated by validate_inputs
                        content_lines.append(f"{key} = {json.dumps(value)}")
                content_lines.append(code)
                content = "\n".join(content_lines)

                os.write(fd, content.encode("utf-8"))
            finally:
                if fd is not None:
                    os.close(fd)

            # Use resource limits if available (Unix only)
            preexec_fn = None
            try:
                import resource
            except ImportError:  # pragma: no cover (Windows)
                resource = None  # type: ignore[assignment]

            if resource is not None:
                memory_bytes = _parse_size_bytes(self.config.memory_limit)

                def set_limits() -> None:
                    # Address space / virtual memory cap (best-effort; not supported everywhere).
                    try:
                        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                    except (OSError, ValueError):
                        # Some platforms (notably macOS) may reject RLIMIT_AS/RLIMIT_DATA changes.
                        with contextlib.suppress(OSError, ValueError, AttributeError):
                            resource.setrlimit(resource.RLIMIT_DATA, (memory_bytes, memory_bytes))

                    # Limit CPU time (generally supported).
                    with contextlib.suppress(OSError, ValueError):
                        resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 1))

                preexec_fn = set_limits

            proc = await asyncio.create_subprocess_exec(
                "python3",
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=preexec_fn,
            )

            stdout_task = asyncio.create_task(
                _read_stream_limited(proc.stdout, self.config.max_output_size_bytes)
            )
            stderr_task = asyncio.create_task(
                _read_stream_limited(proc.stderr, self.config.max_output_size_bytes)
            )

            timed_out = False
            try:
                await asyncio.wait_for(
                    proc.wait(),
                    timeout=min(timeout, self.config.subprocess_timeout),
                )
            except TimeoutError:
                # Use SIGKILL for reliable termination (SIGTERM may be ignored)
                with contextlib.suppress(ProcessLookupError):
                    proc.send_signal(signal.SIGKILL)
                await proc.wait()
                timed_out = True

            stdout, stdout_truncated = await stdout_task
            stderr, stderr_truncated = await stderr_task
            elapsed = int((time.monotonic() - start_time) * 1000)

            if timed_out:
                return ExecutionResult(
                    success=False,
                    output=_decode_and_mark(stdout, stdout_truncated, stream_name="stdout"),
                    error=_decode_and_mark(
                        stderr,
                        stderr_truncated,
                        stream_name="stderr",
                        prefix=f"Execution timed out after {timeout}s\n",
                    ),
                    exit_code=-1,
                    timed_out=True,
                    execution_time_ms=elapsed,
                )

            return ExecutionResult(
                success=proc.returncode == 0,
                output=_decode_and_mark(stdout, stdout_truncated, stream_name="stdout"),
                error=_decode_and_mark(stderr, stderr_truncated, stream_name="stderr"),
                exit_code=proc.returncode or 0,
                timed_out=False,
                execution_time_ms=elapsed,
            )

        finally:
            # Clean up temp file securely
            if temp_file:
                with contextlib.suppress(OSError):
                    os.unlink(temp_file)

    async def test_boundary_value(
        self,
        target_code: str,
        function_name: str,
        argument_name: str,
        test_value: Any,
    ) -> ExecutionResult:
        """Test a function with a boundary value.

        Args:
            target_code: The code containing the function
            function_name: Name of function to test
            argument_name: Name of argument to inject value into
            test_value: The boundary value to test

        Returns:
            ExecutionResult from the test
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name, argument_name=argument_name)

        test_code = f"""
{target_code}

# Test with boundary value
try:
    result = {function_name}({argument_name}={json.dumps(test_value)})
    print(f"RESULT: {{result}}")
except Exception as e:
    print(f"EXCEPTION: {{type(e).__name__}}: {{e}}")
"""
        return await self.execute_python(test_code)

    async def test_concurrency(
        self,
        target_code: str,
        function_name: str,
        num_concurrent: int = 10,
    ) -> ExecutionResult:
        """Test a function for race conditions.

        Args:
            target_code: The code containing the function
            function_name: Name of function to test
            num_concurrent: Number of concurrent calls

        Returns:
            ExecutionResult from the test
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)

        test_code = f"""
import asyncio
import threading

{target_code}

results = []
errors = []

def call_function():
    try:
        result = {function_name}()
        results.append(result)
    except Exception as e:
        errors.append(str(e))

# Run concurrent calls
threads = [threading.Thread(target=call_function) for _ in range({num_concurrent})]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"RESULTS: {{len(results)}} successes, {{len(errors)}} errors")
if errors:
    print(f"ERRORS: {{errors[:5]}}")
"""
        return await self.execute_python(test_code, timeout=30)

    # =========================================================================
    # SECURITY EXPLOIT VALIDATION METHODS
    # =========================================================================

    async def test_sql_injection(
        self,
        target_code: str,
        function_name: str,
        param_name: str,
        payloads: list[str] | None = None,
    ) -> ExecutionResult:
        """Test for SQL injection vulnerability.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function that executes SQL
            param_name: Name of parameter to inject payload into
            payloads: SQL injection payloads to try

        Returns:
            ExecutionResult indicating if injection was successful
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name, param_name=param_name)

        if payloads is None:
            payloads = [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "1 UNION SELECT * FROM users --",
            ]

        payloads_json = json.dumps(payloads)
        template = '''
import sqlite3

# Create test database
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
conn.executescript(
    """
    CREATE TABLE users (id INTEGER, name TEXT, password TEXT);
    INSERT INTO users VALUES (1, 'admin', 'secret123');
    INSERT INTO users VALUES (2, 'user', 'password');
    """
)
conn.commit()

__ADVERSARIAL_DEBATE_TARGET_CODE__

payloads = __ADVERSARIAL_DEBATE_PAYLOADS_JSON__
vulnerabilities_found = []

for payload in payloads:
    try:
        result = __ADVERSARIAL_DEBATE_FUNCTION_NAME__(__ADVERSARIAL_DEBATE_PARAM_NAME__=payload)
        # Check if we got more results than expected (injection success)
        if hasattr(result, "__len__") and len(result) > 1:
            vulnerabilities_found.append(f"Payload '{payload}' returned {len(result)} rows")
        elif result is not None:
            vulnerabilities_found.append(f"Payload '{payload}' executed successfully")
    except Exception as e:
        # SQL error might indicate partial injection
        if "syntax" in str(e).lower():
            print(f"SYNTAX_ERROR: {payload}")

if vulnerabilities_found:
    print("SQL_INJECTION_FOUND")
    for v in vulnerabilities_found:
        print(f"  {v}")
else:
    print("NO_INJECTION_FOUND")

conn.close()
'''
        test_code = (
            template.replace("__ADVERSARIAL_DEBATE_TARGET_CODE__", target_code)
            .replace("__ADVERSARIAL_DEBATE_PAYLOADS_JSON__", payloads_json)
            .replace("__ADVERSARIAL_DEBATE_FUNCTION_NAME__", function_name)
            .replace("__ADVERSARIAL_DEBATE_PARAM_NAME__", param_name)
        )
        return await self.execute_python(test_code)

    async def test_command_injection(
        self,
        target_code: str,
        function_name: str,
        param_name: str,
        payloads: list[str] | None = None,
    ) -> ExecutionResult:
        """Test for command injection vulnerability.

        Note: This runs in sandbox with restricted permissions.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function that executes commands
            param_name: Name of parameter to inject payload into
            payloads: Command injection payloads to try

        Returns:
            ExecutionResult indicating if injection was successful
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name, param_name=param_name)

        if payloads is None:
            payloads = [
                "; echo INJECTED",
                "| echo INJECTED",
                "$(echo INJECTED)",
                "`echo INJECTED`",
            ]

        test_code = f"""
import subprocess

{target_code}

payloads = {json.dumps(payloads)}
injection_found = False

for payload in payloads:
    try:
        result = {function_name}({param_name}=payload)
        output = str(result) if result else ""
        if "INJECTED" in output:
            print(f"COMMAND_INJECTION_FOUND: {{payload}}")
            injection_found = True
            break
    except Exception as e:
        pass  # Expected for some payloads

if not injection_found:
    print("NO_INJECTION_FOUND")
"""
        return await self.execute_python(test_code)

    async def test_path_traversal(
        self,
        target_code: str,
        function_name: str,
        param_name: str,
        payloads: list[str] | None = None,
    ) -> ExecutionResult:
        """Test for path traversal vulnerability.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function that reads files
            param_name: Name of parameter to inject path into
            payloads: Path traversal payloads to try

        Returns:
            ExecutionResult indicating if traversal was successful
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name, param_name=param_name)

        if payloads is None:
            payloads = [
                "../../../etc/passwd",
                "....//....//etc/passwd",
                "..\\\\..\\\\..\\\\etc\\\\passwd",
            ]

        test_code = f"""
import os
import tempfile

# Create a restricted directory structure for testing
with tempfile.TemporaryDirectory() as tmpdir:
    # Create allowed directory
    allowed_dir = os.path.join(tmpdir, "allowed")
    os.makedirs(allowed_dir)

    # Create a file outside allowed directory
    secret_file = os.path.join(tmpdir, "secret.txt")
    with open(secret_file, "w") as f:
        f.write("SECRET_DATA")

    # Create a file inside allowed directory
    allowed_file = os.path.join(allowed_dir, "public.txt")
    with open(allowed_file, "w") as f:
        f.write("PUBLIC_DATA")

    {target_code}

    payloads = {json.dumps(payloads)}
    traversal_found = False

    for payload in payloads:
        try:
            # Simulate reading relative to allowed_dir
            result = {function_name}({param_name}=payload)
            if result and "SECRET" in str(result):
                print(f"PATH_TRAVERSAL_FOUND: {{payload}}")
                traversal_found = True
                break
        except Exception as e:
            pass  # Expected for invalid paths

    if not traversal_found:
        print("NO_TRAVERSAL_FOUND")
"""
        return await self.execute_python(test_code)

    async def test_ssrf(
        self,
        target_code: str,
        function_name: str,
        param_name: str,
        payloads: list[str] | None = None,
    ) -> ExecutionResult:
        """Test for SSRF vulnerability.

        Note: Network is disabled in sandbox, so this tests URL validation.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function that makes HTTP requests
            param_name: Name of parameter containing URL
            payloads: SSRF payloads to try

        Returns:
            ExecutionResult indicating if SSRF is possible
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name, param_name=param_name)

        if payloads is None:
            payloads = [
                "http://localhost/admin",
                "http://127.0.0.1:22",
                "http://169.254.169.254/latest/meta-data/",
                "file:///etc/passwd",
            ]

        test_code = f"""
# Mock requests to track what URLs are attempted
attempted_urls = []

class MockResponse:
    def __init__(self, url):
        self.url = url
        self.status_code = 200
        self.text = "mock response"

def mock_get(url, *args, **kwargs):
    attempted_urls.append(url)
    return MockResponse(url)

# Patch requests
import sys
class MockRequests:
    get = staticmethod(mock_get)
    post = staticmethod(mock_get)

sys.modules['requests'] = MockRequests()

{target_code}

payloads = {json.dumps(payloads)}
ssrf_possible = []

for payload in payloads:
    attempted_urls.clear()
    try:
        {function_name}({param_name}=payload)
        # Check if internal URLs were attempted
        for url in attempted_urls:
            if any(x in url for x in ['localhost', '127.0.0.1', '169.254', 'file://']):
                ssrf_possible.append(f"Internal URL attempted: {{url}}")
    except Exception as e:
        pass  # May be expected

if ssrf_possible:
    print("SSRF_POSSIBLE")
    for s in ssrf_possible:
        print(f"  {{s}}")
else:
    print("NO_SSRF_FOUND")
"""
        return await self.execute_python(test_code)

    async def test_deserialization(
        self,
        target_code: str,
        function_name: str,
        param_name: str,
    ) -> ExecutionResult:
        """Test for insecure deserialization vulnerability.

        SECURITY NOTE: This method intentionally creates a pickle payload to TEST
        whether target code is vulnerable to deserialization attacks. The payload
        is benign (only calls print()) and executes in the sandbox. This is
        legitimate security testing functionality.

        The test works by:
        1. Creating a pickle payload with __reduce__ that calls print()
        2. Passing this payload to the target function
        3. If "PICKLE_EXECUTED" appears in output, the target is vulnerable

        Args:
            target_code: Code containing the function to test
            function_name: Name of function that deserializes data
            param_name: Name of parameter containing serialized data

        Returns:
            ExecutionResult indicating if insecure deserialization exists
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name, param_name=param_name)

        test_code = f"""
import pickle
import base64

# Create a pickle payload that would execute code if vulnerable
class MaliciousPickle:
    def __reduce__(self):
        return (print, ("PICKLE_EXECUTED",))

payload = base64.b64encode(pickle.dumps(MaliciousPickle())).decode()

{target_code}

try:
    result = {function_name}({param_name}=base64.b64decode(payload))
    print("DESERIALIZATION_COMPLETE")
except Exception as e:
    print(f"DESERIALIZATION_ERROR: {{e}}")
"""
        result = await self.execute_python(test_code)

        # Check if the pickle payload executed
        if "PICKLE_EXECUTED" in result.output:
            result.output = "INSECURE_DESERIALIZATION_FOUND\n" + result.output

        return result

    # =========================================================================
    # CHAOS ENGINEERING VALIDATION METHODS
    # =========================================================================

    async def test_dependency_failure(
        self,
        target_code: str,
        function_name: str,
        dependency_type: str,
        failure_mode: str = "unavailable",
    ) -> ExecutionResult:
        """Test how code handles dependency failures.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function that uses the dependency
            dependency_type: Type of dependency (database, cache, api)
            failure_mode: How the dependency fails (unavailable, timeout, error)

        Returns:
            ExecutionResult indicating how the code handled the failure
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)

        # Create mock that simulates the failure
        mock_behaviors = {
            "unavailable": "raise ConnectionRefusedError('Connection refused')",
            "timeout": "import time; time.sleep(100)  # Will timeout",
            "error": "raise RuntimeError('Service error: 500 Internal Server Error')",
            "corrupt": "return {'invalid': 'malformed response'}",
        }

        mock_behavior = mock_behaviors.get(failure_mode, mock_behaviors["unavailable"])

        test_code = f'''
import sys
from unittest.mock import MagicMock, patch

# Create mock that simulates {failure_mode}
def failing_mock(*args, **kwargs):
    {mock_behavior}

# Track if fallback/recovery was used
recovery_used = False
errors_caught = []

{target_code}

# Patch common dependency access patterns
patches = {{
    'database': ['connect', 'execute', 'cursor'],
    'cache': ['get', 'set', 'delete'],
    'api': ['get', 'post', 'request'],
}}

dependency_patterns = patches.get("{dependency_type}", ['connect'])

# Try calling the function
try:
    result = {function_name}()
    print(f"FUNCTION_RETURNED: {{result}}")
    print("DEPENDENCY_FAILURE_HANDLED: Function completed despite failure")
except ConnectionRefusedError as e:
    errors_caught.append(f"ConnectionRefusedError: {{e}}")
    print(f"UNHANDLED_CONNECTION_ERROR: {{e}}")
except TimeoutError as e:
    errors_caught.append(f"TimeoutError: {{e}}")
    print(f"UNHANDLED_TIMEOUT: {{e}}")
except Exception as e:
    errors_caught.append(f"{{type(e).__name__}}: {{e}}")
    print(f"UNHANDLED_ERROR: {{type(e).__name__}}: {{e}}")

if errors_caught:
    print(f"ERRORS: {{len(errors_caught)}} unhandled errors")
'''
        return await self.execute_python(test_code, timeout=15)

    async def test_timeout_handling(
        self,
        target_code: str,
        function_name: str,
        expected_timeout_seconds: float = 5.0,
    ) -> ExecutionResult:
        """Test if code properly times out on slow operations.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function to test
            expected_timeout_seconds: Expected timeout threshold

        Returns:
            ExecutionResult indicating timeout behavior
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)

        test_code = f"""
import time
import threading

# Create a slow mock
def slow_operation(*args, **kwargs):
    time.sleep(30)  # Longer than any reasonable timeout
    return "completed"

{target_code}

start_time = time.monotonic()
timed_out = False
completed = False

# Run in thread so we can monitor
def run_function():
    global completed
    try:
        result = {function_name}()
        completed = True
        print(f"COMPLETED: {{result}}")
    except TimeoutError:
        print("TIMEOUT_HANDLED: Function properly timed out")
    except Exception as e:
        print(f"ERROR: {{type(e).__name__}}: {{e}}")

thread = threading.Thread(target=run_function)
thread.start()
thread.join(timeout={expected_timeout_seconds + 2})

elapsed = time.monotonic() - start_time

if thread.is_alive():
    print(f"NO_TIMEOUT: Function still running after {{elapsed:.1f}}s")
    print("VULNERABILITY: No timeout protection")
elif elapsed > {expected_timeout_seconds}:
    print(f"SLOW_TIMEOUT: Took {{elapsed:.1f}}s (expected < {expected_timeout_seconds}s)")
else:
    print(f"TIMEOUT_OK: Completed in {{elapsed:.1f}}s")
"""
        return await self.execute_python(test_code, timeout=int(expected_timeout_seconds + 5))

    async def test_retry_behavior(
        self,
        target_code: str,
        function_name: str,
        failure_count: int = 3,
    ) -> ExecutionResult:
        """Test if code properly retries on transient failures.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function to test
            failure_count: Number of failures before success

        Returns:
            ExecutionResult indicating retry behavior
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)

        test_code = f"""
call_count = 0
FAILURE_COUNT = {failure_count}

# Mock that fails first N times, then succeeds
def flaky_operation(*args, **kwargs):
    global call_count
    call_count += 1
    if call_count <= FAILURE_COUNT:
        raise ConnectionError(f"Transient failure {{call_count}}/{{FAILURE_COUNT}}")
    return "success"

{target_code}

try:
    result = {function_name}()
    print(f"RESULT: {{result}}")
    print(f"ATTEMPTS: {{call_count}}")
    if call_count > FAILURE_COUNT:
        print("RETRY_WORKING: Function retried and eventually succeeded")
    else:
        print("NO_RETRY_NEEDED: Succeeded on first attempts")
except Exception as e:
    print(f"RETRY_FAILED: {{type(e).__name__}}: {{e}}")
    print(f"ATTEMPTS: {{call_count}}")
    if call_count == 1:
        print("NO_RETRY: Function doesn't retry on failure")
    else:
        print(f"INSUFFICIENT_RETRIES: Only {{call_count}} attempts before giving up")
"""
        return await self.execute_python(test_code)

    async def test_circuit_breaker(
        self,
        target_code: str,
        function_name: str,
        failure_threshold: int = 5,
    ) -> ExecutionResult:
        """Test if code implements circuit breaker pattern.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function to test
            failure_threshold: Number of failures before circuit should open

        Returns:
            ExecutionResult indicating circuit breaker behavior
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)

        test_code = f"""
import time

call_count = 0
external_call_count = 0

# Mock that always fails
def failing_external(*args, **kwargs):
    global external_call_count
    external_call_count += 1
    raise ConnectionError("Service unavailable")

{target_code}

# Make many calls - circuit breaker should stop calling external after threshold
results = []
for i in range({failure_threshold * 3}):
    try:
        result = {function_name}()
        results.append(('success', result))
    except Exception as e:
        results.append(('error', str(e)))

print(f"TOTAL_CALLS: {{len(results)}}")
print(f"EXTERNAL_CALLS: {{external_call_count}}")

if external_call_count < {failure_threshold * 3}:
    print("CIRCUIT_BREAKER_DETECTED: External calls stopped after failures")
    print(f"CIRCUIT_OPENED_AFTER: {{external_call_count}} failures")
else:
    print("NO_CIRCUIT_BREAKER: All calls attempted external service")
    print("VULNERABILITY: No circuit breaker protection")
"""
        return await self.execute_python(test_code)

    async def test_resource_cleanup(
        self,
        target_code: str,
        function_name: str,
        iterations: int = 100,
    ) -> ExecutionResult:
        """Test if code properly cleans up resources on failure.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function to test
            iterations: Number of iterations to detect leaks

        Returns:
            ExecutionResult indicating resource cleanup behavior
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)

        test_code = f'''
import gc
import sys

# Track resource allocations
open_resources = []

class TrackedResource:
    """Resource that tracks whether it's been closed."""
    def __init__(self, name):
        self.name = name
        self.closed = False
        open_resources.append(self)

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

{target_code}

# Run multiple iterations
leaked_count = 0
for i in range({iterations}):
    try:
        {function_name}()
    except Exception:
        pass  # Expected failures are OK

# Check for leaks
gc.collect()
leaked = [r for r in open_resources if not r.closed]
leaked_count = len(leaked)

print(f"TOTAL_RESOURCES: {{len(open_resources)}}")
print(f"LEAKED_RESOURCES: {{leaked_count}}")

if leaked_count > 0:
    print(f"RESOURCE_LEAK: {{leaked_count}} resources not cleaned up")
    print("VULNERABILITY: Resources leaked on failure path")
else:
    print("CLEANUP_OK: All resources properly closed")
'''
        return await self.execute_python(test_code)

    async def test_graceful_degradation(
        self,
        target_code: str,
        function_name: str,
        degradation_check: str = "result is not None",
    ) -> ExecutionResult:
        """Test if code gracefully degrades when dependencies fail.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function to test
            degradation_check: Expression to verify degraded response is valid
                              (limited to simple boolean expressions for safety)

        Returns:
            ExecutionResult indicating degradation behavior
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)
        # Validate degradation_check is a safe expression (no dangerous operations)
        if any(
            danger in degradation_check
            for danger in [
                "import",
                "exec",
                "eval",
                "compile",
                "open",
                "__",
                "os.",
                "subprocess",
                "system",
                "popen",
                "spawn",
            ]
        ):
            raise SandboxSecurityError(
                f"Dangerous pattern in degradation_check: {degradation_check}"
            )

        test_code = f"""
# Mock primary service as unavailable
primary_available = False

def mock_primary(*args, **kwargs):
    if not primary_available:
        raise ConnectionError("Primary service unavailable")
    return "primary_response"

{target_code}

# Test with primary down
try:
    result = {function_name}()
    if {degradation_check}:
        print(f"GRACEFUL_DEGRADATION: Returned fallback: {{result}}")
    else:
        print(f"DEGRADATION_INVALID: Result doesn't satisfy check: {{result}}")
except Exception as e:
    print(f"NO_DEGRADATION: Exception propagated: {{type(e).__name__}}: {{e}}")
    print("VULNERABILITY: No fallback when primary fails")
"""
        return await self.execute_python(test_code)

    async def test_memory_pressure(
        self,
        target_code: str,
        function_name: str,
        memory_limit_mb: int = 50,
    ) -> ExecutionResult:
        """Test code behavior under memory pressure.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function to test
            memory_limit_mb: Memory limit to simulate

        Returns:
            ExecutionResult indicating behavior under memory pressure
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)

        test_code = f"""
import sys
import gc

# Allocate memory to create pressure
memory_hog = []
try:
    # Allocate chunks until we hit the "limit"
    for i in range({memory_limit_mb}):
        memory_hog.append("X" * (1024 * 1024))  # 1MB strings
except MemoryError:
    pass

# Now test the function under memory pressure
{target_code}

gc.collect()  # Free some memory

try:
    result = {function_name}()
    print(f"COMPLETED_UNDER_PRESSURE: {{result}}")
except MemoryError as e:
    print(f"MEMORY_ERROR: Function failed under memory pressure")
    print("VULNERABILITY: No memory-efficient fallback")
except Exception as e:
    print(f"ERROR_UNDER_PRESSURE: {{type(e).__name__}}: {{e}}")

# Clean up
memory_hog.clear()
gc.collect()
"""
        return await self.execute_python(test_code, timeout=30)

    async def test_concurrent_access(
        self,
        target_code: str,
        function_name: str,
        num_concurrent: int = 20,
        shared_state_check: str | None = None,
    ) -> ExecutionResult:
        """Test for race conditions under concurrent access.

        Args:
            target_code: Code containing the function to test
            function_name: Name of function to test
            num_concurrent: Number of concurrent calls
            shared_state_check: Optional expression to verify state consistency
                               (limited to simple expressions for safety)

        Returns:
            ExecutionResult indicating concurrent access safety
        """
        # Validate parameters to prevent code injection
        validate_test_params(function_name=function_name)
        dangerous_tokens = (
            "import",
            "exec",
            "eval",
            "compile",
            "open",
            "__",
            "os.",
            "subprocess",
            "system",
            "popen",
            "spawn",
        )
        if shared_state_check is not None and any(
            token in shared_state_check for token in dangerous_tokens
        ):
            raise SandboxSecurityError(
                f"Dangerous pattern in shared_state_check: {shared_state_check}"
            )

        test_code = f"""
	import threading
	import time

{target_code}

results = []
errors = []
lock = threading.Lock()

def worker(worker_id):
    try:
        result = {function_name}()
        with lock:
            results.append((worker_id, result))
    except Exception as e:
        with lock:
            errors.append((worker_id, str(e)))

# Start all workers simultaneously
threads = []
barrier = threading.Barrier({num_concurrent})

def synchronized_worker(worker_id):
    barrier.wait()  # All threads start together
    worker(worker_id)

for i in range({num_concurrent}):
    t = threading.Thread(target=synchronized_worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join(timeout=10)

print(f"COMPLETED: {{len(results)}}/{num_concurrent}")
print(f"ERRORS: {{len(errors)}}")

if errors:
    print("CONCURRENT_ERRORS:")
    for worker_id, err in errors[:5]:
        print(f"  Worker {{worker_id}}: {{err}}")

# Check for inconsistent results (potential race condition)
if results:
    unique_results = set(str(r[1]) for r in results)
    if len(unique_results) > 1:
        print(f"INCONSISTENT_RESULTS: {{len(unique_results)}} different values")
        print("POTENTIAL_RACE_CONDITION: Results vary under concurrent access")
    else:
        print("CONSISTENT_RESULTS: All workers got same result")
"""
        return await self.execute_python(test_code, timeout=30)
