"""Pipeline service for orchestrating adversarial security analysis."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..agents import (
    Agent,
    AgentContext,
    AgentOutput,
    Arbiter,
    BreakAgent,
    ChaosAgent,
    ChaosOrchestrator,
    CrossExaminationAgent,
    CryptoAgent,
    ExploitAgent,
)
from ..attack_plan import AgentType, AttackPlan
from ..baseline import compute_fingerprint, diff_bundles, severity_gte
from ..cache import CacheManager
from ..config import Config
from ..logging import get_logger
from ..path_filter import DEFAULT_IGNORE_PATTERNS, path_matches_any
from ..providers import LLMProvider
from ..results import BundleInputs, build_results_bundle
from ..store import BeadStore

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""

    target: str
    files: list[str] | None = None
    time_budget: int = 600
    parallel: int = 3
    cache_enabled: bool = False
    skip_debate: bool = False
    skip_verdict: bool = False
    debate_max_findings: int = 40
    baseline_file: str | None = None
    baseline_mode: str = "off"
    fail_on: str = "block"
    min_severity: str = "high"
    config_path: str | None = None


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    success: bool
    exit_code: int
    run_id: str
    run_dir: Path
    bundle: dict[str, Any]
    baseline_diff: dict[str, Any] | None = None
    error: str | None = None


class PipelineService:
    """Service for executing the full adversarial analysis pipeline."""

    def __init__(self, config: Config, provider: LLMProvider, bead_store: BeadStore):
        """Initialize pipeline service.

        Args:
            config: Application configuration
            provider: LLM provider for agent execution
            bead_store: Bead store for coordination
        """
        self.config = config
        self.provider = provider
        self.bead_store = bead_store

    async def execute(self, pipeline_config: PipelineConfig) -> PipelineResult:
        """Execute the full adversarial analysis pipeline.

        Args:
            pipeline_config: Pipeline configuration

        Returns:
            PipelineResult with execution results
        """
        timestamp = datetime.now(UTC)
        run_id = f"cli-run-{timestamp.strftime('%Y%m%d%H%M%S')}"
        run_dir = Path(self.config.output_dir) / f"run-{timestamp.strftime('%Y%m%d%H%M%S')}"
        run_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Collect files and code
            code, files, changed_files, patches = self._collect_files(
                pipeline_config.target, pipeline_config.files
            )

            if not files:
                return PipelineResult(
                    success=False,
                    exit_code=1,
                    run_id=run_id,
                    run_dir=run_dir,
                    bundle={},
                    error="No Python files found",
                )

            if not code.strip():
                return PipelineResult(
                    success=False,
                    exit_code=1,
                    run_id=run_id,
                    run_dir=run_dir,
                    bundle={},
                    error="No code found to analyze",
                )

            # Initialize agents
            orchestrator = ChaosOrchestrator(self.provider, self.bead_store)
            exploit = ExploitAgent(self.provider, self.bead_store)
            breaker = BreakAgent(self.provider, self.bead_store)
            chaos = ChaosAgent(self.provider, self.bead_store)
            crypto = CryptoAgent(self.provider, self.bead_store)
            arbiter = Arbiter(self.provider, self.bead_store)

            # Execute orchestrator
            plan_output = await self._run_orchestrator(
                orchestrator, run_id, timestamp, changed_files, patches, pipeline_config
            )

            # Extract attack plan hints
            hints_by_agent = self._extract_attack_hints(plan_output)

            # Execute agents in parallel
            agent_outputs = await self._run_agents_parallel(
                exploit,
                breaker,
                chaos,
                crypto,
                run_id,
                timestamp,
                code,
                files,
                hints_by_agent,
                pipeline_config,
            )

            # Combine and fingerprint findings
            combined_findings = self._combine_findings(agent_outputs)

            # Persist artifacts
            self._persist_artifacts(
                run_dir, plan_output, agent_outputs, combined_findings
            )

            # Optional debate step
            debated_findings, debate_output = await self._run_debate(
                run_id,
                timestamp,
                combined_findings,
                code,
                agent_outputs,
                pipeline_config,
                run_dir,
            )

            # Optional verdict step
            verdict_output = await self._run_verdict(
                arbiter,
                run_id,
                timestamp,
                debated_findings if debated_findings is not None else combined_findings,
                pipeline_config,
                changed_files,
                run_dir,
            )

            # Build canonical bundle
            bundle = self._build_bundle(
                run_id,
                timestamp,
                pipeline_config,
                files,
                agent_outputs,
                verdict_output,
                debate_output,
                debated_findings,
            )

            # Optional baseline comparison
            baseline_diff, baseline_exit_code = self._compare_baseline(
                bundle, pipeline_config
            )

            # Determine exit code
            exit_code = self._determine_exit_code(
                verdict_output, baseline_exit_code, pipeline_config
            )

            return PipelineResult(
                success=True,
                exit_code=exit_code,
                run_id=run_id,
                run_dir=run_dir,
                bundle=bundle,
                baseline_diff=baseline_diff,
            )

        except Exception as e:
            logger.exception("Pipeline execution failed")
            return PipelineResult(
                success=False,
                exit_code=1,
                run_id=run_id,
                run_dir=run_dir,
                bundle={},
                error=str(e),
            )

    def _collect_files(
        self, target: str, specific_files: list[str] | None
    ) -> tuple[str, list[str], list[dict[str, str]], dict[str, str]]:
        """Collect files and code from target.

        Returns:
            Tuple of (code, files, changed_files, patches)
        """
        target_path = Path(target)
        code_parts: list[str] = []
        files: list[str] = []
        changed_files: list[dict[str, str]] = []
        patches: dict[str, str] = {}

        if specific_files:
            for fp in specific_files:
                p = Path(fp)
                if not p.exists() or not p.is_file():
                    raise FileNotFoundError(f"File not found: {fp}")
                files.append(str(p))
                text = self._read_text_safe(p)
                code_parts.append(f"# File: {p}\n{text}\n")
                changed_files.append({"path": str(p), "change_type": "modified"})
                patches[str(p)] = text[:2000]
            code = "\n".join(code_parts)
        elif target_path.is_file():
            code = self._read_text_safe(target_path)
            files = [str(target_path)]
            changed_files = [{"path": str(target_path), "change_type": "modified"}]
            patches = {str(target_path): code[:2000]}
        else:
            for py_file in self._iter_python_files(target_path, DEFAULT_IGNORE_PATTERNS):
                rel_path = str(py_file.relative_to(target_path))
                files.append(str(py_file))
                text = self._read_text_safe(py_file)
                code_parts.append(f"# File: {py_file}\n{text}\n")
                changed_files.append({"path": rel_path, "change_type": "modified"})
                patches[rel_path] = text[:2000]
            code = "\n".join(code_parts)

        return code, files, changed_files, patches

    def _iter_python_files(self, root: Path, ignore_patterns: list[str]) -> list[Path]:
        """Iterate Python files, excluding ignored patterns."""
        files: list[Path] = []
        for py_file in root.rglob("*.py"):
            if not path_matches_any(py_file, ignore_patterns):
                files.append(py_file)
        return files

    def _read_text_safe(self, path: Path) -> str:
        """Read text with UTF-8 fallback handling."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning("Non-UTF8 file encountered, replacing invalid bytes: %s", path)
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Failed to read file %s: %s", path, exc)
            return ""

    async def _run_orchestrator(
        self,
        orchestrator: ChaosOrchestrator,
        run_id: str,
        timestamp: datetime,
        changed_files: list[dict[str, str]],
        patches: dict[str, str],
        pipeline_config: PipelineConfig,
    ) -> AgentOutput:
        """Run the orchestrator to generate attack plan."""
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
                "time_budget_seconds": pipeline_config.time_budget,
            },
        )

        return await orchestrator.run(orchestrator_context)

    def _extract_attack_hints(self, plan_output: AgentOutput) -> dict[str, dict[str, Any]]:
        """Extract attack hints from orchestrator output."""
        hints_by_agent: dict[str, dict[str, Any]] = {
            "exploit": {},
            "break": {},
            "chaos": {},
            "crypto": {},
        }

        plan_dict = plan_output.result.get("attack_plan")
        if not isinstance(plan_dict, dict):
            return hints_by_agent

        try:
            plan = AttackPlan.from_dict(plan_dict)
        except Exception:
            return hints_by_agent

        for agent_key, agent_type in (
            ("exploit", AgentType.EXPLOIT_AGENT),
            ("break", AgentType.BREAK_AGENT),
            ("chaos", AgentType.CHAOS_AGENT),
            ("crypto", AgentType.CRYPTO_AGENT),
        ):
            attacks = plan.get_attacks_by_agent(agent_type)

            attack_hints: list[str] = []
            focus_areas: list[str] = []
            payload_hints: list[str] = []
            success_indicators: list[str] = []
            hints: list[str] = []

            for a in attacks:
                for v in a.attack_vectors:
                    if v.name:
                        attack_hints.append(v.name)
                    if v.category:
                        focus_areas.append(v.category)
                    payload_hints.extend(v.payload_hints or [])
                    success_indicators.extend(v.success_indicators or [])
                hints.extend(a.hints or [])

            merged: dict[str, Any] = {}
            if attack_hints:
                merged["attack_hints"] = sorted(set(attack_hints))
            if focus_areas:
                merged["focus_areas"] = sorted(set(focus_areas))
            if payload_hints:
                merged["payload_hints"] = payload_hints
            if success_indicators:
                merged["success_indicators"] = success_indicators
            if hints:
                merged["hints"] = hints
            hints_by_agent[agent_key] = merged

        return hints_by_agent

    async def _run_agents_parallel(
        self,
        exploit: ExploitAgent,
        breaker: BreakAgent,
        chaos: ChaosAgent,
        crypto: CryptoAgent,
        run_id: str,
        timestamp: datetime,
        code: str,
        files: list[str],
        hints_by_agent: dict[str, dict[str, Any]],
        pipeline_config: PipelineConfig,
    ) -> dict[str, AgentOutput]:
        """Run all agents in parallel with caching."""
        cache = CacheManager(
            cache_dir=self.config.cache_dir, enabled=pipeline_config.cache_enabled
        )

        base_analysis_inputs = {
            "code": code,
            "file_path": files[0] if files else "",
            "file_paths": files,
        }

        async def run_agent(
            agent: Agent, task_id: str, extra_inputs: dict[str, Any]
        ) -> AgentOutput:
            cached = cache.get_cached(code, agent.name, extra_inputs=extra_inputs)
            if cached is not None:
                logger.info("Cache hit for %s; skipping analysis", agent.name)
                confidence = cached.get("confidence")
                return AgentOutput(
                    agent_name=agent.name,
                    result=cached,
                    beads_out=[],
                    confidence=float(confidence) if isinstance(confidence, int | float) else 1.0,
                )

            analysis_inputs = dict(base_analysis_inputs)
            analysis_inputs.update(extra_inputs)
            context = AgentContext(
                run_id=run_id,
                timestamp_iso=timestamp.isoformat(),
                policy={},
                thread_id=run_id,
                task_id=task_id,
                inputs=analysis_inputs,
            )
            output = await agent.run(context)
            cache.cache_result(
                code, agent.name, base_analysis_inputs["file_path"], output.result, extra_inputs=extra_inputs
            )
            return output

        sem = asyncio.Semaphore(max(1, pipeline_config.parallel))

        async def with_limit(
            agent: Agent, task_id: str, extra_inputs: dict[str, Any]
        ) -> AgentOutput:
            async with sem:
                return await run_agent(agent, task_id, extra_inputs)

        exploit_output, break_output, chaos_output, crypto_output = await asyncio.gather(
            with_limit(exploit, "exploit", hints_by_agent.get("exploit", {})),
            with_limit(breaker, "break", hints_by_agent.get("break", {})),
            with_limit(chaos, "chaos", hints_by_agent.get("chaos", {})),
            with_limit(crypto, "crypto", hints_by_agent.get("crypto", {})),
        )

        return {
            "exploit": exploit_output,
            "break": break_output,
            "chaos": chaos_output,
            "crypto": crypto_output,
        }

    def _combine_findings(self, agent_outputs: dict[str, AgentOutput]) -> list[dict[str, Any]]:
        """Combine findings from all agents and add fingerprints."""
        combined_findings: list[dict[str, Any]] = []
        combined_findings.extend(agent_outputs["exploit"].result.get("findings", []))
        combined_findings.extend(agent_outputs["break"].result.get("findings", []))

        for finding in agent_outputs["crypto"].result.get("findings", []):
            crypto_finding = dict(finding) if isinstance(finding, dict) else {"raw": finding}
            crypto_finding.setdefault("agent", "CryptoAgent")
            crypto_finding.setdefault("finding_type", "crypto")
            combined_findings.append(crypto_finding)

        for experiment in agent_outputs["chaos"].result.get("experiments", []):
            chaos_finding = dict(experiment)
            chaos_finding["agent"] = "ChaosAgent"
            chaos_finding["finding_type"] = "chaos_experiment"
            combined_findings.append(chaos_finding)

        # Fingerprint all findings
        for finding in combined_findings:
            if isinstance(finding, dict) and not finding.get("fingerprint"):
                finding["fingerprint"] = compute_fingerprint(finding)

        return combined_findings

    def _persist_artifacts(
        self,
        run_dir: Path,
        plan_output: AgentOutput,
        agent_outputs: dict[str, AgentOutput],
        combined_findings: list[dict[str, Any]],
    ) -> None:
        """Persist pipeline artifacts to disk."""
        attack_plan_path = run_dir / "attack_plan.json"
        exploit_path = run_dir / "exploit_findings.json"
        break_path = run_dir / "break_findings.json"
        chaos_path = run_dir / "chaos_findings.json"
        crypto_path = run_dir / "crypto_findings.json"
        combined_path = run_dir / "findings.json"

        with open(attack_plan_path, "w") as fh:
            json.dump(plan_output.result, fh, indent=2, default=str)
        with open(exploit_path, "w") as fh:
            json.dump(agent_outputs["exploit"].result, fh, indent=2, default=str)
        with open(break_path, "w") as fh:
            json.dump(agent_outputs["break"].result, fh, indent=2, default=str)
        with open(chaos_path, "w") as fh:
            json.dump(agent_outputs["chaos"].result, fh, indent=2, default=str)
        with open(crypto_path, "w") as fh:
            json.dump(agent_outputs["crypto"].result, fh, indent=2, default=str)
        with open(combined_path, "w") as fh:
            json.dump(combined_findings, fh, indent=2, default=str)

    async def _run_debate(
        self,
        run_id: str,
        timestamp: datetime,
        combined_findings: list[dict[str, Any]],
        code: str,
        agent_outputs: dict[str, AgentOutput],
        pipeline_config: PipelineConfig,
        run_dir: Path,
    ) -> tuple[list[dict[str, Any]] | None, AgentOutput | None]:
        """Run cross-examination debate step."""
        if pipeline_config.skip_debate or pipeline_config.skip_verdict:
            return None, None

        pre_bundle = build_results_bundle(
            inputs=BundleInputs(
                run_id=run_id,
                target=pipeline_config.target,
                provider=self.config.provider.provider,
                started_at_iso=timestamp.isoformat(),
                finished_at_iso=timestamp.isoformat(),
                files_analyzed=[],  # Will be populated from context
                time_budget_seconds=pipeline_config.time_budget,
                config_path=pipeline_config.config_path,
            ),
            exploit_result=agent_outputs["exploit"].result,
            break_result=agent_outputs["break"].result,
            chaos_result=agent_outputs["chaos"].result,
            crypto_result=agent_outputs["crypto"].result,
            arbiter_result=None,
        )

        debater = CrossExaminationAgent(self.provider, self.bead_store)
        debate_context = AgentContext(
            run_id=run_id,
            timestamp_iso=timestamp.isoformat(),
            policy={},
            thread_id=run_id,
            task_id="cross-examination",
            inputs={
                "findings": pre_bundle.get("findings", []),
                "code_excerpt": code[:20000],
                "max_findings": pipeline_config.debate_max_findings,
            },
        )

        try:
            debate_output = await debater.run(debate_context)
            debated_findings = debate_output.result.get("findings", None)
            if isinstance(debated_findings, list):
                for finding in debated_findings:
                    if isinstance(finding, dict) and not finding.get("fingerprint"):
                        finding["fingerprint"] = compute_fingerprint(finding)
            debated_path = run_dir / "findings.debated.json"
            with open(debated_path, "w") as fh:
                json.dump(debated_findings, fh, indent=2, default=str)
            return debated_findings, debate_output
        except Exception as e:
            logger.exception("CrossExaminationAgent failed")
            logger.error("Cross-examination failed (continuing): %s", e)
            return None, None

    async def _run_verdict(
        self,
        arbiter: Arbiter,
        run_id: str,
        timestamp: datetime,
        findings: list[dict[str, Any]],
        pipeline_config: PipelineConfig,
        changed_files: list[dict[str, str]],
        run_dir: Path,
    ) -> AgentOutput | None:
        """Run arbiter verdict step."""
        if pipeline_config.skip_verdict:
            return None

        arbiter_context = AgentContext(
            run_id=run_id,
            timestamp_iso=timestamp.isoformat(),
            policy={},
            thread_id=run_id,
            task_id="verdict",
            inputs={
                "findings": findings,
                "original_task": f"CLI run on {pipeline_config.target}",
                "changed_files": changed_files,
            },
        )

        verdict_output = await arbiter.run(arbiter_context)

        verdict_path = run_dir / "verdict.json"
        with open(verdict_path, "w") as fh:
            json.dump(verdict_output.result, fh, indent=2, default=str)

        return verdict_output

    def _build_bundle(
        self,
        run_id: str,
        timestamp: datetime,
        pipeline_config: PipelineConfig,
        files: list[str],
        agent_outputs: dict[str, AgentOutput],
        verdict_output: AgentOutput | None,
        debate_output: AgentOutput | None,
        debated_findings: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Build canonical results bundle."""
        finished_at = datetime.now(UTC).isoformat()

        bundle = build_results_bundle(
            inputs=BundleInputs(
                run_id=run_id,
                target=pipeline_config.target,
                provider=self.config.provider.provider,
                started_at_iso=timestamp.isoformat(),
                finished_at_iso=finished_at,
                files_analyzed=files,
                time_budget_seconds=pipeline_config.time_budget,
                config_path=pipeline_config.config_path,
            ),
            exploit_result=agent_outputs["exploit"].result,
            break_result=agent_outputs["break"].result,
            chaos_result=agent_outputs["chaos"].result,
            crypto_result=agent_outputs["crypto"].result,
            arbiter_result=verdict_output.result if verdict_output else None,
        )

        if debate_output and debated_findings is not None:
            # Prefer debated findings in the canonical bundle
            bundle["findings"] = debated_findings
            bundle_metadata = bundle.get("metadata", {})
            severity_counts: dict[str, int] = {}
            for finding in debated_findings:
                sev = str((finding or {}).get("severity", "UNKNOWN")).upper()
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            bundle_metadata["finding_counts"] = {
                "total": len(debated_findings),
                "by_severity": severity_counts,
            }
            bundle_metadata["cross_examination"] = debate_output.result.get("summary", {})
            bundle["metadata"] = bundle_metadata

        return bundle

    def _compare_baseline(
        self, bundle: dict[str, Any], pipeline_config: PipelineConfig
    ) -> tuple[dict[str, Any] | None, int | None]:
        """Compare bundle against baseline if configured."""
        if not pipeline_config.baseline_file or pipeline_config.baseline_mode == "off":
            return None, None

        try:
            baseline_bundle = json.loads(Path(pipeline_config.baseline_file).read_text())
            diff = diff_bundles(bundle, baseline_bundle)
            baseline_diff = diff.to_dict()
            bundle["baseline"] = {
                "mode": pipeline_config.baseline_mode,
                "baseline_file": pipeline_config.baseline_file,
                **baseline_diff,
            }

            baseline_exit_code: int | None = None
            if pipeline_config.baseline_mode == "only-new" and pipeline_config.fail_on != "never":
                threshold = str(pipeline_config.min_severity).upper()
                regressions = [
                    finding
                    for finding in diff.new
                    if severity_gte(str(finding.get("severity", "UNKNOWN")), threshold)
                ]
                if regressions:
                    baseline_exit_code = 2

            return baseline_diff, baseline_exit_code
        except Exception as e:
            logger.error("Failed to apply baseline comparison: %s", e)
            return None, None

    def _determine_exit_code(
        self,
        verdict_output: AgentOutput | None,
        baseline_exit_code: int | None,
        pipeline_config: PipelineConfig,
    ) -> int:
        """Determine final exit code based on verdict and baseline."""
        if baseline_exit_code is not None:
            return baseline_exit_code

        if pipeline_config.fail_on != "never" and verdict_output:
            verdict_summary = verdict_output.result.get("summary", {})
            decision = verdict_summary.get("decision")
            should_block = verdict_summary.get("should_block", False)

            if should_block:
                return 2
            if pipeline_config.fail_on == "warn" and decision in {"WARN", "BLOCK"}:
                return 1

        return 0
