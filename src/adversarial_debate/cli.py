"""Command-line interface for adversarial-debate.

Usage:
    adversarial-debate analyze <agent> <target>  Run single agent analysis
    adversarial-debate orchestrate <target>      Create attack plan
    adversarial-debate verdict <findings>        Run arbiter on findings
    adversarial-debate run <target>              Full pipeline
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import NoReturn

from . import __version__
from .cli_commands import (
    async_main,
    cmd_analyze,
    cmd_cache,
    cmd_orchestrate,
    cmd_run,
    cmd_verdict,
    cmd_watch,
)
from .cli_output import print_error, print_json
from .config import Config, set_config
from .logging import get_logger, setup_logging

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="adversarial-debate",
        description="AI Red Team Security Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run ExploitAgent on a file
    adversarial-debate analyze exploit src/api/users.py

    # Create an attack plan for changed files
    adversarial-debate orchestrate src/

    # Run arbiter on collected findings
    adversarial-debate verdict findings.json

    # Run full pipeline on a target
    adversarial-debate run src/api/ --output results/
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--completions",
        choices=["bash", "zsh", "fish"],
        help="Generate shell completion script and exit",
        metavar="SHELL",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to configuration file",
        metavar="FILE",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)",
    )

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file or directory",
        metavar="PATH",
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands",
    )

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run a single agent on a target",
        description="Run a specific red team agent on a file or directory",
    )
    analyze_parser.add_argument(
        "agent",
        choices=["exploit", "break", "chaos"],
        help="Agent to run (exploit, break, or chaos)",
    )
    analyze_parser.add_argument(
        "target",
        type=str,
        help="File or directory to analyze",
    )
    analyze_parser.add_argument(
        "--focus",
        type=str,
        nargs="+",
        help="Focus areas for analysis (e.g., injection auth)",
    )
    analyze_parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)",
    )

    # orchestrate command
    orchestrate_parser = subparsers.add_parser(
        "orchestrate",
        help="Create an attack plan",
        description="Analyze code and create a coordinated attack plan",
    )
    orchestrate_parser.add_argument(
        "target",
        type=str,
        help="File or directory to analyze",
    )
    orchestrate_parser.add_argument(
        "--time-budget",
        type=int,
        default=300,
        help="Time budget in seconds (default: 300)",
    )
    orchestrate_parser.add_argument(
        "--exposure",
        choices=["public", "authenticated", "internal"],
        default="internal",
        help="Exposure level of the code (default: internal)",
    )

    # verdict command
    verdict_parser = subparsers.add_parser(
        "verdict",
        help="Run arbiter on findings",
        description="Review findings and render a verdict",
    )
    verdict_parser.add_argument(
        "findings",
        type=str,
        help="JSON file containing findings",
    )
    verdict_parser.add_argument(
        "--context",
        type=str,
        help="Additional context file (JSON)",
    )

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run full pipeline",
        description="Run the complete adversarial analysis pipeline",
    )
    run_parser.add_argument(
        "target",
        type=str,
        help="File or directory to analyze",
    )
    run_parser.add_argument(
        "--output",
        type=str,
        help="Output directory for run artifacts",
        metavar="PATH",
    )
    run_parser.add_argument(
        "--files",
        type=str,
        nargs="*",
        help="Analyze only these specific files (useful for pre-commit)",
        metavar="FILE",
    )
    run_parser.add_argument(
        "--time-budget",
        type=int,
        default=600,
        help="Total time budget in seconds (default: 600)",
    )
    run_parser.add_argument(
        "--parallel",
        type=int,
        default=3,
        help="Maximum parallel agents (default: 3)",
    )
    run_parser.add_argument(
        "--skip-verdict",
        action="store_true",
        help="Skip the final verdict (just collect findings)",
    )
    run_parser.add_argument(
        "--skip-debate",
        action="store_true",
        help="Skip cross-examination debate step",
    )
    run_parser.add_argument(
        "--debate-max-findings",
        type=int,
        default=40,
        help="Max findings to include in cross-examination (default: 40)",
    )
    run_parser.add_argument(
        "--format",
        choices=["json", "sarif", "html", "markdown"],
        help="Write a formatted report (requires --report-file)",
    )
    run_parser.add_argument(
        "--report-file",
        type=str,
        help="Write formatted report to this path",
        metavar="PATH",
    )
    run_parser.add_argument(
        "--bundle-file",
        type=str,
        help="Write the canonical JSON bundle to this path (default: <run_dir>/bundle.json)",
        metavar="PATH",
    )
    run_parser.add_argument(
        "--fail-on",
        choices=["block", "warn", "never"],
        default="block",
        help="Exit non-zero based on verdict (default: block)",
    )
    run_parser.add_argument(
        "--min-severity",
        choices=["critical", "high", "medium", "low", "info"],
        default="high",
        help="Minimum severity to consider for failure gating (default: high)",
    )
    run_parser.add_argument(
        "--baseline-file",
        type=str,
        help="Baseline bundle JSON file to compare against",
        metavar="PATH",
    )
    run_parser.add_argument(
        "--baseline-mode",
        choices=["off", "only-new"],
        default="off",
        help="Failure gating mode with baseline (default: off)",
    )
    run_parser.add_argument(
        "--baseline-write",
        type=str,
        help="Write the current bundle to this path as a baseline and exit 0",
        metavar="PATH",
    )

    # watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch files and re-run analysis on changes",
        description="Continuously watch for file changes and re-run analysis",
    )
    watch_parser.add_argument(
        "target",
        type=str,
        help="File or directory to watch",
    )
    watch_parser.add_argument(
        "--agent",
        choices=["exploit", "break", "chaos", "all"],
        default="all",
        help="Agent to run (default: all)",
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=0.5,
        help="Debounce delay in seconds (default: 0.5)",
    )
    watch_parser.add_argument(
        "--patterns",
        type=str,
        nargs="+",
        default=["*.py"],
        help="File patterns to watch (default: *.py)",
    )

    # cache command
    cache_parser = subparsers.add_parser(
        "cache",
        help="Manage analysis cache",
        description="View and manage the analysis cache",
    )
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command")

    cache_subparsers.add_parser("stats", help="Show cache statistics")
    cache_subparsers.add_parser("clear", help="Clear all cache entries")
    cache_subparsers.add_parser("cleanup", help="Remove expired cache entries")

    return parser


def load_config(args: argparse.Namespace) -> Config:
    """Load configuration from file or environment."""
    config = Config.from_file(args.config) if args.config else Config.from_env()

    # Override with CLI arguments
    config.logging.level = args.log_level
    config.dry_run = args.dry_run

    if args.output:
        config.output_dir = args.output

    return config


def main() -> NoReturn:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle completions early (before config loading)
    if hasattr(args, "completions") and args.completions:
        from .completions import print_completion_script

        print_completion_script(args.completions)
        sys.exit(0)

    # Load and set configuration
    try:
        config = load_config(args)
        set_config(config)
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Setup logging
    setup_logging(config.logging)

    # Run the command
    try:
        exit_code = asyncio.run(async_main(args, config))
    except KeyboardInterrupt:
        print("\nInterrupted")
        exit_code = 130
    except Exception as e:
        logger.exception("Unexpected error")
        print_error(f"Unexpected error: {e}")
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()


__all__ = [
    "create_parser",
    "load_config",
    "main",
    "cmd_analyze",
    "cmd_orchestrate",
    "cmd_run",
    "cmd_verdict",
    "cmd_watch",
    "cmd_cache",
    "print_error",
    "print_json",
]
