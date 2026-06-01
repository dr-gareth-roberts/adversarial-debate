"""Tests for SandboxExecutor's capability methods (subprocess backend).

These exercise the vulnerability/resilience probes (``test_sql_injection``,
``test_timeout_handling``, …) end-to-end through the real subprocess backend —
no Docker, no network. Each probe builds a Python snippet, runs it, and
classifies the outcome; the assertions check that classification against
deliberately vulnerable or safe target code.
"""

from __future__ import annotations

import pytest

from adversarial_debate.exceptions import SandboxSecurityError
from adversarial_debate.sandbox import ExecutionResult, SandboxConfig, SandboxExecutor


@pytest.fixture
def executor() -> SandboxExecutor:
    return SandboxExecutor(SandboxConfig(use_docker=False, use_subprocess=True, timeout_seconds=30))


def _out(result: ExecutionResult) -> str:
    assert result.success, f"sandbox run failed: {result.error}\n{result.output}"
    return result.output


class TestExecuteExploitAndVerify:
    async def test_successful_exploit(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_exploit("def f():\n    return 1", "assert f() == 1")
        assert "EXPLOIT_SUCCESS" in _out(result)

    async def test_failed_exploit(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_exploit("def f():\n    return 1", "assert f() == 2")
        assert "EXPLOIT_FAILED" in _out(result)

    async def test_verify_finding_confirmed(self, executor: SandboxExecutor) -> None:
        verified, explanation = await executor.verify_finding(
            "def f():\n    return 1", "assert f() == 1", "returns 1"
        )
        assert verified is True
        assert "confirmed" in explanation.lower()

    async def test_verify_finding_rejected(self, executor: SandboxExecutor) -> None:
        verified, _ = await executor.verify_finding(
            "def f():\n    return 1", "assert f() == 2", "returns 2"
        )
        assert verified is False


class TestExecutePythonBackends:
    async def test_no_backend_available(self) -> None:
        executor = SandboxExecutor(SandboxConfig(use_docker=False, use_subprocess=False))
        result = await executor.execute_python("print('hi')")
        assert result.success is False
        assert "No execution backend available" in result.error

    async def test_oversized_code_rejected(self, executor: SandboxExecutor) -> None:
        result = await executor.execute_python("x = '" + "a" * (1024 * 1024 + 10) + "'")
        assert result.success is False
        assert "Security validation failed" in result.error

    async def test_docker_unavailable_falls_back_to_subprocess(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        executor = SandboxExecutor(SandboxConfig(use_docker=True, use_subprocess=True))
        # Force the Docker probe to report unavailable so execution falls back.
        monkeypatch.setattr(executor, "is_docker_available", lambda: False)
        result = await executor.execute_python("print('FELL_BACK')")
        assert result.success is True
        assert "FELL_BACK" in result.output

    def test_is_docker_available_returns_bool(self, executor: SandboxExecutor) -> None:
        assert isinstance(executor.is_docker_available(), bool)


class TestBoundaryAndConcurrency:
    async def test_boundary_value_triggers_exception(self, executor: SandboxExecutor) -> None:
        result = await executor.test_boundary_value(
            "def divide(n):\n    return 100 // n", "divide", "n", 0
        )
        assert "EXCEPTION: ZeroDivisionError" in _out(result)

    async def test_boundary_value_returns_result(self, executor: SandboxExecutor) -> None:
        result = await executor.test_boundary_value(
            "def divide(n):\n    return 100 // n", "divide", "n", 5
        )
        assert "RESULT: 20" in _out(result)

    async def test_concurrency_runs(self, executor: SandboxExecutor) -> None:
        target = "_c = [0]\ndef inc():\n    _c[0] += 1\n    return _c[0]"
        result = await executor.test_concurrency(target, "inc", num_concurrent=5)
        assert "RESULTS: 5 successes" in _out(result)


class TestSecurityProbes:
    async def test_sql_injection_detected(self, executor: SandboxExecutor) -> None:
        vulnerable = (
            "def lookup(name):\n"
            "    cur = conn.cursor()\n"
            '    cur.execute("SELECT * FROM users WHERE name = \'" + name + "\'")\n'
            "    return cur.fetchall()"
        )
        result = await executor.test_sql_injection(
            vulnerable, "lookup", "name", payloads=["' OR '1'='1"]
        )
        assert "SQL_INJECTION_FOUND" in _out(result)

    async def test_sql_injection_safe_code(self, executor: SandboxExecutor) -> None:
        # Validates input then uses a parameterised query; the payload is
        # rejected (returns None), so the probe reports no injection.
        safe = (
            "def lookup(name):\n"
            "    if not name.isalnum():\n"
            "        return None\n"
            "    cur = conn.cursor()\n"
            "    cur.execute('SELECT * FROM users WHERE name = ?', (name,))\n"
            "    return cur.fetchall()"
        )
        result = await executor.test_sql_injection(safe, "lookup", "name", payloads=["' OR '1'='1"])
        assert "NO_INJECTION_FOUND" in _out(result)

    async def test_command_injection_detected(self, executor: SandboxExecutor) -> None:
        vulnerable = (
            "import subprocess\n"
            "def run(cmd):\n"
            "    return subprocess.run('echo ok ' + cmd, shell=True, "
            "capture_output=True, text=True).stdout"
        )
        result = await executor.test_command_injection(
            vulnerable, "run", "cmd", payloads=["; echo INJECTED"]
        )
        assert "COMMAND_INJECTION_FOUND" in _out(result)

    async def test_path_traversal_detected(self, executor: SandboxExecutor) -> None:
        vulnerable = (
            "def read(rel):\n"
            "    with open(os.path.join(allowed_dir, rel)) as fh:\n"
            "        return fh.read()"
        )
        result = await executor.test_path_traversal(
            vulnerable, "read", "rel", payloads=["../secret.txt"]
        )
        assert "PATH_TRAVERSAL_FOUND" in _out(result)

    async def test_ssrf_detected(self, executor: SandboxExecutor) -> None:
        vulnerable = "import requests\ndef fetch(url):\n    return requests.get(url).text"
        result = await executor.test_ssrf(vulnerable, "fetch", "url")
        assert "SSRF_POSSIBLE" in _out(result)

    async def test_insecure_deserialization_detected(self, executor: SandboxExecutor) -> None:
        vulnerable = "import pickle\ndef load(data):\n    return pickle.loads(data)"
        result = await executor.test_deserialization(vulnerable, "load", "data")
        assert "INSECURE_DESERIALIZATION_FOUND" in _out(result)

    async def test_probe_rejects_unsafe_function_name(self, executor: SandboxExecutor) -> None:
        with pytest.raises(SandboxSecurityError):
            await executor.test_sql_injection("x = 1", "foo; import os", "name")


class TestResilienceProbes:
    async def test_dependency_failure_handled(self, executor: SandboxExecutor) -> None:
        target = "def op():\n    return 'ok'"
        result = await executor.test_dependency_failure(target, "op", "api")
        assert "DEPENDENCY_FAILURE_HANDLED" in _out(result)

    async def test_timeout_ok_for_fast_function(self, executor: SandboxExecutor) -> None:
        target = "def op():\n    return 'fast'"
        result = await executor.test_timeout_handling(target, "op", expected_timeout_seconds=2)
        assert "TIMEOUT_OK" in _out(result) or "COMPLETED" in _out(result)

    async def test_retry_working(self, executor: SandboxExecutor) -> None:
        target = (
            "def op():\n"
            "    for _ in range(10):\n"
            "        try:\n"
            "            return flaky_operation()\n"
            "        except ConnectionError:\n"
            "            continue"
        )
        result = await executor.test_retry_behavior(target, "op", failure_count=2)
        assert "RETRY_WORKING" in _out(result)

    async def test_no_circuit_breaker(self, executor: SandboxExecutor) -> None:
        target = "def op():\n    return failing_external()"
        result = await executor.test_circuit_breaker(target, "op", failure_threshold=2)
        assert "NO_CIRCUIT_BREAKER" in _out(result)

    async def test_resource_leak_detected(self, executor: SandboxExecutor) -> None:
        target = "def op():\n    TrackedResource('r')  # never closed"
        result = await executor.test_resource_cleanup(target, "op", iterations=3)
        assert "RESOURCE_LEAK" in _out(result)

    async def test_graceful_degradation(self, executor: SandboxExecutor) -> None:
        target = (
            "def op():\n"
            "    try:\n"
            "        return mock_primary()\n"
            "    except ConnectionError:\n"
            "        return 'degraded'"
        )
        result = await executor.test_graceful_degradation(target, "op")
        assert "GRACEFUL_DEGRADATION" in _out(result)

    async def test_graceful_degradation_rejects_dangerous_check(
        self, executor: SandboxExecutor
    ) -> None:
        with pytest.raises(SandboxSecurityError):
            await executor.test_graceful_degradation(
                "def op():\n    return 1", "op", degradation_check="__import__('os')"
            )

    async def test_memory_pressure_completes(self, executor: SandboxExecutor) -> None:
        target = "def op():\n    return 'ok'"
        result = await executor.test_memory_pressure(target, "op", memory_limit_mb=2)
        assert "COMPLETED_UNDER_PRESSURE" in _out(result)

    async def test_concurrent_access_consistent(self, executor: SandboxExecutor) -> None:
        target = "def op():\n    return 42"
        result = await executor.test_concurrent_access(target, "op", num_concurrent=3)
        assert "CONSISTENT_RESULTS" in _out(result)

    async def test_concurrent_access_rejects_dangerous_check(
        self, executor: SandboxExecutor
    ) -> None:
        with pytest.raises(SandboxSecurityError):
            await executor.test_concurrent_access(
                "def op():\n    return 1", "op", shared_state_check="__import__('os')"
            )
