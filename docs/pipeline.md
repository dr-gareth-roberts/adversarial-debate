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
- [Performance Optimization](#performance-optimization)

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

When invoked via CLI, the `cmd_run` function in `cli.py` handles input collection:

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
| `changed_files` | `list[dict]` | File system scan | Files to analyze with metadata |
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
    print_error("No code found to analyze")
    return 1
```

---

## Stage 2: Attack Planning

The ChaosOrchestrator analyzes the inputs and creates a coordinated attack plan.

### Orchestrator Initialization

```python
from adversarial_debate.agents import ChaosOrchestrator
from adversarial_debate.providers import get_provider
from adversarial_debate.store import BeadStore

provider = get_provider(config.provider.provider)
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

Red team agents execute their assigned attacks concurrently.

### Agent Instantiation

```python
from adversarial_debate.agents import ExploitAgent, BreakAgent, ChaosAgent

agents = {
    AgentType.EXPLOIT_AGENT: ExploitAgent(provider, bead_store),
    AgentType.BREAK_AGENT: BreakAgent(provider, bead_store),
    AgentType.CHAOS_AGENT: ChaosAgent(provider, bead_store),
}
```

### Execution Strategy

The pipeline uses the attack plan's parallel groups to maximize concurrency:

```python
async def execute_attacks(attack_plan: AttackPlan) -> list[AgentOutput]:
    all_outputs = []
    completed_attacks = set()
    
    # Process in batches based on dependencies
    while len(completed_attacks) < len(attack_plan.attacks):
        # Get attacks ready to run (dependencies satisfied)
        ready = attack_plan.get_ready_attacks(completed_attacks)
        
        # Run ready attacks in parallel
        tasks = []
        for attack in ready:
            agent = agents[attack.agent]
            context = create_attack_context(attack, attack_plan)
            tasks.append(run_with_timeout(agent, context, attack.time_budget_seconds))
        
        # Wait for batch to complete
        batch_outputs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for attack, output in zip(ready, batch_outputs):
            if isinstance(output, Exception):
                output = create_error_output(attack, output)
            all_outputs.append(output)
            completed_attacks.add(attack.id)
    
    return all_outputs
```

### Context for Each Attack

Each agent receives a context tailored to its attack assignment:

```python
def create_attack_context(attack: Attack, plan: AttackPlan) -> AgentContext:
    return AgentContext(
        run_id=plan.plan_id,
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id=plan.thread_id,
        task_id=attack.id,
        parent_bead_id=plan_bead.bead_id,  # Link to attack plan
        inputs={
            "code": get_file_content(attack.target_file),
            "file_path": attack.target_file,
            "target_function": attack.target_function,
            "attack_vectors": [v.__dict__ for v in attack.attack_vectors],
            "hints": attack.hints,
            "focus_areas": [v.category for v in attack.attack_vectors],
        },
    )
```

### Parallel Execution Visualization

```
Time -->
        |  ATK-001 (Exploit)  |
        |  ATK-002 (Break)    |  <- Batch 1 (parallel)
        |  ATK-003 (Chaos)    |
                              |  ATK-004 (Exploit)  |  <- Batch 2 (depends on ATK-001)
                              |  ATK-005 (Break)    |
                                                    |  ATK-006 (Arbiter)  |  <- Final
```

### Collecting Findings

Each agent produces findings in its output:

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

---

## Stage 4: Verdict Rendering

The Arbiter reviews all findings and renders a final verdict.

### Arbiter Initialization

```python
from adversarial_debate.agents import Arbiter

arbiter = Arbiter(provider, bead_store)
```

### Consolidating Findings

All findings from red team agents are collected:

```python
def consolidate_findings(outputs: list[AgentOutput]) -> list[dict]:
    all_findings = []
    
    for output in outputs:
        agent_name = output.agent_name
        
        # Extract findings (different structure per agent)
        if "findings" in output.result:
            for finding in output.result["findings"]:
                finding["source_agent"] = agent_name
                all_findings.append(finding)
        
        if "experiments" in output.result:
            for exp in output.result["experiments"]:
                exp["source_agent"] = agent_name
                exp["finding_type"] = "chaos_experiment"
                all_findings.append(exp)
    
    return all_findings
```

### Arbiter Context

```python
arbiter_context = AgentContext(
    run_id=plan.plan_id,
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id=plan.thread_id,
    task_id="verdict",
    parent_bead_id=plan_bead.bead_id,
    inputs={
        "findings": consolidated_findings,
        "original_task": "Security analysis of code changes",
        "changed_files": changed_files,
        "codebase_context": {
            "security_controls": [...],
            "existing_mitigations": [...],
        },
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
    ├── attack_plan.json      # Full attack plan
    ├── findings/
    │   ├── exploit.json      # ExploitAgent findings
    │   ├── break.json        # BreakAgent findings
    │   └── chaos.json        # ChaosAgent experiments
    ├── verdict.json          # Arbiter verdict
    ├── report.md             # Human-readable report
    └── summary.json          # Executive summary
```

### Writing Outputs

```python
def write_outputs(
    output_dir: Path,
    attack_plan: AttackPlan,
    agent_outputs: list[AgentOutput],
    verdict: ArbiterVerdict,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write attack plan
    with open(output_dir / "attack_plan.json", "w") as f:
        json.dump(attack_plan.__dict__, f, indent=2, default=str)
    
    # Write findings by agent
    findings_dir = output_dir / "findings"
    findings_dir.mkdir(exist_ok=True)
    for output in agent_outputs:
        filename = f"{output.agent_name.lower().replace('agent', '')}.json"
        with open(findings_dir / filename, "w") as f:
            json.dump(output.result, f, indent=2, default=str)
    
    # Write verdict
    with open(output_dir / "verdict.json", "w") as f:
        json.dump(verdict.__dict__, f, indent=2, default=str)
    
    # Generate and write report
    report = verdict.generate_summary_report()
    with open(output_dir / "report.md", "w") as f:
        f.write(report)
```

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

## Performance Optimization

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
from datetime import UTC, datetime
from pathlib import Path

from adversarial_debate.agents import (
    AgentContext,
    Arbiter,
    BreakAgent,
    ChaosAgent,
    ChaosOrchestrator,
    ExploitAgent,
)
from adversarial_debate.providers import get_provider
from adversarial_debate.store import BeadStore


async def run_pipeline(target_path: str, output_dir: str) -> int:
    # Initialize components
    provider = get_provider("anthropic")
    bead_store = BeadStore("beads/ledger.jsonl")
    
    # Collect inputs
    target = Path(target_path)
    files = list(target.rglob("*.py"))
    changed_files = [{"path": str(f), "change_type": "modified"} for f in files]
    patches = {str(f): f.read_text()[:2000] for f in files}
    
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    thread_id = f"pipeline-{timestamp}"
    
    # Stage 1: Attack Planning
    orchestrator = ChaosOrchestrator(provider, bead_store)
    plan_context = AgentContext(
        run_id=f"run-{timestamp}",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id=thread_id,
        task_id="orchestrate",
        inputs={
            "changed_files": changed_files,
            "patches": patches,
            "time_budget_seconds": 600,
        },
    )
    plan_output = await orchestrator.run(plan_context)
    attack_plan = plan_output.result["attack_plan"]
    
    # Stage 2: Parallel Analysis
    agents = {
        "EXPLOIT_AGENT": ExploitAgent(provider, bead_store),
        "BREAK_AGENT": BreakAgent(provider, bead_store),
        "CHAOS_AGENT": ChaosAgent(provider, bead_store),
    }
    
    async def run_attack(attack: dict) -> dict:
        agent = agents[attack["agent"]]
        context = AgentContext(
            run_id=f"run-{timestamp}",
            timestamp_iso=datetime.now(UTC).isoformat(),
            policy={},
            thread_id=thread_id,
            task_id=attack["id"],
            inputs={
                "code": Path(attack["target_file"]).read_text(),
                "file_path": attack["target_file"],
                "attack_vectors": attack.get("attack_vectors", []),
            },
        )
        return await agent.run(context)
    
    tasks = [run_attack(a) for a in attack_plan["attacks"]]
    agent_outputs = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Stage 3: Verdict
    findings = []
    for output in agent_outputs:
        if not isinstance(output, Exception):
            findings.extend(output.result.get("findings", []))
    
    arbiter = Arbiter(provider, bead_store)
    verdict_context = AgentContext(
        run_id=f"run-{timestamp}",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id=thread_id,
        task_id="verdict",
        inputs={"findings": findings},
    )
    verdict_output = await arbiter.run(verdict_context)
    
    # Stage 4: Output
    out_path = Path(output_dir) / f"run-{timestamp}"
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Write results...
    
    # Return exit code based on verdict
    if verdict_output.result.get("decision") == "BLOCK":
        return 2
    return 0


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
