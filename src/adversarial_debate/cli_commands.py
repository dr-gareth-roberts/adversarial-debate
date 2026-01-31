"""Command implementations for the adversarial-debate CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from . import __version__
from .cli_output import print_error, print_json
from .cli_provider import _get_provider_from_config
from .config import Config
from .logging import get_logger

logger = get_logger(__name__)


async def cmd_analyze(args: argparse.Namespace, config: Config) -> int:
    """Run a single agent analysis."""
    from .agents import Agent, AgentContext, BreakAgent, ChaosAgent, ExploitAgent
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

    # Create provider, bead store, and agent
    provider = _get_provider_from_config(config)
    bead_store = BeadStore(config.bead_ledger_path)
    agent: Agent
    if args.agent == "exploit":
        agent = ExploitAgent(provider, bead_store)
    elif args.agent == "break":
        agent = BreakAgent(provider, bead_store)
    else:
        agent = ChaosAgent(provider, bead_store)

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
    from .agents import (
        Agent,
        AgentContext,
        AgentOutput,
        Arbiter,
        BreakAgent,
        ChaosAgent,
        ChaosOrchestrator,
        ExploitAgent,
    )
    from .store import BeadStore

    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Target not found: {args.target}")
        return 1

    # Collect files and patches
    file_path = str(target_path)
    code_parts: list[str] = []
    files: list[str] = []
    changed_files: list[dict[str, str]] = []
    patches: dict[str, str] = {}

    if args.files:
        for fp in args.files:
            p = Path(fp)
            if not p.exists() or not p.is_file():
                print_error(f"File not found: {fp}")
                return 1
            files.append(str(p))
            text = p.read_text()
            code_parts.append(f"# File: {p}\n{text}\n")
            changed_files.append({"path": str(p), "change_type": "modified"})
            patches[str(p)] = text[:2000]
        code = "\n".join(code_parts)
    elif target_path.is_file():
        code = target_path.read_text()
        files = [str(target_path)]
        changed_files = [{"path": str(target_path), "change_type": "modified"}]
        patches = {str(target_path): code[:2000]}
    else:
        for py_file in target_path.rglob("*.py"):
            rel_path = str(py_file.relative_to(target_path))
            files.append(str(py_file))
            text = py_file.read_text()
            code_parts.append(f"# File: {py_file}\n{text}\n")
            changed_files.append({"path": rel_path, "change_type": "modified"})
            patches[rel_path] = text[:2000]
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
    provider = _get_provider_from_config(config)
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

    async def run_agent(agent: Agent, task_id: str) -> AgentOutput:
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

    async def with_limit(agent: Agent, task_id: str) -> AgentOutput:
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

    # Cross-examination debate step (ferocious peer review between agents)
    debated_findings = None
    debate_output = None
    if not args.skip_debate and not args.skip_verdict:
        from .agents import CrossExaminationAgent
        from .results import BundleInputs, build_results_bundle

        pre_bundle = build_results_bundle(
            inputs=BundleInputs(
                run_id=run_id,
                target=args.target,
                provider=config.provider.provider,
                started_at_iso=timestamp.isoformat(),
                finished_at_iso=timestamp.isoformat(),
                files_analyzed=files,
                time_budget_seconds=args.time_budget,
                config_path=args.config,
            ),
            exploit_result=exploit_output.result,
            break_result=break_output.result,
            chaos_result=chaos_output.result,
            arbiter_result=None,
        )

        debater = CrossExaminationAgent(provider, bead_store)
        debate_context = AgentContext(
            run_id=run_id,
            timestamp_iso=timestamp.isoformat(),
            policy={},
            thread_id=run_id,
            task_id="cross-examination",
            inputs={
                "findings": pre_bundle.get("findings", []),
                "code_excerpt": analysis_inputs.get("code", "")[:20000],
                "max_findings": args.debate_max_findings,
            },
        )
        try:
            debate_output = await debater.run(debate_context)
            debated_findings = debate_output.result.get("findings", None)
            if isinstance(debated_findings, list):
                from .baseline import compute_fingerprint

                for f in debated_findings:
                    if isinstance(f, dict) and not f.get("fingerprint"):
                        f["fingerprint"] = compute_fingerprint(f)
            debated_path = run_dir / "findings.debated.json"
            with open(debated_path, "w") as f:
                json.dump(debated_findings, f, indent=2, default=str)
        except Exception as e:
            logger.exception("CrossExaminationAgent failed")
            print_error(f"Cross-examination failed (continuing): {e}")

    verdict_output = None
    if not args.skip_verdict:
        arbiter_context = AgentContext(
            run_id=run_id,
            timestamp_iso=timestamp.isoformat(),
            policy={},
            thread_id=run_id,
            task_id="verdict",
            inputs={
                "findings": debated_findings if debated_findings is not None else combined_findings,
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

    # Build canonical bundle + optional formatted report
    finished_at = datetime.now(UTC).isoformat()
    from .results import BundleInputs, build_results_bundle

    bundle = build_results_bundle(
        inputs=BundleInputs(
            run_id=run_id,
            target=args.target,
            provider=config.provider.provider,
            started_at_iso=timestamp.isoformat(),
            finished_at_iso=finished_at,
            files_analyzed=files,
            time_budget_seconds=args.time_budget,
            config_path=args.config,
        ),
        exploit_result=exploit_output.result,
        break_result=break_output.result,
        chaos_result=chaos_output.result,
        arbiter_result=verdict_output.result if verdict_output else None,
    )

    if debate_output and debated_findings is not None:
        # Prefer debated findings in the canonical bundle and recompute counts.
        bundle["findings"] = debated_findings
        bundle_metadata = bundle.get("metadata", {})
        severity_counts: dict[str, int] = {}
        for f in debated_findings:
            sev = str((f or {}).get("severity", "UNKNOWN")).upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        bundle_metadata["finding_counts"] = {
            "total": len(debated_findings),
            "by_severity": severity_counts,
        }
        bundle_metadata["cross_examination"] = debate_output.result.get("summary", {})
        bundle["metadata"] = bundle_metadata

    # Optional baseline diff (for PR workflows: fail only on NEW findings)
    baseline_diff: dict[str, Any] | None = None
    baseline_exit_code: int | None = None
    if args.baseline_file and args.baseline_mode != "off":
        try:
            baseline_bundle = json.loads(Path(args.baseline_file).read_text())
            from .baseline import diff_bundles, severity_gte

            diff = diff_bundles(bundle, baseline_bundle)
            baseline_diff = diff.to_dict()
            bundle["baseline"] = {
                "mode": args.baseline_mode,
                "baseline_file": args.baseline_file,
                **baseline_diff,
            }

            if args.baseline_mode == "only-new" and args.fail_on != "never":
                threshold = str(args.min_severity).upper()
                regressions = [
                    f
                    for f in diff.new
                    if severity_gte(str(f.get("severity", "UNKNOWN")), threshold)
                ]
                if regressions:
                    # Mirror existing convention: 2 means "block".
                    baseline_exit_code = 2
        except Exception as e:
            print_error(f"Failed to apply baseline comparison: {e}")

    bundle_path = Path(args.bundle_file) if args.bundle_file else (run_dir / "bundle.json")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, indent=2, default=str))

    if args.baseline_write:
        baseline_out = Path(args.baseline_write)
        baseline_out.parent.mkdir(parents=True, exist_ok=True)
        baseline_out.write_text(json.dumps(bundle, indent=2, default=str))

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

    if args.baseline_write:
        if not args.json_output:
            print(f"Baseline written: {args.baseline_write}")
        return 0

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
        if baseline_diff:
            print("\nBASELINE DIFF")
            print(f"New: {baseline_diff.get('new_count', 0)}")
            print(f"Fixed: {baseline_diff.get('fixed_count', 0)}")

    if baseline_exit_code is not None:
        return baseline_exit_code

    if args.fail_on != "never" and verdict_output:
        verdict_summary = verdict_output.result.get("summary", {})
        decision = verdict_summary.get("decision")
        should_block = verdict_summary.get("should_block", False)

        if should_block:
            return 2
        if args.fail_on == "warn" and decision in {"WARN", "BLOCK"}:
            return 1

    return 0


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

        for path in changed_paths[:5]:  # Limit to first 5 for performance
            analyze_args = argparse.Namespace(
                agent=args.agent if args.agent != "all" else "exploit",
                target=str(path),
                focus=None,
                timeout=60,
                json_output=json_output_flag,
                output=None,
            )
            try:
                await cmd_analyze(analyze_args, config)
            except Exception as e:
                print_error(f"Analysis failed for {path}: {e}")

    runner = WatchRunner([target_path], analyze_files, watch_config)
    await runner.run()
    return 0


async def cmd_cache(args: argparse.Namespace, config: Config) -> int:
    """Manage analysis cache."""
    from .cache import CacheManager

    cache = CacheManager()

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
