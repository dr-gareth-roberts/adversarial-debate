"""Command implementations for the adversarial-debate CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import __version__
from .cli_output import print_error, print_json
from .cli_provider import _get_provider_from_config
from .config import Config
from .logging import get_logger
from .path_filter import DEFAULT_IGNORE_PATTERNS, path_matches_any

logger = get_logger(__name__)


def _iter_python_files(root: Path, ignore_patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for py_file in root.rglob("*.py"):
        if not path_matches_any(py_file, ignore_patterns):
            files.append(py_file)
    return files


def _read_text_safe(path: Path) -> str:
    """Read text with UTF-8 fallback handling for non-UTF8 files."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("Non-UTF8 file encountered, replacing invalid bytes: %s", path)
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Failed to read file %s: %s", path, exc)
        return ""


async def cmd_analyze(args: argparse.Namespace, config: Config) -> int:
    """Run a single agent analysis."""
    from .agents import Agent, AgentContext, BreakAgent, ChaosAgent, CryptoAgent, ExploitAgent
    from .store import BeadStore

    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Target not found: {args.target}")
        return 1

    # Read target code
    file_path = str(target_path)

    if target_path.is_file():
        code = _read_text_safe(target_path)
        files = [str(target_path)]
    else:
        # Read all Python files in directory
        code_parts = []
        files = []
        for py_file in _iter_python_files(target_path, DEFAULT_IGNORE_PATTERNS):
            files.append(str(py_file))
            code_parts.append(f"# File: {py_file}\n{_read_text_safe(py_file)}\n")
        code = "\n".join(code_parts)

    if not code.strip():
        print_error("No code found to analyze")
        return 1

    # Check dry run early (before provider creation which may fail without API key)
    if config.dry_run:
        agent_names = {
            "exploit": "ExploitAgent",
            "break": "BreakAgent",
            "chaos": "ChaosAgent",
            "crypto": "CryptoAgent",
        }
        print(f"Would run {agent_names[args.agent]} on {len(files)} file(s)")
        return 0

    # Create provider, bead store, and agent
    provider = _get_provider_from_config(config)
    bead_store = BeadStore(config.bead_ledger_path)

    agent_factories: dict[str, type[Agent]] = {
        "exploit": ExploitAgent,
        "break": BreakAgent,
        "chaos": ChaosAgent,
        "crypto": CryptoAgent,
    }

    agent_cls = agent_factories.get(args.agent)
    if agent_cls is None:
        raise ValueError(
            f"Unknown agent: {args.agent}. Valid agents: {list(agent_factories.keys())}"
        )

    agent: Agent = agent_cls(provider, bead_store)

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
        patches[str(target_path)] = _read_text_safe(target_path)[:2000]
    else:
        for py_file in _iter_python_files(target_path, DEFAULT_IGNORE_PATTERNS):
            rel_path = str(py_file.relative_to(target_path))
            changed_files.append({"path": rel_path, "change_type": "modified"})
            patches[rel_path] = _read_text_safe(py_file)[:2000]

    if not changed_files:
        print_error("No Python files found")
        return 1

    # Check dry run early (before provider creation which may fail without API key)
    if config.dry_run:
        print(f"Would create attack plan for {len(changed_files)} file(s)")
        return 0

    # Create provider, bead store, and orchestrator
    provider = _get_provider_from_config(config)
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
    provider = _get_provider_from_config(config)
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
        if report := output.result.get("report", ""):
            print(f"\n{report}")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output.result, f, indent=2, default=str)
        logger.info(f"Verdict saved to {output_path}")

    # Return non-zero if should block
    return 2 if output.result.get("summary", {}).get("should_block") else 0


async def cmd_run(args: argparse.Namespace, config: Config) -> int:
    """Run the full pipeline."""
    from .services import PipelineConfig, PipelineService
    from .store import BeadStore

    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Target not found: {args.target}")
        return 1

    # Check dry run early (before provider creation which may fail without API key)
    if config.dry_run:
        # Count files for dry run message
        if args.files:
            file_count = len(args.files)
        elif target_path.is_file():
            file_count = 1
        else:
            file_count = len(list(_iter_python_files(target_path, DEFAULT_IGNORE_PATTERNS)))
        print(f"Would run orchestrator + 4 agents + verdict on {file_count} file(s)")
        return 0

    # Create provider and bead store
    provider = _get_provider_from_config(config)
    bead_store = BeadStore(config.bead_ledger_path)

    # Build pipeline configuration from CLI args
    pipeline_config = PipelineConfig(
        target=args.target,
        files=args.files,
        time_budget=args.time_budget,
        parallel=args.parallel,
        cache_enabled=getattr(args, "cache", False),
        skip_debate=args.skip_debate,
        skip_verdict=args.skip_verdict,
        debate_max_findings=args.debate_max_findings,
        baseline_file=args.baseline_file,
        baseline_mode=args.baseline_mode,
        fail_on=args.fail_on,
        min_severity=args.min_severity,
        config_path=args.config,
    )

    # Execute pipeline via service layer
    service = PipelineService(config, provider, bead_store)
    result = await service.execute(pipeline_config)

    if not result.success:
        print_error(result.error or "Pipeline execution failed")
        return result.exit_code

    # Handle CLI-specific output (bundle writing, formatting, display)
    bundle = result.bundle
    run_dir = result.run_dir

    # Write bundle to disk
    bundle_path = Path(args.bundle_file) if args.bundle_file else (run_dir / "bundle.json")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, indent=2, default=str))

    # Handle baseline write
    if args.baseline_write:
        baseline_out = Path(args.baseline_write)
        baseline_out.parent.mkdir(parents=True, exist_ok=True)
        baseline_out.write_text(json.dumps(bundle, indent=2, default=str))

    # Generate formatted report if requested
    report_path: Path | None = None
    if args.report_file:
        from .formatters import FormatterConfig, get_formatter

        fmt = args.format
        if not fmt:
            suffix = Path(args.report_file).suffix.lower()
            fmt = {
                ".sarif": "sarif",
                ".json": "json",
                ".md": "markdown",
                ".html": "html",
            }.get(suffix, "sarif")

        formatter = get_formatter(
            fmt,
            FormatterConfig(
                tool_name="adversarial-debate",
                tool_version=__version__,
            ),
        )
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(formatter.format(bundle))

    # Early exit for baseline write
    if args.baseline_write:
        if not args.json_output:
            print(f"Baseline written: {args.baseline_write}")
        return 0

    # Display results
    if args.json_output:
        print_json(bundle)
    else:
        print(f"\n{'=' * 60}")
        print("Run Complete")
        print(f"{'=' * 60}")
        print(f"Output Dir: {run_dir}")
        print(f"Bundle: {bundle_path}")
        if report_path:
            print(f"Report: {report_path}")
        print(f"Attack Plan: {run_dir / 'attack_plan.json'}")
        print(f"Exploit Findings: {run_dir / 'exploit_findings.json'}")
        print(f"Break Findings: {run_dir / 'break_findings.json'}")
        print(f"Chaos Findings: {run_dir / 'chaos_findings.json'}")
        print(f"Combined Findings: {run_dir / 'findings.json'}")

        # Display verdict summary if available
        verdict_data = bundle.get("verdict")
        if verdict_data:
            verdict_summary = verdict_data.get("summary", {})
            print(f"\nVERDICT: {verdict_summary.get('decision', 'UNKNOWN')}")
            print(f"Blocking Issues: {verdict_summary.get('blocking_issues', 0)}")
            print(f"Warnings: {verdict_summary.get('warnings', 0)}")
            print(f"Passed: {verdict_summary.get('passed', 0)}")
            print(f"False Positives: {verdict_summary.get('false_positives', 0)}")

        # Display baseline diff if available
        if result.baseline_diff:
            print("\nBASELINE DIFF")
            print(f"New: {result.baseline_diff.get('new_count', 0)}")
            print(f"Fixed: {result.baseline_diff.get('fixed_count', 0)}")

    return result.exit_code


async def cmd_watch(args: argparse.Namespace, config: Config) -> int:
    """Run in watch mode."""
    from .watch import WatchConfig, WatchRunner

    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Target not found: {args.target}")
        return 1

    watch_config = WatchConfig(
        patterns=args.patterns,
        debounce_seconds=args.debounce,
    )

    async def analyze_files(changed_paths: list[Path]) -> None:
        """Run analysis on changed files."""
        print(f"\n{'=' * 60}")
        print(f"Analyzing {len(changed_paths)} file(s)...")
        print(f"{'=' * 60}\n")

        # Create a temporary args for analyze
        json_output_flag = bool(getattr(args, "json_output", False))

        # Determine which agents to run
        agents_to_run = (
            ["exploit", "break", "chaos", "crypto"] if args.agent == "all" else [args.agent]
        )

        for path in changed_paths[:5]:  # Limit to first 5 for performance
            for agent_name in agents_to_run:
                analyze_args = argparse.Namespace(
                    agent=agent_name,
                    target=str(path),
                    focus=None,
                    timeout=60,
                    json_output=json_output_flag,
                    output=None,
                )
                try:
                    await cmd_analyze(analyze_args, config)
                except Exception as e:
                    print_error(f"Analysis failed for {path} ({agent_name}): {e}")

    runner = WatchRunner([target_path], analyze_files, watch_config)
    await runner.run()
    return 0


async def cmd_cache(args: argparse.Namespace, config: Config) -> int:
    """Manage analysis cache."""
    from .cache import CacheManager

    cache = CacheManager(cache_dir=config.cache_dir)

    if args.cache_command == "stats":
        stats = cache.stats()
        if args.json_output if hasattr(args, "json_output") else False:
            print_json(stats)
        else:
            print("\nCache Statistics")
            print("=" * 40)
            print(f"Enabled: {stats.get('enabled', False)}")
            if stats.get("enabled"):
                print(f"Total Entries: {stats.get('total_entries', 0)}")
                print(f"Valid Entries: {stats.get('valid_entries', 0)}")
                print(f"Expired Entries: {stats.get('expired_entries', 0)}")
                print(f"Total Size: {stats.get('total_size_mb', 0)} MB")
                print(f"Cache Dir: {stats.get('cache_dir', 'N/A')}")
                if stats.get("by_agent"):
                    print("\nBy Agent:")
                    for agent, count in stats["by_agent"].items():
                        print(f"  {agent}: {count}")
        return 0

    elif args.cache_command == "clear":
        count = cache.clear()
        print(f"Cleared {count} cache entries")
        return 0

    elif args.cache_command == "cleanup":
        count = cache.cleanup()
        print(f"Removed {count} expired cache entries")
        return 0

    else:
        print("No cache command specified. Use: stats, clear, or cleanup")
        return 1


async def async_main(args: argparse.Namespace, config: Config) -> int:
    """Async main entry point."""
    command_map = {
        "analyze": cmd_analyze,
        "orchestrate": cmd_orchestrate,
        "watch": cmd_watch,
        "cache": cmd_cache,
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
