"""Unit tests for CLI module."""

import argparse
import json

import pytest

from adversarial_debate.cli import (
    create_parser,
    load_config,
    print_error,
    print_json,
)
from adversarial_debate.config import Config


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.prog == "adversarial-debate"

    def test_version_argument(self):
        """Test --version argument."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_global_arguments(self):
        """Test global CLI arguments."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "--config",
                "config.json",
                "--log-level",
                "DEBUG",
                "--json-output",
                "--dry-run",
                "-o",
                "output.json",
            ]
        )
        assert args.config == "config.json"
        assert args.log_level == "DEBUG"
        assert args.json_output is True
        assert args.dry_run is True
        assert args.output == "output.json"

    def test_analyze_command(self):
        """Test analyze subcommand."""
        parser = create_parser()
        args = parser.parse_args(
            ["analyze", "exploit", "src/api.py", "--focus", "injection", "auth", "--timeout", "60"]
        )
        assert args.command == "analyze"
        assert args.agent == "exploit"
        assert args.target == "src/api.py"
        assert args.focus == ["injection", "auth"]
        assert args.timeout == 60

    def test_analyze_agent_choices(self):
        """Test that analyze only accepts valid agents."""
        parser = create_parser()

        # Valid agents should work
        for agent in ["exploit", "break", "chaos"]:
            args = parser.parse_args(["analyze", agent, "file.py"])
            assert args.agent == agent

        # Invalid agent should fail
        with pytest.raises(SystemExit):
            parser.parse_args(["analyze", "invalid", "file.py"])

    def test_orchestrate_command(self):
        """Test orchestrate subcommand."""
        parser = create_parser()
        args = parser.parse_args(
            ["orchestrate", "src/", "--time-budget", "600", "--exposure", "public"]
        )
        assert args.command == "orchestrate"
        assert args.target == "src/"
        assert args.time_budget == 600
        assert args.exposure == "public"

    def test_verdict_command(self):
        """Test verdict subcommand."""
        parser = create_parser()
        args = parser.parse_args(["verdict", "findings.json", "--context", "context.json"])
        assert args.command == "verdict"
        assert args.findings == "findings.json"
        assert args.context == "context.json"

    def test_run_command(self):
        """Test run subcommand."""
        parser = create_parser()
        args = parser.parse_args(
            ["run", "src/", "--time-budget", "900", "--parallel", "5", "--skip-verdict"]
        )
        assert args.command == "run"
        assert args.target == "src/"
        assert args.time_budget == 900
        assert args.parallel == 5
        assert args.skip_verdict is True


class TestLoadConfig:
    """Tests for configuration loading."""

    def test_load_from_env(self):
        """Test loading config from environment."""
        parser = create_parser()
        args = parser.parse_args(["--log-level", "WARNING"])
        config = load_config(args)

        assert isinstance(config, Config)
        assert config.logging.level == "WARNING"

    def test_load_with_dry_run(self):
        """Test dry_run is set from args."""
        parser = create_parser()
        args = parser.parse_args(["--dry-run"])
        config = load_config(args)

        assert config.dry_run is True

    def test_load_with_output(self, tmp_path):
        """Test output_dir is set from args."""
        output_path = tmp_path / "results"
        parser = create_parser()
        args = parser.parse_args(["--output", str(output_path)])
        config = load_config(args)

        assert config.output_dir == str(output_path)


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_print_json(self, capsys):
        """Test JSON printing."""
        data = {"key": "value", "number": 42}
        print_json(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == data

    def test_print_json_with_non_serializable(self, capsys):
        """Test JSON printing with non-serializable objects."""
        from datetime import datetime

        data = {"timestamp": datetime(2024, 1, 1, 12, 0, 0)}
        print_json(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "timestamp" in parsed

    def test_print_error(self, capsys):
        """Test error printing."""
        print_error("Something went wrong")
        captured = capsys.readouterr()
        assert "Error: Something went wrong" in captured.err


class TestAnalyzeCommand:
    """Tests for the analyze command."""

    @pytest.mark.asyncio
    async def test_analyze_file_not_found(self, capsys, monkeypatch):
        """Test analyze with non-existent file."""
        from adversarial_debate.cli import cmd_analyze

        parser = create_parser()
        args = parser.parse_args(["analyze", "exploit", "/nonexistent/file.py"])
        config = Config.from_env()

        result = await cmd_analyze(args, config)
        assert result == 1

        captured = capsys.readouterr()
        assert "Target not found" in captured.err

    @pytest.mark.asyncio
    async def test_analyze_dry_run(self, capsys, tmp_path):
        """Test analyze in dry run mode."""
        from adversarial_debate.cli import cmd_analyze

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        parser = create_parser()
        args = parser.parse_args(["--dry-run", "analyze", "exploit", str(test_file)])
        config = load_config(args)

        result = await cmd_analyze(args, config)
        assert result == 0

        captured = capsys.readouterr()
        assert "Would run ExploitAgent" in captured.out


class TestOrchestrateCommand:
    """Tests for the orchestrate command."""

    @pytest.mark.asyncio
    async def test_orchestrate_file_not_found(self, capsys):
        """Test orchestrate with non-existent target."""
        from adversarial_debate.cli import cmd_orchestrate

        parser = create_parser()
        args = parser.parse_args(["orchestrate", "/nonexistent/dir"])
        config = Config.from_env()

        result = await cmd_orchestrate(args, config)
        assert result == 1

        captured = capsys.readouterr()
        assert "Target not found" in captured.err

    @pytest.mark.asyncio
    async def test_orchestrate_dry_run(self, capsys, tmp_path):
        """Test orchestrate in dry run mode."""
        from adversarial_debate.cli import cmd_orchestrate

        # Create test files
        (tmp_path / "test.py").write_text("print('hello')")

        parser = create_parser()
        args = parser.parse_args(["--dry-run", "orchestrate", str(tmp_path)])
        config = load_config(args)

        result = await cmd_orchestrate(args, config)
        assert result == 0

        captured = capsys.readouterr()
        assert "Would create attack plan" in captured.out


class TestVerdictCommand:
    """Tests for the verdict command."""

    @pytest.mark.asyncio
    async def test_verdict_file_not_found(self, capsys):
        """Test verdict with non-existent findings file."""
        from adversarial_debate.cli import cmd_verdict

        parser = create_parser()
        args = parser.parse_args(["verdict", "/nonexistent/findings.json"])
        config = Config.from_env()

        result = await cmd_verdict(args, config)
        assert result == 1

        captured = capsys.readouterr()
        assert "Findings file not found" in captured.err

    @pytest.mark.asyncio
    async def test_verdict_invalid_json(self, capsys, tmp_path):
        """Test verdict with invalid JSON file."""
        from adversarial_debate.cli import cmd_verdict

        findings_file = tmp_path / "findings.json"
        findings_file.write_text("not valid json")

        parser = create_parser()
        args = parser.parse_args(["verdict", str(findings_file)])
        config = Config.from_env()

        result = await cmd_verdict(args, config)
        assert result == 1

        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.err

    @pytest.mark.asyncio
    async def test_verdict_dry_run(self, capsys, tmp_path):
        """Test verdict in dry run mode."""
        from adversarial_debate.cli import cmd_verdict

        findings_file = tmp_path / "findings.json"
        findings_file.write_text('{"findings": [{"title": "test"}]}')

        parser = create_parser()
        args = parser.parse_args(["--dry-run", "verdict", str(findings_file)])
        config = load_config(args)

        result = await cmd_verdict(args, config)
        assert result == 0

        captured = capsys.readouterr()
        assert "Would render verdict" in captured.out
