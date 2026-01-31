# Pipeline Execution Guide

This document provides a step-by-step walkthrough of how the Adversarial Debate pipeline executes, from receiving code changes to producing a final verdict.

## Table of Contents

- [Pipeline Overview](#pipeline-overview)
- [Stage 1: Input Collection](#stage-1-input-collection)
- [Stage 2: Attack Planning](#stage-2-attack-planning)
- [Stage 3: Parallel Analysis](#stage-3-parallel-analysis)
- [Stage 4: Verdict Rendering](#stage-4-verdict-rendering)
- [Stage 5: Output Generation](#stage-5-output-generation)
- [Error Handling](#error-handling)
- [Performance Optimisation](#performance-optimisation)

---

## Pipeline Overview

The Adversarial Debate pipeline follows a structured flow that transforms code changes into actionable security assessments:

```
+-------------+     +-------------+     +-------------+     +-------------+     +-------------+
|   INPUT     | --> |    PLAN     | --> |   ANALYZE   | --> |   VERDICT   | --> |   OUTPUT    |
|  Collection |     |  (Orchestr) |     |  (Red Team) |     |  (Arbiter)  |     | Generation  |
+-------------+     +-------------+     +-------------+     +-------------+     +-------------+
      |                   |                   |                   |                   |
      v                   v                   v                   v                   v
  Files &            AttackPlan           Findings          ArbiterVerdict      Reports &
  Patches            + Beads              + Beads              + Beads           Artifacts
```

### Execution Timeline

A typical pipeline run follows this timeline:

```
Time (seconds)
0        30       60       90      120      150      180
|--------|--------|--------|--------|--------|--------|
|<-INPUT->|
         |<----PLAN---->|
                        |<--------ANALYZE-------->|
                        | Exploit |
                        | Break   |  (parallel)
                        | Chaos   |
                                                  |<--VERDICT-->|
                                                               |<-OUTPUT->|
```

---

## Stage 1: Input Collection

The pipeline begins by collecting and preparing the inputs for analysis.

### CLI Entry Point

When invoked via CLI, the `cmd_run` implementation in `src/adversarial_debate/cli_commands.py`
handles input collection (and is re-exported from `adversarial_debate.cli` for compatibility):

```python
async def cmd_run(args: argparse.Namespace, config: Config) -> int:
    target_path = Path(args.target)
    
    # Collect files based on target type
    if target_path.is_file():
        code = target_path.read_text()
        files = [str(target_path)]
        changed_files = [{"path": str(target_path), "change_type": "modified"}]
        patches = {str(target_path): code[:2000]}
    else:
        # Recursively collect Python files
        for py_file in target_path.rglob("*.py"):
            # ... collect file info
```

### Input Data Structure

The collected inputs are structured as:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `changed_files` | `list[dict]` | File system scan | Files to analyse with metadata |
| `patches` | `dict[str, str]` | File content | File path to content/diff mapping |
| `code` | `str` | Concatenated files | All code combined for context |
| `files` | `list[str]` | File paths | List of all file paths |

### Changed File Metadata

Each entry in `changed_files` contains:

```python
{
    "path": "src/api/users.py",
    "change_type": "modified",  # modified, added, deleted
    "lines_changed": 42,        # optional
    "previous_path": None       # for renames
}
```

### Validation

Before proceeding, the pipeline validates:

1. Target path exists
2. At least one file found
3. Files contain non-empty code
4. Configuration is valid

```python
if not files:
    print_error("No Python files found")
    return 1

if not code.strip():
    print_error("No code found to analyse")
    return 1
```

---

## Stage 2: Attack Planning

The ChaosOrchestrator analyses the inputs and creates a coordinated attack plan.

### Orchestrator Initialisation

```python
from adversarial_debate.agents import ChaosOrchestrator
from adversarial_debate.providers import ProviderConfig as RuntimeProviderConfig, get_provider
from adversarial_debate.store import BeadStore

provider = get_provider(
    config.provider.provider,
    RuntimeProviderConfig(
        api_key=config.provider.api_key,
        base_url=config.provider.base_url,
        model=config.provider.model,
        temperature=config.provider.temperature,
        max_tokens=config.provider.max_tokens,
        timeout=float(config.provider.timeout_seconds),
        extra={"max_retries": config.provider.max_retries, **config.provider.extra},
    ),
)
bead_store = BeadStore(config.bead_ledger_path)
orchestrator = ChaosOrchestrator(provider, bead_store)
```

### Context Creation

The orchestrator receives an `AgentContext` with planning inputs:

```python
context = AgentContext(
    run_id=f"run-{timestamp}",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id=f"pipeline-{timestamp}",
    task_id="orchestrate",
    inputs={
        "changed_files": changed_files,
        "patches": patches,
        "exposure": "internal",  # or "public", "authenticated"
        "time_budget_seconds": args.time_budget,
    },
)
```

### Planning Process

The orchestrator's `run()` method executes:

```
1. Build Prompt
   - Include changed files list
   - Include code patches/diffs
   - Add exposure and time constraints
   - Request JSON AttackPlan output

2. Call LLM
   - Use HOSTED_SMALL tier model
   - Enable JSON mode for structured output
   - Apply timeout constraints

3. Parse Response
   - Validate JSON structure
   - Create Attack objects
   - Build ParallelGroup assignments
   - Calculate risk scores

4. Create Bead
   - Generate unique bead_id
   - Set bead_type = ATTACK_PLAN
   - Include full AttackPlan in payload
   - Append to ledger
```

### Attack Plan Output

The orchestrator produces an `AttackPlan`:

```python
attack_plan = AttackPlan(
    plan_id="PLAN-20240115-143022",
    risk_level=RiskLevel.HIGH,
    risk_score=78,
    attacks=[
        Attack(
            id="ATK-001",
            agent=AgentType.EXPLOIT_AGENT,
            target_file="src/api/users.py",
            priority=AttackPriority.CRITICAL,
            attack_vectors=[...],
            time_budget_seconds=60,
        ),
        # ... more attacks
    ],
    parallel_groups=[
        ParallelGroup(
            group_id="PG-001",
            attack_ids=["ATK-001", "ATK-002"],
            estimated_duration_seconds=60,
        ),
    ],
    execution_order=["ATK-001", "ATK-002", "ATK-003"],
)
```

---

## Stage 3: Parallel Analysis

The current CLI runs the three core agents in parallel over the collected code (it does not execute
each `AttackPlan.Attack` as an individual scheduled task).

### Agent Instantiation

```python
from adversarial_debate.agents import BreakAgent, ChaosAgent, ExploitAgent

exploit = ExploitAgent(provider, bead_store)
breaker = BreakAgent(provider, bead_store)
chaos = ChaosAgent(provider, bead_store)
```

### Execution Strategy (Current CLI)

The CLI uses `asyncio.gather(...)` to run the three agents concurrently, bounded by `--parallel`:

```python
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

exploit_output, break_output, chaos_output = await asyncio.gather(
    with_limit(exploit, "exploit"),
    with_limit(breaker, "break"),
    with_limit(chaos, "chaos"),
)
```

### Parallel Execution Visualization

```
Time -->
        |  ExploitAgent  |
        |  BreakAgent    |  <- parallel (bounded by --parallel)
        |  ChaosAgent    |
```

### Collecting Findings

The CLI normalises outputs into a single list:

```python
combined_findings = []
combined_findings.extend(exploit_output.result.get("findings", []))
combined_findings.extend(break_output.result.get("findings", []))
for experiment in chaos_output.result.get("experiments", []):
    f = dict(experiment)
    f["agent"] = "ChaosAgent"
    f["finding_type"] = "chaos_experiment"
    combined_findings.append(f)
```

Each agent still produces its own result shape:

```python
# ExploitAgent output
{
    "findings": [
        {
            "finding_id": "EXP-001",
            "title": "SQL Injection in user lookup",
            "severity": "CRITICAL",
            "owasp_category": "A03:2021",
            # ... full finding details
        }
    ],
    "summary": {
        "total_findings": 3,
        "by_severity": {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1}
    }
}

# BreakAgent output
{
    "findings": [
        {
            "finding_id": "BRK-001",
            "title": "Integer overflow in balance calculation",
            "category": "BOUNDARY",
            # ... full finding details
        }
    ]
}

# ChaosAgent output
{
    "experiments": [
        {
            "experiment_id": "CHAOS-001",
            "title": "Database connection pool exhaustion",
            # ... full experiment details
        }
    ],
    "resilience_assessment": {
        "score": 65,
        "weaknesses": [...]
    }
}
```

### Optional Cross-Examination (Debate)

When running `adversarial-debate run` without `--skip-debate` (and without `--skip-verdict`), the
pipeline runs a `CrossExaminationAgent` step that critiques/refines the merged findings. If it
produces debated findings, they are written to `findings.debated.json` and used for the Arbiter step
and the canonical results bundle.

---

## Stage 4: Verdict Rendering

The Arbiter reviews all findings and renders a final verdict.

### Arbiter Initialisation

```python
from adversarial_debate.agents import Arbiter

arbiter = Arbiter(provider, bead_store)
```

### Consolidating Findings

The Arbiter receives the merged findings from Stage 3. If cross-examination produced debated
findings, those are preferred.

```python
findings_for_verdict = debated_findings if debated_findings is not None else combined_findings

arbiter_context = AgentContext(
    run_id=run_id,
    timestamp_iso=timestamp.isoformat(),
    policy={},
    thread_id=run_id,
    task_id="verdict",
    inputs={
        "findings": findings_for_verdict,
        "original_task": f"CLI run on {args.target}",
        "changed_files": changed_files,
    },
)
```

### Verdict Process

The Arbiter's `run()` method:

```
1. Build Prompt
   - Include all findings from red team
   - Add codebase context
   - Request validation and verdict

2. Call LLM
   - Use HOSTED_LARGE tier for nuanced judgment
   - Enable JSON mode

3. Parse Response
   - Categorize findings (blocking/warning/passed/rejected)
   - Create remediation tasks
   - Calculate overall verdict

4. Create Bead
   - Set bead_type = ARBITER_VERDICT
   - Include full verdict in payload
   - Append to ledger
```

### Verdict Output

```python
verdict = ArbiterVerdict(
    verdict_id="VERDICT-20240115-143522",
    decision=VerdictDecision.BLOCK,
    decision_rationale="Critical SQL injection vulnerability requires immediate fix",
    blocking_issues=[
        ValidatedFinding(
            original_id="EXP-001",
            validation_status=FindingValidation.CONFIRMED,
            validated_severity="CRITICAL",
            exploitation_difficulty=ExploitationDifficulty.TRIVIAL,
            # ...
        )
    ],
    warnings=[...],
    false_positives=[...],
    remediation_tasks=[
        RemediationTask(
            finding_id="EXP-001",
            title="Fix SQL injection in user lookup",
            priority="CRITICAL",
            estimated_effort=RemediationEffort.HOURS,
            # ...
        )
    ],
    summary="1 critical issue must be fixed before merge",
)
```

---

## Stage 5: Output Generation

The pipeline produces various outputs for consumption.

### Output Directory Structure

```
output/
└── run-20240115-143022/
    ├── attack_plan.json          # ChaosOrchestrator output
    ├── exploit_findings.json     # ExploitAgent output
    ├── break_findings.json       # BreakAgent output
    ├── chaos_findings.json       # ChaosAgent output
    ├── findings.json             # Merged findings (pre-debate)
    ├── findings.debated.json     # Merged findings (post-debate, optional)
    ├── verdict.json              # Arbiter output (optional if --skip-verdict)
    ├── bundle.json               # Canonical bundle (override with --bundle-file)
    └── report.<ext>              # Optional formatted report (via --report-file)
```

### Writing Outputs

The CLI writes these artefacts directly during `cmd_run`. See `src/adversarial_debate/cli_commands.py` for the
exact implementation and flags (`--output`, `--bundle-file`, `--report-file`, `--format`,
`--skip-debate`, `--skip-verdict`).

### CLI Output

The CLI provides formatted console output:

```
============================================================
VERDICT: BLOCK
============================================================

*** THIS SHOULD BLOCK THE MERGE ***

Blocking Issues: 1
Warnings: 2
Passed: 5
False Positives: 1

BLOCKING ISSUES:
  [CRITICAL] SQL Injection in user lookup (EXP-001)
    - Exploitation: TRIVIAL
    - Fix effort: HOURS
    - File: src/api/users.py:42

WARNINGS:
  [MEDIUM] Missing rate limiting on login endpoint (EXP-002)
  [LOW] Verbose error messages in production (BRK-003)

REMEDIATION TASKS:
  1. [CRITICAL] Fix SQL injection in user lookup
     Estimated effort: 1-2 hours
     Guidance: Use parameterized queries...

Results saved to: output/run-20240115-143022/
```

### Exit Codes

| Code | Meaning | When |
|------|---------|------|
| `0` | Success | PASS verdict or successful completion |
| `1` | Error | Pipeline error, invalid input |
| `2` | Blocked | BLOCK verdict (security issues found) |

---

## Error Handling

The pipeline includes robust error handling at each stage.

### Agent Timeout Handling

```python
async def run_with_timeout(
    agent: Agent,
    context: AgentContext,
    timeout_seconds: int,
) -> AgentOutput:
    try:
        return await asyncio.wait_for(
            agent.run(context),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.warning(f"{agent.name} timed out after {timeout_seconds}s")
        return AgentOutput(
            agent_name=agent.name,
            result={"error": "timeout", "partial_results": []},
            beads_out=[],
            confidence=0.0,
            assumptions=[],
            unknowns=["Analysis incomplete due to timeout"],
            errors=[f"Timed out after {timeout_seconds} seconds"],
        )
```

### LLM Error Handling

```python
async def safe_llm_call(provider: LLMProvider, messages: list[Message]) -> str:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await provider.complete(messages, json_mode=True)
            return response.content
        except RateLimitError:
            wait_time = 2 ** attempt
            logger.warning(f"Rate limited, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
        except APIError as e:
            logger.error(f"API error: {e}")
            if attempt == max_retries - 1:
                raise
    raise RuntimeError("Max retries exceeded")
```

### Partial Results

If some agents fail, the pipeline continues with available results:

```python
def filter_successful_outputs(outputs: list[AgentOutput]) -> list[AgentOutput]:
    successful = []
    failed = []
    
    for output in outputs:
        if output.errors:
            failed.append(output)
            logger.warning(f"{output.agent_name} had errors: {output.errors}")
        else:
            successful.append(output)
    
    if not successful:
        raise PipelineError("All agents failed")
    
    return successful
```

---

## Performance Optimisation

### Parallel Execution Benefits

Running agents in parallel significantly reduces total execution time:

```
Sequential execution:
  Orchestrator: 30s
  ExploitAgent: 60s
  BreakAgent:   45s
  ChaosAgent:   30s
  Arbiter:      45s
  ─────────────────
  Total:        210s

Parallel execution:
  Orchestrator: 30s
  [Exploit|Break|Chaos]: 60s (max of parallel)
  Arbiter:      45s
  ─────────────────
  Total:        135s (36% faster)
```

### Caching Strategies

The bead ledger enables caching of previous results:

```python
def check_cached_result(
    bead_store: BeadStore,
    idempotency_key: str,
) -> AgentOutput | None:
    if bead_store.has_idempotency_key(idempotency_key):
        bead = bead_store.query(idempotency_key=idempotency_key)[0]
        return reconstruct_output_from_bead(bead)
    return None
```

### Resource Management

The pipeline manages resources to prevent exhaustion:

```python
# Limit concurrent agents
semaphore = asyncio.Semaphore(args.parallel)  # default: 3

async def run_with_limit(agent: Agent, context: AgentContext) -> AgentOutput:
    async with semaphore:
        return await agent.run(context)
```

---

## Complete Pipeline Example

Here's a complete example of running the pipeline programmatically:

```python
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from adversarial_debate.agents import (
    Agent,
    AgentContext,
    AgentOutput,
    Arbiter,
    BreakAgent,
    ChaosAgent,
    ChaosOrchestrator,
    ExploitAgent,
)
from adversarial_debate.config import Config
from adversarial_debate.providers import ProviderConfig as RuntimeProviderConfig, get_provider
from adversarial_debate.results import BundleInputs, build_results_bundle
from adversarial_debate.store import BeadStore


async def run_pipeline(target_path: str, output_dir: str) -> int:
    # Load config from env (or Config.from_file(...))
    config = Config.from_env()

    # Initialise provider + bead store
    provider = get_provider(
        config.provider.provider,
        RuntimeProviderConfig(
            api_key=config.provider.api_key,
            base_url=config.provider.base_url,
            model=config.provider.model,
            temperature=config.provider.temperature,
            max_tokens=config.provider.max_tokens,
            timeout=float(config.provider.timeout_seconds),
            extra={"max_retries": config.provider.max_retries, **config.provider.extra},
        ),
    )
    bead_store = BeadStore(config.bead_ledger_path)

    # Collect inputs
    target = Path(target_path)
    files = [str(p) for p in target.rglob("*.py")] if target.is_dir() else [str(target)]
    changed_files = [{"path": str(f), "change_type": "modified"} for f in files]
    patches = {fp: Path(fp).read_text()[:2000] for fp in files}

    ts = datetime.now(UTC)
    run_id = f"programmatic-run-{ts.strftime('%Y%m%d%H%M%S')}"
    run_dir = Path(output_dir) / f"run-{ts.strftime('%Y%m%d%H%M%S')}"

    # Stage 1: Attack planning
    orchestrator = ChaosOrchestrator(provider, bead_store)
    plan_context = AgentContext(
        run_id=run_id,
        timestamp_iso=ts.isoformat(),
        policy={},
        thread_id=run_id,
        task_id="plan",
        inputs={
            "changed_files": changed_files,
            "patches": patches,
            "time_budget_seconds": 600,
        },
    )
    plan_output = await orchestrator.run(plan_context)

    # Stage 2: Run the three core agents in parallel (current CLI behaviour)
    exploit = ExploitAgent(provider, bead_store)
    breaker = BreakAgent(provider, bead_store)
    chaos = ChaosAgent(provider, bead_store)

    code_parts = []
    for fp in files:
        code_parts.append(f"# File: {fp}\n{Path(fp).read_text()}\n")
    code = "\n".join(code_parts)

    analysis_inputs = {"code": code, "file_path": target_path, "file_paths": files}

    async def run_agent(agent: Agent, task_id: str) -> AgentOutput:
        context = AgentContext(
            run_id=run_id,
            timestamp_iso=ts.isoformat(),
            policy={},
            thread_id=run_id,
            task_id=task_id,
            inputs=analysis_inputs,
        )
        return await agent.run(context)

    exploit_output, break_output, chaos_output = await asyncio.gather(
        run_agent(exploit, "exploit"),
        run_agent(breaker, "break"),
        run_agent(chaos, "chaos"),
    )

    combined_findings = []
    combined_findings.extend(exploit_output.result.get("findings", []))
    combined_findings.extend(break_output.result.get("findings", []))
    for exp in chaos_output.result.get("experiments", []):
        f = dict(exp)
        f["agent"] = "ChaosAgent"
        f["finding_type"] = "chaos_experiment"
        combined_findings.append(f)

    # Stage 3: Verdict (Arbiter)
    arbiter = Arbiter(provider, bead_store)
    verdict_context = AgentContext(
        run_id=run_id,
        timestamp_iso=ts.isoformat(),
        policy={},
        thread_id=run_id,
        task_id="verdict",
        inputs={
            "findings": combined_findings,
            "original_task": f"Programmatic run on {target_path}",
            "changed_files": changed_files,
        },
    )
    verdict_output = await arbiter.run(verdict_context)

    # Stage 4: Write artifacts + canonical bundle
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "attack_plan.json").write_text(json.dumps(plan_output.result, indent=2, default=str))
    (run_dir / "exploit_findings.json").write_text(
        json.dumps(exploit_output.result, indent=2, default=str)
    )
    (run_dir / "break_findings.json").write_text(json.dumps(break_output.result, indent=2, default=str))
    (run_dir / "chaos_findings.json").write_text(json.dumps(chaos_output.result, indent=2, default=str))
    (run_dir / "findings.json").write_text(json.dumps(combined_findings, indent=2, default=str))
    (run_dir / "verdict.json").write_text(json.dumps(verdict_output.result, indent=2, default=str))

    bundle = build_results_bundle(
        inputs=BundleInputs(
            run_id=run_id,
            target=target_path,
            provider=config.provider.provider,
            started_at_iso=ts.isoformat(),
            finished_at_iso=datetime.now(UTC).isoformat(),
            files_analyzed=files,
            time_budget_seconds=600,
            config_path=None,
        ),
        exploit_result=exploit_output.result,
        break_result=break_output.result,
        chaos_result=chaos_output.result,
        arbiter_result=verdict_output.result,
    )
    (run_dir / "bundle.json").write_text(json.dumps(bundle, indent=2, default=str))

    should_block = bool((verdict_output.result.get("summary") or {}).get("should_block"))
    return 2 if should_block else 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_pipeline("src/", "output/"))
    exit(exit_code)
```

---

## Next Steps

For more information, see:

- [Architecture Deep Dive](architecture.md) - System overview
- [Agent System Documentation](agents.md) - Deep dive into each agent
- [Data Structures Reference](data-structures.md) - Complete type definitions
- [API Reference](api.md) - Python API documentation
