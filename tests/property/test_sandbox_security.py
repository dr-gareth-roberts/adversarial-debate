"""Property-based tests for sandbox security.

Uses hypothesis to generate diverse inputs and verify security invariants.
These tests ensure the sandbox cannot be escaped regardless of input.
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from adversarial_debate.sandbox import (
    MAX_CODE_SIZE,
    MAX_INPUT_KEY_LENGTH,
    SandboxConfig,
    SandboxSecurityError,
    generate_secure_temp_name,
    validate_code_size,
    validate_identifier,
    validate_inputs,
    validate_sandbox_config,
)

# =============================================================================
# Property: Identifier validation blocks all dangerous patterns
# =============================================================================

DANGEROUS_IDENTIFIERS = [
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
]


@given(st.text(min_size=1, max_size=100))
@settings(max_examples=500)
def test_identifier_validation_rejects_non_identifiers(text: str) -> None:
    """Non-Python identifiers must be rejected."""
    # If it's not a valid Python identifier, it should be rejected
    if not text.isidentifier():
        with pytest.raises(SandboxSecurityError):
            validate_identifier(text)


@pytest.mark.parametrize("dangerous", DANGEROUS_IDENTIFIERS)
def test_identifier_validation_blocks_dangerous_builtins(dangerous: str) -> None:
    """Dangerous Python builtins must always be blocked."""
    with pytest.raises(SandboxSecurityError):
        validate_identifier(dangerous)


@given(st.text(min_size=MAX_INPUT_KEY_LENGTH + 1, max_size=MAX_INPUT_KEY_LENGTH + 100))
def test_identifier_validation_rejects_long_names(text: str) -> None:
    """Identifiers exceeding max length must be rejected."""
    with pytest.raises(SandboxSecurityError):
        validate_identifier(text)


@given(st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,50}", fullmatch=True))
def test_valid_identifiers_pass(identifier: str) -> None:
    """Valid Python identifiers that aren't dangerous should pass."""
    assume(identifier not in DANGEROUS_IDENTIFIERS)
    assume(len(identifier) <= MAX_INPUT_KEY_LENGTH)
    # Should not raise
    validate_identifier(identifier)


# =============================================================================
# Property: Code size limits are enforced
# =============================================================================


def test_large_code_rejected() -> None:
    """Code exceeding size limit must be rejected.

    Avoid Hypothesis here: generating multi-megabyte examples is slow and
    triggers Hypothesis health checks, while adding little extra coverage.
    """
    code = "x" * (MAX_CODE_SIZE + 1)
    with pytest.raises(SandboxSecurityError):
        validate_code_size(code)


@given(st.text(max_size=MAX_CODE_SIZE // 2))
def test_small_code_accepted(code: str) -> None:
    """Code within size limit should be accepted."""
    if len(code.encode("utf-8")) <= MAX_CODE_SIZE:
        # Should not raise
        validate_code_size(code)


# =============================================================================
# Property: Input validation maintains security invariants
# =============================================================================


@given(
    st.dictionaries(
        keys=st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,30}", fullmatch=True),
        values=st.one_of(
            st.integers(),
            st.floats(allow_nan=False),
            st.text(max_size=100),
            st.booleans(),
            st.lists(st.integers(), max_size=10),
        ),
        max_size=10,
    )
)
def test_valid_inputs_accepted(inputs: dict) -> None:
    """Valid inputs with safe keys and JSON-serializable values should pass."""
    # Filter out dangerous keys
    safe_inputs = {
        k: v
        for k, v in inputs.items()
        if k not in DANGEROUS_IDENTIFIERS and len(k) <= MAX_INPUT_KEY_LENGTH
    }
    # Should not raise
    validate_inputs(safe_inputs)


@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.text(max_size=100),
        min_size=1,
        max_size=5,
    )
)
def test_inputs_with_invalid_keys_rejected(inputs: dict) -> None:
    """Inputs with invalid Python identifier keys should be rejected."""
    # If any key is not a valid identifier, validation should fail
    has_invalid_key = any(not k.isidentifier() or k in DANGEROUS_IDENTIFIERS for k in inputs)

    if has_invalid_key:
        with pytest.raises(SandboxSecurityError):
            validate_inputs(inputs)


# =============================================================================
# Property: Secure temp names are unpredictable
# =============================================================================


@given(st.integers(min_value=1, max_value=100))
def test_secure_temp_names_unique(count: int) -> None:
    """Generated temp names must be unique."""
    names = [generate_secure_temp_name() for _ in range(count)]
    assert len(names) == len(set(names)), "Temp names must be unique"


@given(st.text(max_size=20).filter(lambda x: x.isalnum() or x == "_"))
def test_secure_temp_names_format(prefix: str) -> None:
    """Temp names must follow expected format."""
    if prefix:  # Skip empty prefix
        name = generate_secure_temp_name(prefix)
        assert name.startswith(prefix + "_")
        assert name.endswith(".py")
        # Should have 16 hex chars between prefix and .py
        middle = name[len(prefix) + 1 : -3]
        assert len(middle) == 16
        assert all(c in "0123456789abcdef" for c in middle)


# =============================================================================
# Property: Config validation catches invalid resource limits
# =============================================================================


@given(st.floats(min_value=-100, max_value=0))
def test_invalid_cpu_limit_rejected(cpu_limit: float) -> None:
    """CPU limits <= 0 must be rejected."""
    config = SandboxConfig(cpu_limit=cpu_limit)
    with pytest.raises(SandboxSecurityError):
        validate_sandbox_config(config)


@given(st.floats(min_value=16.01, max_value=100))
def test_excessive_cpu_limit_rejected(cpu_limit: float) -> None:
    """CPU limits > 16 must be rejected."""
    config = SandboxConfig(cpu_limit=cpu_limit)
    with pytest.raises(SandboxSecurityError):
        validate_sandbox_config(config)


@given(st.integers(min_value=-100, max_value=0))
def test_invalid_timeout_rejected(timeout: int) -> None:
    """Timeouts <= 0 must be rejected."""
    config = SandboxConfig(timeout_seconds=timeout)
    with pytest.raises(SandboxSecurityError):
        validate_sandbox_config(config)


@given(st.integers(min_value=301, max_value=10000))
def test_excessive_timeout_rejected(timeout: int) -> None:
    """Timeouts > 300s must be rejected."""
    config = SandboxConfig(timeout_seconds=timeout)
    with pytest.raises(SandboxSecurityError):
        validate_sandbox_config(config)


# =============================================================================
# Property: Memory limit format validation
# =============================================================================

VALID_MEMORY_FORMATS = ["64m", "128m", "256M", "1g", "2G", "512k", "1024K"]
INVALID_MEMORY_FORMATS = ["64mb", "128 m", "-256m", "1.5g", "abc", "", "m64"]


@pytest.mark.parametrize("memory", VALID_MEMORY_FORMATS)
def test_valid_memory_formats_accepted(memory: str) -> None:
    """Valid memory limit formats should be accepted."""
    config = SandboxConfig(memory_limit=memory)
    validate_sandbox_config(config)


@pytest.mark.parametrize("memory", INVALID_MEMORY_FORMATS)
def test_invalid_memory_formats_rejected(memory: str) -> None:
    """Invalid memory limit formats must be rejected."""
    config = SandboxConfig(memory_limit=memory)
    with pytest.raises(SandboxSecurityError):
        validate_sandbox_config(config)


# =============================================================================
# Property: Docker image name validation
# =============================================================================

VALID_DOCKER_IMAGES = [
    "python:3.11-slim",
    "python:3.12",
    "ubuntu:22.04",
    "alpine:latest",
    "ghcr.io/owner/repo:v1.0.0",
]

INVALID_DOCKER_IMAGES = [
    "python",  # No tag
    ":3.11",  # No image name
    "python:3.11; rm -rf /",  # Command injection attempt
    "python:$(whoami)",  # Command substitution
    "",  # Empty
]


@pytest.mark.parametrize("image", VALID_DOCKER_IMAGES)
def test_valid_docker_images_accepted(image: str) -> None:
    """Valid Docker image names should be accepted."""
    config = SandboxConfig(use_docker=True, docker_image=image)
    validate_sandbox_config(config)


@pytest.mark.parametrize("image", INVALID_DOCKER_IMAGES)
def test_invalid_docker_images_rejected(image: str) -> None:
    """Invalid or dangerous Docker image names must be rejected."""
    config = SandboxConfig(use_docker=True, docker_image=image)
    with pytest.raises(SandboxSecurityError):
        validate_sandbox_config(config)


# =============================================================================
# Property: Allowed hosts validation
# =============================================================================


@given(
    st.lists(
        st.from_regex(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,50}", fullmatch=True),
        max_size=10,
    )
)
def test_valid_hosts_accepted(hosts: list) -> None:
    """Valid hostnames should be accepted."""
    config = SandboxConfig(allowed_hosts=hosts)
    validate_sandbox_config(config)


@given(
    st.lists(
        st.text(min_size=1, max_size=20).filter(lambda x: any(c in x for c in ";&|`$(){}<>")),
        min_size=1,
        max_size=3,
    )
)
def test_hosts_with_shell_chars_rejected(hosts: list) -> None:
    """Hostnames with shell metacharacters must be rejected."""
    config = SandboxConfig(allowed_hosts=hosts)
    with pytest.raises(SandboxSecurityError):
        validate_sandbox_config(config)
