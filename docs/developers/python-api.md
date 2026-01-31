# Python API Guide

Use Adversarial Debate programmatically in your Python applications.

## Installation

```bash
pip install adversarial-debate
```

## Quick Start

```python
import asyncio
from datetime import UTC, datetime

from adversarial_debate import (
    AgentContext,
    ExploitAgent,
    get_provider,
    BeadStore,
)


async def analyse_code(code: str, file_path: str) -> dict:
    # Initialise provider and store
    provider = get_provider("anthropic")  # or "mock" for testing
    store = BeadStore()

    # Create agent
    agent = ExploitAgent(provider, store)

    # Build context
    context = AgentContext(
        run_id=f"run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id="my-analysis",
        task_id="exploit",
        inputs={
            "code": code,
            "file_path": file_path,
        },
    )

    # Run analysis
    output = await agent.run(context)
    return output.result


# Example usage
code = '''
def get_user(user_id):
    return db.execute(f"SELECT * FROM users WHERE id = {user_id}")
'''

result = asyncio.run(analyse_code(code, "app.py"))
print(f"Found {len(result.get('findings', []))} issues")
```

## Core Components

### Providers

Providers handle communication with LLM backends.

```python
from adversarial_debate import get_provider
from adversarial_debate.providers import ProviderConfig

# Default provider (uses environment variables)
provider = get_provider("anthropic")

# With explicit configuration
provider = get_provider(
    "anthropic",
    ProviderConfig(
        api_key="sk-ant-...",
        model="claude-sonnet-4-20250514",
        temperature=0.7,
        max_tokens=4096,
        timeout=120.0,
    ),
)

# Mock provider for testing
provider = get_provider("mock")
```

### BeadStore

The bead store manages the event sourcing ledger.

```python
from adversarial_debate import BeadStore

# Default location
store = BeadStore()

# Custom location
store = BeadStore("./my-project/beads/ledger.jsonl")

# Query beads
for bead in store.iter_all():
    print(f"{bead.bead_id}: {bead.agent} - {bead.bead_type}")

# Query with filters
exploit_beads = store.query(bead_type="EXPLOIT_ANALYSIS", limit=10)

# Check for existing work
if store.has_idempotency_key("my-unique-key"):
    print("Already processed")
```

### AgentContext

Context provides all information agents need for analysis.

```python
from adversarial_debate import AgentContext

context = AgentContext(
    # Run metadata
    run_id="run-001",
    timestamp_iso="2024-01-15T14:30:22Z",

    # Policy constraints
    policy={"max_severity": "HIGH"},

    # Workstream identification
    thread_id="pr-123",
    task_id="security-review",

    # Optional: link to parent bead
    parent_bead_id="B-20240115-143022-000001",

    # Agent-specific inputs
    inputs={
        "code": "...",
        "file_path": "src/api/users.py",
        "focus_areas": ["injection", "authentication"],
    },

    # Repository context (optional)
    repo_files={
        "src/api/users.py": "...",
        "src/api/auth.py": "...",
    },
)
```

## Agents

### ExploitAgent

Finds security vulnerabilities.

```python
from adversarial_debate import ExploitAgent

agent = ExploitAgent(provider, store)

context = AgentContext(
    run_id="run-001",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="audit",
    task_id="exploit",
    inputs={
        "code": code,
        "file_path": "src/api/users.py",
        "focus_areas": ["injection", "authentication"],
        "attack_vectors": [
            {"name": "SQL Injection", "category": "A03:2021"}
        ],
    },
)

output = await agent.run(context)

# Access results
for finding in output.result.get("findings", []):
    print(f"[{finding['severity']}] {finding['title']}")
    print(f"  Location: {finding['location']['file']}:{finding['location']['line']}")
    print(f"  Remediation: {finding['remediation']}")
```

### BreakAgent

Finds logic bugs and edge cases.

```python
from adversarial_debate import BreakAgent

agent = BreakAgent(provider, store)

context = AgentContext(
    run_id="run-001",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="audit",
    task_id="break",
    inputs={
        "code": code,
        "file_path": "src/core/calculator.py",
        "focus_areas": ["boundary", "concurrency"],
    },
)

output = await agent.run(context)
```

### ChaosAgent

Designs resilience experiments.

```python
from adversarial_debate import ChaosAgent

agent = ChaosAgent(provider, store)

context = AgentContext(
    run_id="run-001",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="audit",
    task_id="chaos",
    inputs={
        "code": code,
        "file_path": "src/services/api_client.py",
        "infrastructure_context": {
            "database": "postgresql",
            "cache": "redis",
        },
    },
)

output = await agent.run(context)
```

### CryptoAgent

Finds cryptographic weaknesses.

```python
from adversarial_debate import CryptoAgent

agent = CryptoAgent(provider, store)

context = AgentContext(
    run_id="run-001",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="audit",
    task_id="crypto",
    inputs={
        "code": code,
        "file_path": "src/auth/tokens.py",
    },
)

output = await agent.run(context)
```

### ChaosOrchestrator

Creates attack plans.

```python
from adversarial_debate import ChaosOrchestrator

orchestrator = ChaosOrchestrator(provider, store)

context = AgentContext(
    run_id="run-001",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="audit",
    task_id="orchestrate",
    inputs={
        "changed_files": [
            {"path": "src/api/users.py", "change_type": "modified"},
        ],
        "patches": {
            "src/api/users.py": code[:2000],
        },
        "exposure": "public",
        "time_budget_seconds": 600,
    },
)

output = await orchestrator.run(context)
attack_plan = output.result.get("attack_plan")
```

### Arbiter

Renders verdicts on findings.

```python
from adversarial_debate import Arbiter

arbiter = Arbiter(provider, store)

context = AgentContext(
    run_id="run-001",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="audit",
    task_id="verdict",
    inputs={
        "findings": all_findings,  # From other agents
        "original_task": "Security review of API",
        "changed_files": changed_files,
    },
)

output = await arbiter.run(context)
verdict = output.result

if verdict.get("decision") == "BLOCK":
    print("Critical issues found!")
```

## Full Pipeline

Run the complete analysis pipeline programmatically.

```python
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from adversarial_debate import (
    AgentContext,
    Arbiter,
    BeadStore,
    BreakAgent,
    ChaosAgent,
    ChaosOrchestrator,
    CryptoAgent,
    ExploitAgent,
    get_provider,
)
from adversarial_debate.providers import ProviderConfig
from adversarial_debate.config import Config


async def run_full_pipeline(target_path: str) -> dict:
    # Load configuration
    config = Config.from_env()

    # Initialise components
    provider = get_provider(
        config.provider.provider,
        ProviderConfig(
            api_key=config.provider.api_key,
            model=config.provider.model,
            timeout=config.provider.timeout_seconds,
        ),
    )
    store = BeadStore(config.bead_ledger_path)

    # Collect files
    target = Path(target_path)
    if target.is_file():
        files = [target]
    else:
        files = list(target.rglob("*.py"))

    # Read code
    code_parts = []
    for f in files:
        code_parts.append(f"# File: {f}\n{f.read_text()}\n")
    code = "\n".join(code_parts)

    # Prepare context
    ts = datetime.now(UTC)
    run_id = f"run-{ts.strftime('%Y%m%d%H%M%S')}"
    base_context = {
        "run_id": run_id,
        "timestamp_iso": ts.isoformat(),
        "policy": {},
        "thread_id": run_id,
    }

    # Stage 1: Orchestrate
    orchestrator = ChaosOrchestrator(provider, store)
    plan_ctx = AgentContext(
        **base_context,
        task_id="orchestrate",
        inputs={
            "changed_files": [
                {"path": str(f), "change_type": "modified"}
                for f in files
            ],
            "patches": {str(f): f.read_text()[:2000] for f in files},
        },
    )
    plan_output = await orchestrator.run(plan_ctx)

    # Stage 2: Analyse (parallel)
    analysis_inputs = {
        "code": code,
        "file_path": str(target_path),
        "file_paths": [str(f) for f in files],
    }

    exploit = ExploitAgent(provider, store)
    breaker = BreakAgent(provider, store)
    chaos = ChaosAgent(provider, store)
    crypto = CryptoAgent(provider, store)

    exploit_output, break_output, chaos_output, crypto_output = await asyncio.gather(
        exploit.run(AgentContext(**base_context, task_id="exploit", inputs=analysis_inputs)),
        breaker.run(AgentContext(**base_context, task_id="break", inputs=analysis_inputs)),
        chaos.run(AgentContext(**base_context, task_id="chaos", inputs=analysis_inputs)),
        crypto.run(AgentContext(**base_context, task_id="crypto", inputs=analysis_inputs)),
    )

    # Combine findings
    combined_findings = []
    combined_findings.extend(exploit_output.result.get("findings", []))
    combined_findings.extend(break_output.result.get("findings", []))
    combined_findings.extend(crypto_output.result.get("findings", []))
    for exp in chaos_output.result.get("experiments", []):
        exp["agent"] = "ChaosAgent"
        exp["finding_type"] = "chaos_experiment"
        combined_findings.append(exp)

    # Stage 3: Verdict
    arbiter = Arbiter(provider, store)
    verdict_ctx = AgentContext(
        **base_context,
        task_id="verdict",
        inputs={
            "findings": combined_findings,
            "original_task": f"Analysis of {target_path}",
        },
    )
    verdict_output = await arbiter.run(verdict_ctx)

    return {
        "attack_plan": plan_output.result,
        "exploit_findings": exploit_output.result,
        "break_findings": break_output.result,
        "chaos_findings": chaos_output.result,
        "crypto_findings": crypto_output.result,
        "combined_findings": combined_findings,
        "verdict": verdict_output.result,
    }


# Run the pipeline
result = asyncio.run(run_full_pipeline("src/"))
print(f"Verdict: {result['verdict'].get('decision')}")
```

## Sandbox Execution

Execute code safely in isolation.

```python
from adversarial_debate import SandboxExecutor, SandboxConfig

config = SandboxConfig(
    timeout_seconds=30,
    memory_limit="256m",
    cpu_limit=0.5,
    network_enabled=False,
    use_docker=True,
)

executor = SandboxExecutor(config)


async def test_code():
    result = await executor.execute_python("print('Hello')")
    print(f"Output: {result.output}")
    print(f"Exit code: {result.exit_code}")
    print(f"Timed out: {result.timed_out}")


asyncio.run(test_code())
```

## Output Formatting

Generate formatted reports.

```python
from adversarial_debate.formatters import (
    JSONFormatter,
    SARIFFormatter,
    HTMLFormatter,
    MarkdownFormatter,
)
from adversarial_debate.results import BundleInputs, build_results_bundle

# Build canonical bundle
bundle = build_results_bundle(
    inputs=BundleInputs(
        run_id=run_id,
        target="src/",
        provider="anthropic",
        started_at_iso=started.isoformat(),
        finished_at_iso=finished.isoformat(),
        files_analysed=[str(f) for f in files],
    ),
    exploit_result=exploit_output.result,
    break_result=break_output.result,
    chaos_result=chaos_output.result,
    arbiter_result=verdict_output.result,
)

# Format as SARIF
sarif = SARIFFormatter().format(bundle)
Path("findings.sarif").write_text(sarif)

# Format as HTML
html = HTMLFormatter().format(bundle)
Path("report.html").write_text(html)

# Format as Markdown
md = MarkdownFormatter().format(bundle)
Path("SECURITY.md").write_text(md)
```

## Error Handling

```python
from adversarial_debate.exceptions import (
    AdversarialDebateError,
    AgentError,
    ProviderError,
    SandboxError,
)

try:
    output = await agent.run(context)
except ProviderError as e:
    print(f"LLM provider error: {e}")
except AgentError as e:
    print(f"Agent error: {e}")
except SandboxError as e:
    print(f"Sandbox error: {e}")
except AdversarialDebateError as e:
    print(f"Framework error: {e}")
```

## Type Hints

Full type annotations are available:

```python
from adversarial_debate import (
    AgentContext,
    AgentOutput,
    Bead,
    BeadType,
)
from adversarial_debate.attack_plan import (
    AttackPlan,
    Attack,
    AttackVector,
    AgentType,
    AttackPriority,
    RiskLevel,
)
from adversarial_debate.verdict import (
    ArbiterVerdict,
    ValidatedFinding,
    RejectedFinding,
    RemediationTask,
    VerdictDecision,
    ExploitationDifficulty,
    RemediationEffort,
)
```

## See Also

- [Extending Agents](extending-agents.md) — Create custom agents
- [Event Sourcing](event-sourcing.md) — Bead system details
- [Testing Guide](testing.md) — Testing your integration
- [Data Structures](../reference/data-structures.md) — Type reference
