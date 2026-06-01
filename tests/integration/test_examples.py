"""Integration tests that run every shipped example to completion.

Examples are documentation users copy-paste, so a broken example is worse than
no example. These run each one end-to-end with the deterministic mock provider
(no API key, no network) and assert a clean exit — catching runtime drift that
lives behind ``if __name__ == "__main__"`` (broken imports, renamed APIs, etc.).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _run(args: list[str], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LLM_PROVIDER"] = "mock"
    env["ADVERSARIAL_BEAD_LEDGER"] = str(tmp_path / "ledger.jsonl")
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        cwd=EXAMPLES_DIR.parent,
    )


@pytest.mark.parametrize(
    "example",
    ["quickstart.py", "basic_analysis.py", "sandbox_execution.py", "ci_integration.py"],
)
def test_example_runs_to_completion(example: str, tmp_path: Path) -> None:
    result = _run([str(EXAMPLES_DIR / example)], tmp_path)
    assert result.returncode == 0, (
        f"{example} exited {result.returncode}\n"
        f"STDOUT:\n{result.stdout[-2000:]}\nSTDERR:\n{result.stderr[-2000:]}"
    )


def test_single_agent_example_runs(tmp_path: Path) -> None:
    # This example requires a --file argument.
    sample = tmp_path / "sample.py"
    sample.write_text(
        'def get_user(uid):\n    return db.execute(f"SELECT * FROM u WHERE id={uid}")\n'
    )
    result = _run(
        [str(EXAMPLES_DIR / "single_agent.py"), "--file", str(sample), "--agent", "exploit"],
        tmp_path,
    )
    assert result.returncode == 0, (
        f"single_agent.py exited {result.returncode}\n"
        f"STDOUT:\n{result.stdout[-2000:]}\nSTDERR:\n{result.stderr[-2000:]}"
    )
