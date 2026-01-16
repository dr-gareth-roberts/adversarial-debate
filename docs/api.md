# API Reference

This document provides API guidance for Adversarial Debate. Examples are minimal and match the current codebase.

## Table of Contents

- [Agents](#agents)
  - [AgentContext](#agentcontext)
  - [AgentOutput](#agentoutput)
  - [ExploitAgent](#exploitagent)
  - [BreakAgent](#breakagent)
  - [ChaosAgent](#chaosagent)
  - [ChaosOrchestrator](#chaosorchestrator)
  - [Arbiter](#arbiter)
- [Attack Plan Types](#attack-plan-types)
- [Verdict Types](#verdict-types)
- [Providers](#providers)
- [Store (Beads)](#store-beads)
- [Sandbox](#sandbox)
- [Configuration](#configuration)
- [Exceptions](#exceptions)

---

## Agents

### AgentContext

The input payload for agents.

```python
from datetime import UTC, datetime
from adversarial_debate import AgentContext

context = AgentContext(
    run_id="run-001",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="thread-001",
    task_id="analysis",
    inputs={
        "code": "def example(): pass",
        "file_path": "example.py",
        "language": "python",
        "exposure": "public",
    },
)
```

Key fields:
- `run_id`, `timestamp_iso`, `thread_id`, `task_id`
- `policy`: optional policy constraints
- `inputs`: agent-specific data (code, file paths, hints)
- `recent_beads` / `repo_files`: optional context

### AgentOutput

Structured output from an agent run.

```python
output = await agent.run(context)

print(output.agent_name)
print(output.result)
print(output.beads_out)
print(output.confidence)
```

Attributes:
- `agent_name`: name of the agent
- `result`: structured JSON-like output
- `beads_out`: list of beads emitted
- `confidence`, `assumptions`, `unknowns`, `errors`

### ExploitAgent

Finds security vulnerabilities (OWASP Top 10) with exploit payloads and remediation guidance.

```python
from adversarial_debate import ExploitAgent, get_provider, BeadStore

provider = get_provider("anthropic")
store = BeadStore()
agent = ExploitAgent(provider, store)
result = await agent.run(context)
```

### BreakAgent

Finds logic bugs, edge cases, and failure modes.

```python
from adversarial_debate import BreakAgent
agent = BreakAgent(provider, store)
result = await agent.run(context)
```

### ChaosAgent

Designs resilience experiments and failure scenarios.

```python
from adversarial_debate import ChaosAgent
agent = ChaosAgent(provider, store)
result = await agent.run(context)
```

### ChaosOrchestrator

Builds an `AttackPlan` describing what each agent should test.

```python
from adversarial_debate import ChaosOrchestrator
orchestrator = ChaosOrchestrator(provider, store)
plan_output = await orchestrator.run(context)
```

### Arbiter

Validates and consolidates findings into an `ArbiterVerdict`.

```python
from adversarial_debate import Arbiter
arbiter = Arbiter(provider, store)
verdict_output = await arbiter.run(context)
```

---

## Attack Plan Types

Attack planning types live in `adversarial_debate.attack_plan`.

Key types:
- `AttackPlan`
- `Attack`, `AttackVector`
- `AgentType`, `AttackPriority`, `RiskLevel`
- `AttackSurface`, `FileRiskProfile`, `ParallelGroup`, `SkipReason`

These are returned by `ChaosOrchestrator` as structured JSON.

---

## Verdict Types

Verdict types live in `adversarial_debate.verdict`.

Key types:
- `ArbiterVerdict`
- `ValidatedFinding`, `RejectedFinding`, `RemediationTask`
- `VerdictDecision`, `FindingValidation`, `ExploitationDifficulty`, `RemediationEffort`

---

## Providers

### get_provider

```python
from adversarial_debate import get_provider

provider = get_provider("anthropic")  # real API
provider = get_provider("mock")       # deterministic demo
```

### LLMProvider

Base class with async `complete()` and `get_model_for_tier()`.

### MockProvider

Deterministic provider used for demos/tests. No API key required.

---

## Store (Beads)

Beads are immutable, append-only event records stored in JSONL.

```python
from adversarial_debate import BeadStore

store = BeadStore("./beads/ledger.jsonl")
```

Common types:
- `BeadStore`, `Bead`, `BeadType`
- `Artefact`, `ArtefactType`

---

## Sandbox

```python
import asyncio
from adversarial_debate import SandboxExecutor, SandboxConfig

config = SandboxConfig(enabled=True, timeout_seconds=30)
executor = SandboxExecutor(config)

async def run():
    result = await executor.execute_python("print('hello')")
    print(result.stdout)

asyncio.run(run())
```

Types:
- `SandboxConfig`
- `SandboxExecutor`
- `ExecutionResult`

---

## Configuration

```python
from adversarial_debate import Config

config = Config.from_env()
config = Config.from_file("config.json")
```

Configuration types:
- `Config`
- `ProviderConfig`
- `LoggingConfig`
- `SandboxConfig`

---

## Exceptions

Exceptions live in `adversarial_debate.exceptions` and are exported at top level.
Key base types:
- `AdversarialDebateError`
- `AgentError`, `ProviderError`, `SandboxError`, `StoreError`
