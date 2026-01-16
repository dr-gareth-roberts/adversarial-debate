#!/usr/bin/env python3
"""Sandbox execution example: Run untrusted code safely.

This example demonstrates how to use the hardened sandbox to:
1. Execute untrusted Python code safely
2. Test for specific vulnerabilities
3. Capture output and errors
"""

from adversarial_debate.sandbox import (
    SandboxConfig,
    SandboxExecutor,
    SandboxResult,
)


def basic_execution() -> None:
    """Basic sandbox execution example."""
    print("=" * 60)
    print("Example 1: Basic Execution")
    print("=" * 60)

    config = SandboxConfig(
        timeout_seconds=10,
        max_memory_mb=128,
        use_docker=False,  # Use subprocess for simplicity
    )

    executor = SandboxExecutor(config)

    # Safe code
    code = """
x = 5
y = 10
result = x + y
print(f"Result: {result}")
"""

    result = executor.execute_python(code, inputs={})
    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.stdout}")
    print(f"Errors: {result.stderr}")
    print()


def execution_with_inputs() -> None:
    """Execute code with input values."""
    print("=" * 60)
    print("Example 2: Execution with Inputs")
    print("=" * 60)

    config = SandboxConfig(timeout_seconds=10)
    executor = SandboxExecutor(config)

    code = """
# Inputs are available as variables
print(f"Name: {name}")
print(f"Numbers: {numbers}")
print(f"Sum: {sum(numbers)}")
"""

    result = executor.execute_python(
        code,
        inputs={
            "name": "Alice",
            "numbers": [1, 2, 3, 4, 5],
        },
    )

    print(f"Output: {result.stdout}")
    print()


def timeout_handling() -> None:
    """Demonstrate timeout handling."""
    print("=" * 60)
    print("Example 3: Timeout Handling")
    print("=" * 60)

    config = SandboxConfig(timeout_seconds=2)
    executor = SandboxExecutor(config)

    # Code that runs too long
    code = """
import time
print("Starting...")
time.sleep(10)  # This will be killed
print("Done!")  # This won't be reached
"""

    result = executor.execute_python(code, inputs={})
    print(f"Exit code: {result.exit_code}")
    print(f"Timed out: {result.timed_out}")
    print(f"Output: {result.stdout}")
    print()


def memory_limit_handling() -> None:
    """Demonstrate memory limit handling."""
    print("=" * 60)
    print("Example 4: Memory Limit Handling")
    print("=" * 60)

    config = SandboxConfig(
        timeout_seconds=10,
        max_memory_mb=50,
    )
    executor = SandboxExecutor(config)

    # Code that tries to allocate too much memory
    code = """
# Try to allocate a large list
data = [0] * (100 * 1024 * 1024)  # 100M integers
print(f"Allocated: {len(data)} items")
"""

    result = executor.execute_python(code, inputs={})
    print(f"Exit code: {result.exit_code}")
    print(f"Output: {result.stdout}")
    print(f"Errors: {result.stderr[:200] if result.stderr else 'None'}")
    print()


def sql_injection_test() -> None:
    """Test code for SQL injection vulnerability."""
    print("=" * 60)
    print("Example 5: SQL Injection Testing")
    print("=" * 60)

    config = SandboxConfig(timeout_seconds=10)
    executor = SandboxExecutor(config)

    # Vulnerable code to test
    vulnerable_code = '''
def build_query(user_input):
    """Build SQL query - VULNERABLE."""
    return f"SELECT * FROM users WHERE id = '{user_input}'"

# Test with normal input
print("Normal input:", build_query("123"))

# Test with malicious input
print("Injection:", build_query("' OR '1'='1"))
'''

    result = executor.execute_python(vulnerable_code, inputs={})
    print(f"Output:\n{result.stdout}")

    # The output shows the injection worked
    if "OR '1'='1" in result.stdout:
        print("VULNERABILITY CONFIRMED: SQL injection possible")
    print()


def error_handling() -> None:
    """Demonstrate error handling."""
    print("=" * 60)
    print("Example 6: Error Handling")
    print("=" * 60)

    config = SandboxConfig(timeout_seconds=10)
    executor = SandboxExecutor(config)

    # Code with an error
    code = """
x = 1 / 0  # ZeroDivisionError
"""

    result = executor.execute_python(code, inputs={})
    print(f"Exit code: {result.exit_code}")
    print(f"Error output:\n{result.stderr}")
    print()


def network_disabled() -> None:
    """Demonstrate network access is disabled."""
    print("=" * 60)
    print("Example 7: Network Disabled")
    print("=" * 60)

    config = SandboxConfig(
        timeout_seconds=10,
        use_docker=True,  # Docker required for network isolation
        network_disabled=True,
    )

    try:
        executor = SandboxExecutor(config)

        code = """
import urllib.request
try:
    response = urllib.request.urlopen('https://example.com', timeout=5)
    print(f"Status: {response.status}")
except Exception as e:
    print(f"Network blocked: {type(e).__name__}: {e}")
"""

        result = executor.execute_python(code, inputs={})
        print(f"Output: {result.stdout}")
    except RuntimeError as e:
        print(f"Docker not available: {e}")
        print("Network isolation requires Docker.")
    print()


def main() -> None:
    """Run all examples."""
    print()
    print("Adversarial Debate - Sandbox Execution Examples")
    print("=" * 60)
    print()

    basic_execution()
    execution_with_inputs()
    timeout_handling()
    memory_limit_handling()
    sql_injection_test()
    error_handling()

    # This requires Docker
    # network_disabled()

    print("All examples completed!")


if __name__ == "__main__":
    main()
