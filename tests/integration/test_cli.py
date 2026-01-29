"""Integration tests for CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def sample_code_file(temp_dir: Path) -> Path:
    """Create a sample Python file for testing."""
    code_file = temp_dir / "sample.py"
    code_file.write_text('''
def get_user(user_id: str) -> dict:
    """Get user by ID."""
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)

def process_input(data: str) -> str:
    """Process user input."""
    return eval(data)  # Dangerous!
''')
    return code_file


class TestCLIHelp:
    """Tests for CLI help and version."""

    def test_help(self) -> None:
        """Test --help flag."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "adversarial-debate" in result.stdout
        assert "analyze" in result.stdout
        assert "orchestrate" in result.stdout
        assert "verdict" in result.stdout

    def test_version(self) -> None:
        """Test --version flag."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_no_command(self) -> None:
        """Test running without a command."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "No command specified" in result.stdout


class TestCLIAnalyze:
    """Tests for analyze command."""

    def test_analyze_help(self) -> None:
        """Test analyze --help."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "analyze", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "exploit" in result.stdout
        assert "break" in result.stdout
        assert "chaos" in result.stdout

    def test_analyze_nonexistent_file(self) -> None:
        """Test analyze with nonexistent file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "adversarial_debate.cli",
                "analyze",
                "exploit",
                "/nonexistent/file.py",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_analyze_dry_run(self, sample_code_file: Path) -> None:
        """Test analyze with --dry-run."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "adversarial_debate.cli",
                "--dry-run",
                "analyze",
                "exploit",
                str(sample_code_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Would run" in result.stdout


class TestCLIOrchestrate:
    """Tests for orchestrate command."""

    def test_orchestrate_help(self) -> None:
        """Test orchestrate --help."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "orchestrate", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--time-budget" in result.stdout
        assert "--exposure" in result.stdout

    def test_orchestrate_dry_run(self, sample_code_file: Path) -> None:
        """Test orchestrate with --dry-run."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "adversarial_debate.cli",
                "--dry-run",
                "orchestrate",
                str(sample_code_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Would create attack plan" in result.stdout


class TestCLIVerdict:
    """Tests for verdict command."""

    def test_verdict_help(self) -> None:
        """Test verdict --help."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "verdict", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "findings" in result.stdout.lower()

    def test_verdict_nonexistent_file(self) -> None:
        """Test verdict with nonexistent findings file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "adversarial_debate.cli",
                "verdict",
                "/nonexistent/findings.json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_verdict_dry_run(self, temp_dir: Path) -> None:
        """Test verdict with --dry-run."""
        findings_file = temp_dir / "findings.json"
        findings_file.write_text(
            json.dumps(
                [
                    {
                        "id": "TEST-001",
                        "title": "Test Finding",
                        "severity": "MEDIUM",
                    }
                ]
            )
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "adversarial_debate.cli",
                "--dry-run",
                "verdict",
                str(findings_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Would render verdict" in result.stdout


class TestCLIRun:
    """Tests for run command."""

    def test_run_help(self) -> None:
        """Test run --help."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "run", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--parallel" in result.stdout
        assert "--skip-verdict" in result.stdout

    def test_run_dry_run(self, sample_code_file: Path) -> None:
        """Test run with --dry-run."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "adversarial_debate.cli",
                "--dry-run",
                "run",
                str(sample_code_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Would run orchestrator" in result.stdout

    def test_run_with_mock(self, sample_code_file: Path, temp_dir: Path) -> None:
        """Test full run with mock provider."""
        env = os.environ.copy()
        env["LLM_PROVIDER"] = "mock"
        env["ADVERSARIAL_BEAD_LEDGER"] = str(temp_dir / "ledger.jsonl")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "adversarial_debate.cli",
                "run",
                str(sample_code_file),
                "--output",
                str(temp_dir),
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0

        run_dirs = sorted(temp_dir.glob("run-*"))
        assert run_dirs
        run_dir = run_dirs[0]

        for filename in [
            "attack_plan.json",
            "exploit_findings.json",
            "break_findings.json",
            "chaos_findings.json",
            "findings.json",
            "verdict.json",
        ]:
            assert (run_dir / filename).exists()


class TestCLIOutput:
    """Tests for CLI output options."""

    def test_json_output_flag(self) -> None:
        """Test --json-output flag is accepted."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "--json-output", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_log_level_flag(self) -> None:
        """Test --log-level flag is accepted."""
        result = subprocess.run(
            [sys.executable, "-m", "adversarial_debate.cli", "--log-level", "DEBUG", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
