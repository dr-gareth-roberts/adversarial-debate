"""Sandbox execution package.

Implementation lives in `adversarial_debate.sandbox.executor`.
This module re-exports the full public surface so external imports remain stable.
"""

from __future__ import annotations

from . import executor as _executor

ExecutionResult = _executor.ExecutionResult
SandboxConfig = _executor.SandboxConfig
SandboxExecutor = _executor.SandboxExecutor
SandboxSecurityError = _executor.SandboxSecurityError
validate_sandbox_config = _executor.validate_sandbox_config

__all__ = [
    "ExecutionResult",
    "SandboxConfig",
    "SandboxExecutor",
    "SandboxSecurityError",
    "validate_sandbox_config",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    return getattr(_executor, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(dir(_executor)))
