#!/usr/bin/env python3
"""Sandbox execution examples: run untrusted code safely.

This example demonstrates how to use the hardened sandbox to:
1. Execute untrusted Python code safely
2. Provide structured inputs
3. Enforce timeouts (and, with Docker, resource limits and network isolation)
4. Capture output and errors
"""

from __future__ import annotations

import asyncio

from adversarial_debate.sandbox import SandboxConfig, SandboxExecutor


async def basic_execution() -> None:
    """Basic sandbox execution example (subprocess backend)."""
    print("=" * 60)
    print("Example 1: Basic Execution (subprocess backend)")
    print("=" * 60)

    config = SandboxConfig(
        timeout_seconds=10,
        memory_limit="128m",
        use_docker=False,  # Use subprocess for simplicity
    )
    executor = SandboxExecutor(config)

    code = """
x = 5
y = 10
result = x + y
print(f"Result: {result}")
"""

    result = await executor.execute_python(code, inputs={})
    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.output}")
    if result.error:
        print(f"Errors: {result.error}")
    print()


async def execution_with_inputs() -> None:
    """Execute code with input values."""
    print("=" * 60)
    print("Example 2: Execution with Inputs")
    print("=" * 60)

    executor = SandboxExecutor(SandboxConfig(timeout_seconds=10, use_docker=False))

    code = """
# Inputs are available as variables
print(f"Name: {name}")
print(f"Numbers: {numbers}")
print(f"Sum: {sum(numbers)}")
"""

    result = await executor.execute_python(
        code,
        inputs={
            "name": "Alice",
            "numbers": [1, 2, 3, 4, 5],
        },
    )

    print(f"Output: {result.output}")
    if result.error:
        print(f"Errors: {result.error}")
    print()


async def timeout_handling() -> None:
    """Demonstrate timeout handling."""
    print("=" * 60)
    print("Example 3: Timeout Handling")
    print("=" * 60)

    executor = SandboxExecutor(SandboxConfig(timeout_seconds=2, use_docker=False))

    code = """
import time
print("Starting...")
time.sleep(10)  # This will be killed
print("Done!")  # This won't be reached
"""

    result = await executor.execute_python(code, inputs={})
    print(f"Exit code: {result.exit_code}")
    print(f"Timed out: {result.timed_out}")
    print(f"Output: {result.output}")
    if result.error:
        print(f"Errors: {result.error}")
    print()


async def sql_injection_test() -> None:
    """Test code for SQL injection vulnerability using the built-in helper."""
    print("=" * 60)
    print("Example 4: SQL Injection Testing")
    print("=" * 60)

    executor = SandboxExecutor(SandboxConfig(timeout_seconds=10, use_docker=False))

    target_code = """
def get_users(user_id: str):
    # VULNERABLE: f-string query construction using attacker-controlled input.
    query = f"SELECT id, name, password FROM users WHERE id = {user_id}"
    return cursor.execute(query).fetchall()
"""

    result = await executor.test_sql_injection(
        target_code,
        function_name="get_users",
        param_name="user_id",
    )
    print("Output:")
    print(result.output)
    if result.error:
        print("Errors:")
        print(result.error)
    print()


async def error_handling() -> None:
    """Demonstrate error handling."""
    print("=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    executor = SandboxExecutor(SandboxConfig(timeout_seconds=10, use_docker=False))

    code = "x = 1 / 0  # ZeroDivisionError\n"
    result = await executor.execute_python(code, inputs={})

    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.output}")
    if result.error:
        print("Error output:")
        print(result.error)
    print()


async def network_isolation() -> None:
    """Demonstrate that outbound network access is disabled (Docker backend)."""
    print("=" * 60)
    print("Example 6: Network Isolation (Docker backend)")
    print("=" * 60)

    config = SandboxConfig(
        timeout_seconds=10,
        use_docker=True,
        network_enabled=False,  # default; explicit for clarity
    )
    executor = SandboxExecutor(config)

    if not executor.is_docker_available():
        print("Docker not available; skipping network isolation example.")
        print()
        return

    code = """
import urllib.request
try:
    response = urllib.request.urlopen("https://example.com", timeout=5)
    print(f"Status: {response.status}")
except Exception as e:
    print(f"Network blocked: {type(e).__name__}: {e}")
"""

    result = await executor.execute_python(code, inputs={})
    print(f"Output: {result.output}")
    if result.error:
        print(f"Errors: {result.error}")
    print()


async def memory_limit_handling() -> None:
    """Demonstrate memory limit behavior (Docker backend)."""
    print("=" * 60)
    print("Example 7: Memory Limit Handling (Docker backend)")
    print("=" * 60)

    config = SandboxConfig(
        timeout_seconds=10,
        use_docker=True,
        memory_limit="64m",
    )
    executor = SandboxExecutor(config)

    if not executor.is_docker_available():
        print("Docker not available; skipping memory limit example.")
        print()
        return

    code = """
try:
    # Attempt to allocate more than the configured memory limit.
    data = bytearray(128 * 1024 * 1024)  # 128 MiB
    print(f"Allocated: {len(data)} bytes")
except Exception as e:
    print(f"Allocation failed: {type(e).__name__}: {e}")
"""

    result = await executor.execute_python(code, inputs={})
    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.output}")
    if result.error:
        print("Errors:")
        print(result.error)
    print()


async def main() -> None:
    """Run all examples."""
    print()
    print("Adversarial Debate - Sandbox Execution Examples")
    print("=" * 60)
    print()

    await basic_execution()
    await execution_with_inputs()
    await timeout_handling()
    await sql_injection_test()
    await error_handling()
    await network_isolation()
    await memory_limit_handling()


if __name__ == "__main__":
    asyncio.run(main())
