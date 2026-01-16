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
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

from . import __version__
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
        "-c", "--config",
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
        "-o", "--output",
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


def print_json(data: dict[str, Any]) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, default=str))


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


async def cmd_analyze(args: argparse.Namespace, config: Config) -> int:
    """Run a single agent analysis."""
    from .agents import AgentContext, BreakAgent, ChaosAgent, ExploitAgent
    from .providers import get_provider
    from .store import BeadStore

    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Target not found: {args.target}")
        return 1

    # Read target code
    file_path = str(target_path)

    if target_path.is_file():
        code = target_path.read_text()
        files = [str(target_path)]
    else:
        # Read all Python files in directory
        code_parts = []
        files = []
        for py_file in target_path.rglob("*.py"):
            files.append(str(py_file))
            code_parts.append(f"# File: {py_file}\n{py_file.read_text()}\n")
        code = "\n".join(code_parts)

    if not code.strip():
        print_error("No code found to analyze")
        return 1

    # Check dry run early (before provider creation which may fail without API key)
    if config.dry_run:
        agent_names = {"exploit": "ExploitAgent", "break": "BreakAgent", "chaos": "ChaosAgent"}
        print(f"Would run {agent_names[args.agent]} on {len(files)} file(s)")
        return 0

    # Select agent
    agent_map = {
        "exploit": ExploitAgent,
        "break": BreakAgent,
        "chaos": ChaosAgent,
    }
    agent_class = agent_map[args.agent]

    # Create provider, bead store, and agent
    provider = get_provider(config.provider.provider)
    bead_store = BeadStore(config.bead_ledger_path)
    agent = agent_class(provider, bead_store)

    # Create context
    from datetime import UTC, datetime
    context = AgentContext(
        run_id=f"cli-{args.agent}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id=f"cli-{args.agent}",
        task_id="analysis",
        inputs={
            "code": code,
            "file_path": file_path,
            "file_paths": files,
            "focus_areas": args.focus or [],
        },
    )

    logger.info(f"Running {agent.name} on {len(files)} file(s)")

    # Run analysis
    try:
        output = await agent.run(context)
    except Exception as e:
        logger.exception(f"Agent {agent.name} failed")
        print_error(f"Analysis failed: {e}")
        return 1

    # Output results
    if args.json_output:
        print_json(output.result)
    else:
        print(f"\n{'=' * 60}")
        print(f"{agent.name} Analysis Results")
        print(f"{'=' * 60}")
        print(f"Confidence: {output.confidence:.0%}")

        if output.errors:
            print(f"\nErrors: {', '.join(output.errors)}")

        findings = output.result.get("findings", [])
        print(f"\nFindings: {len(findings)}")

        for finding in findings:
            severity = finding.get("severity", "UNKNOWN")
            title = finding.get("title", "Untitled")
            print(f"  [{severity}] {title}")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output.result, f, indent=2, default=str)
        logger.info(f"Results saved to {output_path}")

    return 0


async def cmd_orchestrate(args: argparse.Namespace, config: Config) -> int:
    """Create an attack plan."""
    from .agents import AgentContext, ChaosOrchestrator
    from .providers import get_provider
    from .store import BeadStore

    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Target not found: {args.target}")
        return 1

    # Collect files and patches
    changed_files = []
    patches = {}

    if target_path.is_file():
        changed_files.append({"path": str(target_path), "change_type": "modified"})
        patches[str(target_path)] = target_path.read_text()[:2000]
    else:
        for py_file in target_path.rglob("*.py"):
            rel_path = str(py_file.relative_to(target_path))
            changed_files.append({"path": rel_path, "change_type": "modified"})
            patches[rel_path] = py_file.read_text()[:2000]

    if not changed_files:
        print_error("No Python files found")
        return 1

    # Check dry run early (before provider creation which may fail without API key)
    if config.dry_run:
        print(f"Would create attack plan for {len(changed_files)} file(s)")
        return 0

    # Create provider, bead store, and orchestrator
    provider = get_provider(config.provider.provider)
    bead_store = BeadStore(config.bead_ledger_path)
    orchestrator = ChaosOrchestrator(provider, bead_store)

    # Create context
    from datetime import UTC, datetime
    context = AgentContext(
        run_id=f"cli-orchestrate-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id="cli-orchestrate",
        task_id="plan",
        inputs={
            "changed_files": changed_files,
            "patches": patches,
            "exposure": args.exposure,
            "time_budget_seconds": args.time_budget,
        },
    )

    logger.info(f"Creating attack plan for {len(changed_files)} file(s)")

    # Run orchestrator
    try:
        output = await orchestrator.run(context)
    except Exception as e:
        logger.exception("ChaosOrchestrator failed")
        print_error(f"Planning failed: {e}")
        return 1

    # Output results
    if args.json_output:
        print_json(output.result)
    else:
        summary = output.result.get("summary", {})

        print(f"\n{'=' * 60}")
        print("Attack Plan")
        print(f"{'=' * 60}")
        print(f"Risk Level: {summary.get('risk_level', 'UNKNOWN')}")
        print(f"Total Attacks: {summary.get('total_attacks', 0)}")
        print(f"Estimated Duration: {summary.get('estimated_duration_seconds', 0)}s")

        by_agent = summary.get("by_agent", {})
        print("\nBy Agent:")
        for agent, count in by_agent.items():
            print(f"  {agent}: {count}")

        by_priority = summary.get("by_priority", {})
        print("\nBy Priority:")
        for priority, count in by_priority.items():
            if count > 0:
                print(f"  {priority.upper()}: {count}")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output.result, f, indent=2, default=str)
        logger.info(f"Attack plan saved to {output_path}")

    return 0


async def cmd_verdict(args: argparse.Namespace, config: Config) -> int:
    """Run arbiter on findings."""
    from .agents import AgentContext, Arbiter
    from .providers import get_provider
    from .store import BeadStore

    findings_path = Path(args.findings)
    if not findings_path.exists():
        print_error(f"Findings file not found: {args.findings}")
        return 1

    # Load findings
    try:
        with open(findings_path) as f:
            findings = json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in findings file: {e}")
        return 1

    # Check dry run early (before provider creation which may fail without API key)
    if config.dry_run:
        if isinstance(findings, list):
            finding_count = len(findings)
        else:
            finding_count = len(findings.get("findings", []))
        print(f"Would render verdict on {finding_count} finding(s)")
        return 0

    # Load optional context
    additional_context: dict[str, Any] = {}
    if args.context:
        context_path = Path(args.context)
        if context_path.exists():
            with open(context_path) as f:
                additional_context = json.load(f)

    # Create provider, bead store, and arbiter
    provider = get_provider(config.provider.provider)
    bead_store = BeadStore(config.bead_ledger_path)
    arbiter = Arbiter(provider, bead_store)

    # Create context
    from datetime import UTC, datetime
    context = AgentContext(
        run_id=f"cli-verdict-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id="cli-verdict",
        task_id="verdict",
        inputs={
            "findings": findings if isinstance(findings, list) else findings.get("findings", []),
            "original_task": additional_context.get("task", "CLI analysis"),
            "changed_files": additional_context.get("files", []),
            **additional_context,
        },
    )

    logger.info("Running Arbiter verdict")

    # Run arbiter
    try:
        output = await arbiter.run(context)
    except Exception as e:
        logger.exception("Arbiter failed")
        print_error(f"Verdict failed: {e}")
        return 1

    # Output results
    if args.json_output:
        print_json(output.result)
    else:
        summary = output.result.get("summary", {})

        print(f"\n{'=' * 60}")
        print(f"VERDICT: {summary.get('decision', 'UNKNOWN')}")
        print(f"{'=' * 60}")

        if summary.get("should_block"):
            print("\n*** THIS SHOULD BLOCK THE MERGE ***\n")

        print(f"Blocking Issues: {summary.get('blocking_issues', 0)}")
        print(f"Warnings: {summary.get('warnings', 0)}")
        print(f"Passed: {summary.get('passed', 0)}")
        print(f"False Positives: {summary.get('false_positives', 0)}")

        # Print report if available
        report = output.result.get("report", "")
        if report:
            print(f"\n{report}")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output.result, f, indent=2, default=str)
        logger.info(f"Verdict saved to {output_path}")

    # Return non-zero if should block
    if output.result.get("summary", {}).get("should_block"):
        return 2

    return 0


async def cmd_run(args: argparse.Namespace, config: Config) -> int:
    """Run the full pipeline."""
    from .agents import (
        AgentContext,
        AgentOutput,
        Arbiter,
        BreakAgent,
        ChaosAgent,
        ChaosOrchestrator,
        ExploitAgent,
    )
    from .providers import get_provider
    from .store import BeadStore

    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Target not found: {args.target}")
        return 1

    # Collect files and patches
    file_path = str(target_path)
    if target_path.is_file():
        code = target_path.read_text()
        files = [str(target_path)]
        changed_files = [{"path": str(target_path), "change_type": "modified"}]
        patches = {str(target_path): code[:2000]}
    else:
        code_parts = []
        files = []
        changed_files = []
        patches = {}
        for py_file in target_path.rglob("*.py"):
            rel_path = str(py_file.relative_to(target_path))
            files.append(str(py_file))
            code_parts.append(f"# File: {py_file}\n{py_file.read_text()}\n")
            changed_files.append({"path": rel_path, "change_type": "modified"})
            patches[rel_path] = py_file.read_text()[:2000]
        code = "\n".join(code_parts)

    if not files:
        print_error("No Python files found")
        return 1

    if not code.strip():
        print_error("No code found to analyze")
        return 1

    # Check dry run early (before provider creation which may fail without API key)
    if config.dry_run:
        print(f"Would run orchestrator + 3 agents + verdict on {len(files)} file(s)")
        return 0

    # Create provider, bead store, and agents
    provider = get_provider(config.provider.provider)
    bead_store = BeadStore(config.bead_ledger_path)
    orchestrator = ChaosOrchestrator(provider, bead_store)
    exploit = ExploitAgent(provider, bead_store)
    breaker = BreakAgent(provider, bead_store)
    chaos = ChaosAgent(provider, bead_store)
    arbiter = Arbiter(provider, bead_store)

    from datetime import UTC, datetime
    timestamp = datetime.now(UTC)
    run_id = f"cli-run-{timestamp.strftime('%Y%m%d%H%M%S')}"
    run_dir = Path(config.output_dir) / f"run-{timestamp.strftime('%Y%m%d%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Orchestrator
    orchestrator_context = AgentContext(
        run_id=run_id,
        timestamp_iso=timestamp.isoformat(),
        policy={},
        thread_id=run_id,
        task_id="plan",
        inputs={
            "changed_files": changed_files,
            "patches": patches,
            "exposure": "internal",
            "time_budget_seconds": args.time_budget,
        },
    )

    try:
        plan_output = await orchestrator.run(orchestrator_context)
    except Exception as e:
        logger.exception("ChaosOrchestrator failed")
        print_error(f"Planning failed: {e}")
        return 1

    # Agent analyses (parallel)
    analysis_inputs = {
        "code": code,
        "file_path": file_path,
        "file_paths": files,
    }

    async def run_agent(agent: Any, task_id: str) -> AgentOutput:
        context = AgentContext(
            run_id=run_id,
            timestamp_iso=timestamp.isoformat(),
            policy={},
            thread_id=run_id,
            task_id=task_id,
            inputs=analysis_inputs,
        )
        return await agent.run(context)

    sem = asyncio.Semaphore(max(1, args.parallel))

    async def with_limit(agent: Any, task_id: str) -> AgentOutput:
        async with sem:
            return await run_agent(agent, task_id)

    try:
        exploit_output, break_output, chaos_output = await asyncio.gather(
            with_limit(exploit, "exploit"),
            with_limit(breaker, "break"),
            with_limit(chaos, "chaos"),
        )
    except Exception as e:
        logger.exception("Agent execution failed")
        print_error(f"Analysis failed: {e}")
        return 1

    # Combine findings for the arbiter
    combined_findings = []
    combined_findings.extend(exploit_output.result.get("findings", []))
    combined_findings.extend(break_output.result.get("findings", []))
    for experiment in chaos_output.result.get("experiments", []):
        chaos_finding = dict(experiment)
        chaos_finding["agent"] = "ChaosAgent"
        chaos_finding["finding_type"] = "chaos_experiment"
        combined_findings.append(chaos_finding)

    # Persist artifacts
    attack_plan_path = run_dir / "attack_plan.json"
    exploit_path = run_dir / "exploit_findings.json"
    break_path = run_dir / "break_findings.json"
    chaos_path = run_dir / "chaos_findings.json"
    combined_path = run_dir / "findings.json"

    with open(attack_plan_path, "w") as f:
        json.dump(plan_output.result, f, indent=2, default=str)
    with open(exploit_path, "w") as f:
        json.dump(exploit_output.result, f, indent=2, default=str)
    with open(break_path, "w") as f:
        json.dump(break_output.result, f, indent=2, default=str)
    with open(chaos_path, "w") as f:
        json.dump(chaos_output.result, f, indent=2, default=str)
    with open(combined_path, "w") as f:
        json.dump(combined_findings, f, indent=2, default=str)

    verdict_output = None
    if not args.skip_verdict:
        arbiter_context = AgentContext(
            run_id=run_id,
            timestamp_iso=timestamp.isoformat(),
            policy={},
            thread_id=run_id,
            task_id="verdict",
            inputs={
                "findings": combined_findings,
                "original_task": f"CLI run on {args.target}",
                "changed_files": changed_files,
            },
        )
        try:
            verdict_output = await arbiter.run(arbiter_context)
        except Exception as e:
            logger.exception("Arbiter failed")
            print_error(f"Verdict failed: {e}")
            return 1

        verdict_path = run_dir / "verdict.json"
        with open(verdict_path, "w") as f:
            json.dump(verdict_output.result, f, indent=2, default=str)

    summary = {
        "run_id": run_id,
        "output_dir": str(run_dir),
        "files_analyzed": len(files),
        "findings": {
            "exploit": len(exploit_output.result.get("findings", [])),
            "break": len(break_output.result.get("findings", [])),
            "chaos": len(chaos_output.result.get("experiments", [])),
        },
        "verdict": verdict_output.result.get("summary", {}) if verdict_output else None,
    }

    if args.json_output:
        print_json(summary)
    else:
        print(f"\n{'=' * 60}")
        print("Run Complete")
        print(f"{'=' * 60}")
        print(f"Output Dir: {run_dir}")
        print(f"Attack Plan: {attack_plan_path}")
        print(f"Exploit Findings: {exploit_path}")
        print(f"Break Findings: {break_path}")
        print(f"Chaos Findings: {chaos_path}")
        print(f"Combined Findings: {combined_path}")
        if verdict_output:
            verdict_summary = verdict_output.result.get("summary", {})
            print(f"\nVERDICT: {verdict_summary.get('decision', 'UNKNOWN')}")
            print(f"Blocking Issues: {verdict_summary.get('blocking_issues', 0)}")
            print(f"Warnings: {verdict_summary.get('warnings', 0)}")
            print(f"Passed: {verdict_summary.get('passed', 0)}")
            print(f"False Positives: {verdict_summary.get('false_positives', 0)}")

    if verdict_output and verdict_output.result.get("summary", {}).get("should_block"):
        return 2

    return 0


async def async_main(args: argparse.Namespace, config: Config) -> int:
    """Async main entry point."""
    command_map = {
        "analyze": cmd_analyze,
        "orchestrate": cmd_orchestrate,
        "verdict": cmd_verdict,
        "run": cmd_run,
    }

    if args.command is None:
        print("No command specified. Use --help for usage information.")
        return 1

    cmd_func = command_map.get(args.command)
    if cmd_func is None:
        print_error(f"Unknown command: {args.command}")
        return 1

    return await cmd_func(args, config)


def main() -> NoReturn:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

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
