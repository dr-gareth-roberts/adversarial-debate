"""Tests for the CLI command implementations.

These drive the ``cmd_*`` coroutines directly (rather than via subprocess) with
the deterministic mock provider, so behaviour is exercised in-process and
visible to coverage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from adversarial_debate.cli_commands import (
    async_main,
    cmd_analyze,
    cmd_cache,
    cmd_orchestrate,
    cmd_run,
    cmd_verdict,
    cmd_watch,
)
from adversarial_debate.config import Config, ProviderConfig


@pytest.fixture
def mock_config(tmp_path: Path) -> Config:
    """A config wired to the deterministic mock provider with temp output paths."""
    config = Config()
    config.provider = ProviderConfig(provider="mock", model="mock-model")
    config.bead_ledger_path = str(tmp_path / "beads" / "ledger.jsonl")
    config.output_dir = str(tmp_path / "output")
    config.dry_run = False
    return config


@pytest.fixture
def code_file(tmp_path: Path) -> Path:
    target = tmp_path / "app.py"
    target.write_text(
        'def get_user(uid):\n    return db.execute(f"SELECT * FROM u WHERE id={uid}")\n'
    )
    return target


def make_args(**overrides: object) -> argparse.Namespace:
    """Build an args namespace covering every attribute the commands read."""
    base: dict[str, object] = {
        "command": None,
        "agent": "exploit",
        "target": ".",
        "focus": None,
        "json_output": False,
        "output": None,
        "exposure": "internal",
        "time_budget": 60,
        "findings": None,
        "context": None,
        "files": None,
        "parallel": 4,
        "skip_debate": True,
        "skip_verdict": False,
        "debate_max_findings": 10,
        "baseline_file": None,
        "baseline_mode": "off",
        "baseline_write": None,
        "bundle_file": None,
        "report_file": None,
        "format": None,
        "fail_on": "never",
        "min_severity": "medium",
        "config": None,
        "patterns": ["*.py"],
        "debounce": 0.5,
        "cache_command": "stats",
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class TestAnalyze:
    async def test_missing_target_returns_1(self, mock_config: Config) -> None:
        rc = await cmd_analyze(make_args(target="/no/such.py"), mock_config)
        assert rc == 1

    async def test_empty_file_returns_1(self, mock_config: Config, tmp_path: Path) -> None:
        empty = tmp_path / "empty.py"
        empty.write_text("   \n")
        rc = await cmd_analyze(make_args(target=str(empty)), mock_config)
        assert rc == 1

    async def test_dry_run_returns_0(
        self, mock_config: Config, code_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_config.dry_run = True
        rc = await cmd_analyze(make_args(target=str(code_file)), mock_config)
        assert rc == 0
        assert "Would run" in capsys.readouterr().out

    @pytest.mark.parametrize("agent", ["exploit", "break", "chaos", "crypto"])
    async def test_runs_each_agent_with_mock(
        self, mock_config: Config, code_file: Path, agent: str
    ) -> None:
        rc = await cmd_analyze(make_args(target=str(code_file), agent=agent), mock_config)
        assert rc == 0

    async def test_json_output_writes_output_file(
        self, mock_config: Config, code_file: Path, tmp_path: Path
    ) -> None:
        out_file = tmp_path / "result.json"
        rc = await cmd_analyze(
            make_args(target=str(code_file), json_output=True, output=str(out_file)),
            mock_config,
        )
        assert rc == 0
        assert json.loads(out_file.read_text()) is not None

    async def test_directory_target(self, mock_config: Config, code_file: Path) -> None:
        rc = await cmd_analyze(make_args(target=str(code_file.parent)), mock_config)
        assert rc == 0


class TestOrchestrate:
    async def test_missing_target(self, mock_config: Config) -> None:
        assert await cmd_orchestrate(make_args(target="/no/dir"), mock_config) == 1

    async def test_empty_directory_returns_1(self, mock_config: Config, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert await cmd_orchestrate(make_args(target=str(empty_dir)), mock_config) == 1

    async def test_dry_run(
        self, mock_config: Config, code_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_config.dry_run = True
        rc = await cmd_orchestrate(make_args(target=str(code_file)), mock_config)
        assert rc == 0
        assert "Would create attack plan" in capsys.readouterr().out

    async def test_runs_with_mock(
        self, mock_config: Config, code_file: Path, tmp_path: Path
    ) -> None:
        out_file = tmp_path / "plan.json"
        rc = await cmd_orchestrate(
            make_args(target=str(code_file), output=str(out_file)), mock_config
        )
        assert rc == 0
        assert out_file.exists()


class TestVerdict:
    def _findings_file(self, tmp_path: Path) -> Path:
        path = tmp_path / "findings.json"
        path.write_text(json.dumps([{"id": "F1", "title": "x", "severity": "HIGH"}]))
        return path

    async def test_missing_file(self, mock_config: Config) -> None:
        assert await cmd_verdict(make_args(findings="/no/f.json"), mock_config) == 1

    async def test_invalid_json(self, mock_config: Config, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        assert await cmd_verdict(make_args(findings=str(bad)), mock_config) == 1

    async def test_dry_run(
        self, mock_config: Config, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_config.dry_run = True
        rc = await cmd_verdict(make_args(findings=str(self._findings_file(tmp_path))), mock_config)
        assert rc == 0
        assert "Would render verdict" in capsys.readouterr().out

    async def test_runs_with_mock(self, mock_config: Config, tmp_path: Path) -> None:
        rc = await cmd_verdict(make_args(findings=str(self._findings_file(tmp_path))), mock_config)
        assert rc in (0, 2)


class TestRun:
    async def test_missing_target(self, mock_config: Config) -> None:
        assert await cmd_run(make_args(target="/no/such"), mock_config) == 1

    async def test_explicit_missing_file(self, mock_config: Config) -> None:
        assert await cmd_run(make_args(target=".", files=["/no/f.py"]), mock_config) == 1

    async def test_dry_run(
        self, mock_config: Config, code_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_config.dry_run = True
        rc = await cmd_run(make_args(target=str(code_file)), mock_config)
        assert rc == 0
        assert "Would run orchestrator" in capsys.readouterr().out

    async def test_full_pipeline_writes_artifacts(
        self, mock_config: Config, code_file: Path
    ) -> None:
        rc = await cmd_run(make_args(target=str(code_file)), mock_config)
        assert rc == 0
        run_dirs = sorted(Path(mock_config.output_dir).glob("run-*"))
        assert run_dirs
        for name in (
            "attack_plan.json",
            "exploit_findings.json",
            "break_findings.json",
            "chaos_findings.json",
            "crypto_findings.json",
            "findings.json",
            "verdict.json",
            "bundle.json",
        ):
            assert (run_dirs[0] / name).exists(), f"missing {name}"

    async def test_skip_verdict_omits_verdict_file(
        self, mock_config: Config, code_file: Path
    ) -> None:
        rc = await cmd_run(make_args(target=str(code_file), skip_verdict=True), mock_config)
        assert rc == 0
        run_dir = sorted(Path(mock_config.output_dir).glob("run-*"))[0]
        assert not (run_dir / "verdict.json").exists()

    async def test_report_file_written_in_requested_format(
        self, mock_config: Config, code_file: Path, tmp_path: Path
    ) -> None:
        report = tmp_path / "report.sarif"
        rc = await cmd_run(
            make_args(target=str(code_file), report_file=str(report), format="sarif"),
            mock_config,
        )
        assert rc == 0
        assert json.loads(report.read_text())["version"] == "2.1.0"

    async def test_baseline_write_short_circuits(
        self, mock_config: Config, code_file: Path, tmp_path: Path
    ) -> None:
        baseline = tmp_path / "baseline.json"
        rc = await cmd_run(
            make_args(target=str(code_file), baseline_write=str(baseline)), mock_config
        )
        assert rc == 0
        assert baseline.exists()

    async def test_debate_step_runs_and_writes_debated_findings(
        self, mock_config: Config, code_file: Path
    ) -> None:
        rc = await cmd_run(
            make_args(target=str(code_file), skip_debate=False, skip_verdict=False),
            mock_config,
        )
        assert rc == 0
        run_dir = sorted(Path(mock_config.output_dir).glob("run-*"))[0]
        assert (run_dir / "findings.debated.json").exists()

    async def test_json_output_emits_bundle(
        self, mock_config: Config, code_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = await cmd_run(make_args(target=str(code_file), json_output=True), mock_config)
        assert rc == 0
        # stdout should be a JSON bundle with the expected top-level keys.
        payload = json.loads(capsys.readouterr().out)
        assert {"metadata", "findings", "verdict"} <= set(payload)

    async def test_baseline_only_new_flags_regressions(
        self, mock_config: Config, code_file: Path, tmp_path: Path
    ) -> None:
        # An empty baseline means every current finding is "new".
        baseline = tmp_path / "base.json"
        baseline.write_text(json.dumps({"findings": []}))
        rc = await cmd_run(
            make_args(
                target=str(code_file),
                baseline_file=str(baseline),
                baseline_mode="only-new",
                fail_on="warn",
                min_severity="low",
            ),
            mock_config,
        )
        # New findings above the threshold → block exit code (2).
        assert rc == 2

    async def test_files_argument_selects_specific_files(
        self, mock_config: Config, code_file: Path
    ) -> None:
        rc = await cmd_run(
            make_args(target=str(code_file.parent), files=[str(code_file)]), mock_config
        )
        assert rc == 0


class TestWatch:
    async def test_missing_target(self, mock_config: Config) -> None:
        assert await cmd_watch(make_args(target="/no/such"), mock_config) == 1


class TestCache:
    async def test_stats(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = await cmd_cache(make_args(cache_command="stats"), Config())
        assert rc == 0
        assert "Cache Statistics" in capsys.readouterr().out

    async def test_clear(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = await cmd_cache(make_args(cache_command="clear"), Config())
        assert rc == 0
        assert "Cleared" in capsys.readouterr().out

    async def test_cleanup(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = await cmd_cache(make_args(cache_command="cleanup"), Config())
        assert rc == 0
        assert "Removed" in capsys.readouterr().out

    async def test_unknown_command_returns_1(self) -> None:
        assert await cmd_cache(make_args(cache_command="bogus"), Config()) == 1


class TestAsyncMain:
    async def test_none_command_returns_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = await async_main(make_args(command=None), Config())
        assert rc == 1
        assert "No command specified" in capsys.readouterr().out

    async def test_unknown_command_returns_1(self) -> None:
        assert await async_main(make_args(command="frobnicate"), Config()) == 1

    async def test_dispatches_to_command(self, mock_config: Config, code_file: Path) -> None:
        mock_config.dry_run = True
        rc = await async_main(make_args(command="analyze", target=str(code_file)), mock_config)
        assert rc == 0
