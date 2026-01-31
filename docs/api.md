# API Reference

This document provides comprehensive API documentation for the Adversarial Debate framework, including detailed examples, parameter descriptions, and usage patterns.

## Table of Contents

- [Quick Start](#quick-start)
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
- [CLI Reference](#cli-reference)
- [Exceptions](#exceptions)

---

## Quick Start

Here's a minimal example to run the full pipeline:

```python
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from adversarial_debate import (
    AgentContext,
    Arbiter,
    BeadStore,
    BreakAgent,
    ChaosAgent,
    ChaosOrchestrator,
    ExploitAgent,
    get_provider,
)


async def analyze_code(code: str, file_path: str) -> dict:
    # Initialize components
    provider = get_provider("anthropic")  # or "mock" for testing
    store = BeadStore("beads/ledger.jsonl")
    
    timestamp = datetime.now(UTC)
    base_context = {
        "run_id": f"run-{timestamp.strftime('%Y%m%d%H%M%S')}",
        "timestamp_iso": timestamp.isoformat(),
        "policy": {},
        "thread_id": "analysis-thread",
    }
    
    # Step 1: Create attack plan
    orchestrator = ChaosOrchestrator(provider, store)
    plan_ctx = AgentContext(
        **base_context,
        task_id="plan",
        inputs={
            "changed_files": [{"path": file_path, "change_type": "modified"}],
            "patches": {file_path: code[:2000]},
        },
    )
    plan_output = await orchestrator.run(plan_ctx)
    
    # Step 2: Run red team agents
    exploit_agent = ExploitAgent(provider, store)
    analysis_ctx = AgentContext(
        **base_context,
        task_id="exploit-analysis",
        inputs={"code": code, "file_path": file_path},
    )
    exploit_output = await exploit_agent.run(analysis_ctx)
    
    # Step 3: Get verdict
    arbiter = Arbiter(provider, store)
    verdict_ctx = AgentContext(
        **base_context,
        task_id="verdict",
        inputs={"findings": exploit_output.result.get("findings", [])},
    )
    verdict_output = await arbiter.run(verdict_ctx)
    
    return verdict_output.result


# Run the analysis
code = Path("src/api/users.py").read_text()
result = asyncio.run(analyze_code(code, "src/api/users.py"))
print(f"Verdict: {result.get('decision')}")
```

---

## Agents

All agents follow the same interface pattern: they receive an `AgentContext` and return an `AgentOutput`.

### AgentContext

The input payload for all agents. Contains run metadata, task information, and agent-specific inputs.

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentContext:
    run_id: str                              # Unique run identifier
    timestamp_iso: str                       # ISO 8601 timestamp
    policy: dict[str, Any]                   # Security policies to enforce
    thread_id: str                           # Workstream identifier
    task_id: str                             # Task within thread
    parent_bead_id: str = ""                 # Parent bead for chaining
    recent_beads: list[Bead] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    repo_files: dict[str, str] = field(default_factory=dict)
```

**Example: Creating context for ExploitAgent**

```python
from datetime import UTC, datetime
from adversarial_debate import AgentContext

context = AgentContext(
    run_id="run-20240115-143022",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={"max_severity": "CRITICAL"},
    thread_id="security-audit-001",
    task_id="exploit-analysis",
    inputs={
        "code": "def get_user(user_id):\n    return db.query(f'SELECT * FROM users WHERE id={user_id}')",
        "file_path": "src/api/users.py",
        "file_paths": ["src/api/users.py"],
        "focus_areas": ["injection", "authentication"],
        "attack_vectors": [
            {"name": "SQL Injection", "category": "A03:2021"}
        ],
    },
)
```

**Example: Creating context for ChaosOrchestrator**

```python
context = AgentContext(
    run_id="run-20240115-143022",
    timestamp_iso=datetime.now(UTC).isoformat(),
    policy={},
    thread_id="security-audit-001",
    task_id="orchestrate",
    inputs={
        "changed_files": [
            {"path": "src/api/users.py", "change_type": "modified"},
            {"path": "src/api/auth.py", "change_type": "added"},
        ],
        "patches": {
            "src/api/users.py": "def get_user(user_id):\n    ...",
            "src/api/auth.py": "def login(username, password):\n    ...",
        },
        "exposure": "public",  # or "authenticated", "internal"
        "time_budget_seconds": 600,
    },
)
```

### AgentOutput

Standardized output from all agent runs.

```python
@dataclass
class AgentOutput:
    agent_name: str              # Name of the agent
    result: dict[str, Any]       # Agent-specific findings
    beads_out: list[Bead]        # Beads to append to ledger
    confidence: float            # Confidence score (0.0-1.0)
    assumptions: list[str]       # Assumptions made
    unknowns: list[str]          # Things that couldn't be determined
    errors: list[str]            # Errors encountered
    
    @property
    def success(self) -> bool:
        return len(self.errors) == 0
```

**Example: Processing agent output**

```python
output = await agent.run(context)

if output.success:
    print(f"Agent: {output.agent_name}")
    print(f"Confidence: {output.confidence:.0%}")
    print(f"Findings: {len(output.result.get('findings', []))}")
    
    for finding in output.result.get("findings", []):
        print(f"  [{finding['severity']}] {finding['title']}")
else:
    print(f"Errors: {output.errors}")
```

### ExploitAgent

Finds security vulnerabilities mapped to OWASP Top 10 categories with working exploit payloads.

| Property | Value |
|----------|-------|
| `name` | `"ExploitAgent"` |
| `bead_type` | `BeadType.EXPLOIT_ANALYSIS` |
| `model_tier` | `ModelTier.HOSTED_LARGE` |

**Input fields (in `context.inputs`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | `str` | Yes | Code to analyze |
| `file_path` | `str` | Yes | Path to the file |
| `file_paths` | `list[str]` | No | All files in scope |
| `focus_areas` | `list[str]` | No | Areas to focus on |
| `attack_vectors` | `list[dict]` | No | Hints from orchestrator |

**Output structure:**

```python
{
    "findings": [
        {
            "finding_id": "EXP-001",
            "title": "SQL Injection in user lookup",
            "severity": "CRITICAL",
            "owasp_category": "A03:2021",
            "cwe_id": "CWE-89",
            "description": "User input directly concatenated into SQL query",
            "vulnerable_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
            "location": {"file": "src/api/users.py", "line": 42, "function": "get_user"},
            "exploit_payload": "1 OR 1=1; DROP TABLE users;--",
            "proof_of_concept": "curl 'http://api/users?id=1%20OR%201=1'",
            "impact": "Full database access",
            "remediation": "Use parameterized queries",
            "confidence": 0.95
        }
    ],
    "summary": {
        "total_findings": 1,
        "by_severity": {"CRITICAL": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    },
    "confidence": 0.92,
    "assumptions": ["Database is PostgreSQL based on query syntax"],
    "unknowns": ["Whether WAF is in place"]
}
```

**Example:**

```python
from adversarial_debate import ExploitAgent, get_provider, BeadStore

provider = get_provider("anthropic")
store = BeadStore()
agent = ExploitAgent(provider, store)

context = AgentContext(
    run_id="run-001",
    timestamp_iso="2024-01-15T14:30:22Z",
    policy={},
    thread_id="audit-001",
    task_id="exploit",
    inputs={
        "code": open("src/api/users.py").read(),
        "file_path": "src/api/users.py",
        "focus_areas": ["injection", "authentication"],
    },
)

output = await agent.run(context)
for finding in output.result.get("findings", []):
    print(f"[{finding['severity']}] {finding['title']}")
```

### BreakAgent

Finds logic bugs, edge cases, race conditions, and state corruption issues.

| Property | Value |
|----------|-------|
| `name` | `"BreakAgent"` |
| `bead_type` | `BeadType.BREAK_ANALYSIS` |
| `model_tier` | `ModelTier.HOSTED_LARGE` |

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | `str` | Yes | Code to analyze |
| `file_path` | `str` | Yes | Path to the file |
| `attack_hints` | `list[dict]` | No | Hints from orchestrator |
| `focus_areas` | `list[str]` | No | Categories to focus on |

**Output structure:**

```python
{
    "findings": [
        {
            "finding_id": "BRK-001",
            "title": "Integer overflow in balance calculation",
            "category": "BOUNDARY",  # BOUNDARY, TYPE_CONFUSION, CONCURRENCY, STATE, RESOURCE
            "severity": "HIGH",
            "description": "Adding large values can overflow int32",
            "vulnerable_code": "new_balance = current_balance + deposit_amount",
            "location": {"file": "src/accounts/balance.py", "line": 87},
            "trigger_condition": "deposit_amount > MAX_INT - current_balance",
            "proof_of_concept": "add_funds(account, 2147483647)",
            "expected_behavior": "Reject deposit or use larger integer type",
            "actual_behavior": "Balance becomes negative",
            "impact": "Financial loss, data corruption",
            "remediation": "Use checked arithmetic or BigInt",
            "confidence": 0.88
        }
    ],
    "summary": {
        "total_findings": 1,
        "by_category": {"BOUNDARY": 1, "CONCURRENCY": 0, "STATE": 0}
    }
}
```

**Example:**

```python
from adversarial_debate import BreakAgent

agent = BreakAgent(provider, store)
context = AgentContext(
    run_id="run-001",
    timestamp_iso="2024-01-15T14:30:22Z",
    policy={},
    thread_id="audit-001",
    task_id="break",
    inputs={
        "code": open("src/accounts/balance.py").read(),
        "file_path": "src/accounts/balance.py",
        "focus_areas": ["boundary", "concurrency"],
    },
)
output = await agent.run(context)
```

### ChaosAgent

Designs resilience experiments to test system behavior under failure conditions.

| Property | Value |
|----------|-------|
| `name` | `"ChaosAgent"` |
| `bead_type` | `BeadType.CHAOS_ANALYSIS` |
| `model_tier` | `ModelTier.HOSTED_SMALL` |

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | `str` | Yes | Code to analyze |
| `file_path` | `str` | Yes | Path to the file |
| `infrastructure_context` | `dict` | No | Deployment info |
| `focus_areas` | `list[str]` | No | Failure modes to test |

**Output structure:**

```python
{
    "experiments": [
        {
            "experiment_id": "CHAOS-001",
            "title": "Database connection pool exhaustion",
            "category": "RESOURCE",
            "description": "Test behavior when all DB connections are in use",
            "hypothesis": "System should queue requests and return 503 after timeout",
            "target_component": "src/db/connection_pool.py",
            "failure_injection": {
                "type": "delay",
                "parameters": {"delay_ms": 30000, "probability": 1.0}
            },
            "expected_behavior": {"graceful_degradation": True},
            "blast_radius": "All database operations",
            "safety_checks": ["Monitor error rate", "Set max duration"],
            "risk_level": "MEDIUM"
        }
    ],
    "resilience_assessment": {
        "score": 65,
        "strengths": ["Retry logic present", "Circuit breaker implemented"],
        "weaknesses": ["No timeout on DB queries", "Missing fallback for cache"],
        "recommendations": ["Add query timeouts", "Implement cache-aside pattern"]
    }
}
```

**Example:**

```python
from adversarial_debate import ChaosAgent

agent = ChaosAgent(provider, store)
context = AgentContext(
    run_id="run-001",
    timestamp_iso="2024-01-15T14:30:22Z",
    policy={},
    thread_id="audit-001",
    task_id="chaos",
    inputs={
        "code": open("src/db/connection_pool.py").read(),
        "file_path": "src/db/connection_pool.py",
        "infrastructure_context": {"database": "postgresql", "cache": "redis"},
    },
)
output = await agent.run(context)
```

### ChaosOrchestrator

Analyzes code changes and creates a coordinated attack plan for red team agents.

| Property | Value |
|----------|-------|
| `name` | `"ChaosOrchestrator"` |
| `bead_type` | `BeadType.ATTACK_PLAN` |
| `model_tier` | `ModelTier.HOSTED_SMALL` |

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `changed_files` | `list[dict]` | Yes | Files that changed |
| `patches` | `dict[str, str]` | Yes | File path to content mapping |
| `exposure` | `str` | No | Exposure level (public/authenticated/internal) |
| `time_budget_seconds` | `int` | No | Total time available |

**Output structure:**

```python
{
    "attack_plan": {
        "plan_id": "PLAN-20240115-143022",
        "risk_level": "HIGH",
        "risk_score": 78,
        "risk_factors": ["Public API", "SQL query construction"],
        "attacks": [
            {
                "id": "ATK-001",
                "agent": "EXPLOIT_AGENT",
                "target_file": "src/api/users.py",
                "target_function": "get_user",
                "priority": "CRITICAL",
                "attack_vectors": [{"name": "SQL Injection", "category": "A03:2021"}],
                "time_budget_seconds": 60
            }
        ],
        "parallel_groups": [
            {"group_id": "PG-001", "attack_ids": ["ATK-001", "ATK-002"]}
        ],
        "execution_order": ["ATK-001", "ATK-002", "ATK-003"]
    },
    "summary": {
        "total_attacks": 3,
        "by_agent": {"EXPLOIT_AGENT": 1, "BREAK_AGENT": 1, "CHAOS_AGENT": 1},
        "estimated_duration_seconds": 180
    }
}
```

**Example:**

```python
from adversarial_debate import ChaosOrchestrator

orchestrator = ChaosOrchestrator(provider, store)
context = AgentContext(
    run_id="run-001",
    timestamp_iso="2024-01-15T14:30:22Z",
    policy={},
    thread_id="audit-001",
    task_id="plan",
    inputs={
        "changed_files": [
            {"path": "src/api/users.py", "change_type": "modified"}
        ],
        "patches": {"src/api/users.py": open("src/api/users.py").read()[:2000]},
        "exposure": "public",
        "time_budget_seconds": 600,
    },
)
plan_output = await orchestrator.run(context)
```

### Arbiter

Reviews findings from all red team agents and renders a final verdict.

| Property | Value |
|----------|-------|
| `name` | `"Arbiter"` |
| `bead_type` | `BeadType.ARBITER_VERDICT` |
| `model_tier` | `ModelTier.HOSTED_LARGE` |

**Input fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `findings` | `list[dict]` | Yes | All findings from agents |
| `original_task` | `str` | No | Description of code change |
| `changed_files` | `list[dict]` | No | Files that were changed |
| `codebase_context` | `dict` | No | Security controls info |

**Output structure:**

```python
{
    "verdict_id": "VERDICT-20240115-143522",
    "decision": "BLOCK",  # BLOCK, WARN, or PASS
    "decision_rationale": "Critical SQL injection requires immediate fix",
    "blocking_issues": [
        {
            "original_id": "EXP-001",
            "validation_status": "CONFIRMED",
            "validated_severity": "CRITICAL",
            "exploitation_difficulty": "TRIVIAL",
            "remediation_effort": "HOURS",
            "suggested_fix": "Use parameterized queries"
        }
    ],
    "warnings": [...],
    "false_positives": [...],
    "remediation_tasks": [
        {
            "finding_id": "EXP-001",
            "title": "Fix SQL injection in user lookup",
            "priority": "CRITICAL",
            "estimated_effort": "HOURS",
            "fix_guidance": "Replace string concatenation with parameterized query"
        }
    ],
    "summary": "1 critical issue must be fixed before merge",
    "should_block": True
}
```

**Example:**

```python
from adversarial_debate import Arbiter

arbiter = Arbiter(provider, store)
context = AgentContext(
    run_id="run-001",
    timestamp_iso="2024-01-15T14:30:22Z",
    policy={},
    thread_id="audit-001",
    task_id="verdict",
    inputs={
        "findings": all_findings,  # Combined from all agents
        "original_task": "Add user lookup endpoint",
        "changed_files": [{"path": "src/api/users.py"}],
    },
)
verdict_output = await arbiter.run(context)

if verdict_output.result.get("should_block"):
    print("BLOCKED: Fix issues before merge")
```

---

## Attack Plan Types

Attack planning types are defined in `adversarial_debate.attack_plan`.

### Core Types

| Type | Description |
|------|-------------|
| `AttackPlan` | Complete attack plan with assignments |
| `Attack` | Single attack assignment |
| `AttackVector` | Specific attack method |
| `ParallelGroup` | Attacks that can run concurrently |
| `SkipReason` | Why a target was skipped |
| `AttackSurface` | Aggregated attack surface analysis |
| `FileRiskProfile` | Per-file risk assessment |

### Enumerations

| Enum | Values |
|------|--------|
| `AgentType` | `BREAK_AGENT`, `EXPLOIT_AGENT`, `CHAOS_AGENT` |
| `AttackPriority` | `CRITICAL` (1), `HIGH` (2), `MEDIUM` (3), `LOW` (4), `MINIMAL` (5) |
| `RiskLevel` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |

See [Data Structures Reference](data-structures.md) for complete type definitions.

---

## Verdict Types

Verdict types are defined in `adversarial_debate.verdict`.

### Core Types

| Type | Description |
|------|-------------|
| `ArbiterVerdict` | Complete verdict with findings and tasks |
| `ValidatedFinding` | Confirmed finding with validation details |
| `RejectedFinding` | False positive with rejection reason |
| `RemediationTask` | Actionable fix task |

### Enumerations

| Enum | Values |
|------|--------|
| `VerdictDecision` | `BLOCK`, `WARN`, `PASS` |
| `FindingValidation` | `CONFIRMED`, `LIKELY`, `UNCERTAIN` |
| `ExploitationDifficulty` | `TRIVIAL`, `EASY`, `MODERATE`, `DIFFICULT`, `THEORETICAL` |
| `RemediationEffort` | `MINUTES`, `HOURS`, `DAYS`, `WEEKS` |

See [Data Structures Reference](data-structures.md) for complete type definitions.

---

## Providers

### get_provider

Factory function to create LLM providers.

```python
from adversarial_debate import get_provider

# Production: requires ANTHROPIC_API_KEY environment variable
provider = get_provider("anthropic")

# Testing/demos: no API key required, deterministic output
provider = get_provider("mock")
```

### LLMProvider Interface

```python
from abc import ABC, abstractmethod
from adversarial_debate.providers import LLMProvider, Message, LLMResponse, ModelTier

class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion from the model."""
        ...
    
    @abstractmethod
    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get the appropriate model name for a given tier."""
        ...
```

### Message and Response Types

```python
@dataclass
class Message:
    role: str      # "system", "user", or "assistant"
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int]  # {"input_tokens": N, "output_tokens": M}
    finish_reason: str | None
```

### Model Tiers

| Tier | Use Case | Anthropic Model |
|------|----------|-----------------|
| `LOCAL_SMALL` | Fast, cheap tasks | (reserved) |
| `HOSTED_SMALL` | Balanced reasoning | Claude Haiku |
| `HOSTED_LARGE` | Deep analysis | Claude Sonnet |

---

## Store (Beads)

The bead store provides event sourcing with an append-only JSONL ledger.

### BeadStore

```python
from adversarial_debate import BeadStore

# Initialize with default path
store = BeadStore()

# Or specify custom path
store = BeadStore("./custom/ledger.jsonl")
```

**Methods:**

| Method | Description |
|--------|-------------|
| `append(bead)` | Thread-safe append single bead |
| `append_many(beads)` | Atomic append multiple beads |
| `iter_all()` | Iterate over all beads |
| `query(...)` | Query with filters |
| `has_idempotency_key(key)` | Check if key exists |
| `get_by_id(bead_id)` | Get bead by ID |
| `get_children(parent_id)` | Get beads with parent |

**Query example:**

```python
# Find all exploit findings in a thread
findings = store.query(
    thread_id="audit-001",
    bead_type=BeadType.EXPLOIT_ANALYSIS,
)

# Check for duplicate processing
if store.has_idempotency_key("audit-001:exploit:users.py"):
    print("Already processed")
```

### Bead Types

| Type | Producer |
|------|----------|
| `ATTACK_PLAN` | ChaosOrchestrator |
| `EXPLOIT_ANALYSIS` | ExploitAgent |
| `BREAK_ANALYSIS` | BreakAgent |
| `CHAOS_ANALYSIS` | ChaosAgent |
| `ARBITER_VERDICT` | Arbiter |

---

## Sandbox

The sandbox provides isolated code execution for testing exploit payloads.

```python
from adversarial_debate import SandboxExecutor, SandboxConfig

config = SandboxConfig(
    timeout_seconds=30,
    memory_limit="256m",
    cpu_limit=0.5,
    use_docker=True,
)
executor = SandboxExecutor(config)

# Execute Python code
result = await executor.execute_python("print('hello')")
print(result.output)  # "hello\n"
print(result.exit_code)  # 0

# Execute with timeout
result = await executor.execute_python("import time; time.sleep(60)")
print(result.timed_out)  # True
```

### SandboxConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `memory_limit` | `str` | `"256m"` | Docker memory limit (best-effort for subprocess) |
| `cpu_limit` | `float` | `0.5` | Docker CPU limit |
| `timeout_seconds` | `int` | `30` | Default execution timeout |
| `max_output_size_bytes` | `int` | `1048576` | Max captured output per stream |
| `network_enabled` | `bool` | `False` | Allow network access |
| `allowed_hosts` | `list[str]` | `[]` | Allowlist (not enforced if `network_enabled=True`) |
| `read_only` | `bool` | `True` | Run container with read-only rootfs |
| `temp_size` | `str` | `"64m"` | Docker tmpfs size |
| `use_docker` | `bool` | `True` | Use Docker backend |
| `docker_image` | `str` | `"python:3.11-slim"` | Docker image |
| `use_subprocess` | `bool` | `True` | Allow subprocess fallback when Docker unavailable |
| `subprocess_timeout` | `int` | `10` | Subprocess timeout cap (seconds) |

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: str
    exit_code: int
    timed_out: bool
    resource_exceeded: bool
    execution_time_ms: int
```

---

## Configuration

### Config Class

```python
from adversarial_debate import Config

# Load from environment variables
config = Config.from_env()

# Load from JSON file
config = Config.from_file("config.json")

# Access configuration
print(config.provider.provider)  # "anthropic"
print(config.bead_ledger_path)   # "./beads/ledger.jsonl"
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | Provider name | `"anthropic"` |
| `LLM_MODEL` | Model override | (provider default) |
| `LLM_TIMEOUT` | Provider request timeout (seconds) | `"120"` |
| `ANTHROPIC_API_KEY` | Anthropic API key | (required for anthropic) |
| `OPENAI_API_KEY` | OpenAI API key | (required for openai) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | (required for azure) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | (required for azure) |
| `OLLAMA_BASE_URL` | Ollama base URL | `"http://localhost:11434"` |
| `ADVERSARIAL_DEBUG` | Enable debug mode | `"false"` |
| `ADVERSARIAL_DRY_RUN` | Enable dry run mode | `"false"` |
| `ADVERSARIAL_LOG_LEVEL` | Log level | `"INFO"` |
| `ADVERSARIAL_LOG_FORMAT` | Log format (`text` or `json`) | `"text"` |
| `ADVERSARIAL_BEAD_LEDGER` | Ledger path | `"./beads/ledger.jsonl"` |
| `ADVERSARIAL_OUTPUT_DIR` | Output directory | `"./output"` |

### Configuration File Format

```json
{
  "provider": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "timeout_seconds": 120,
    "max_retries": 3,
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "sandbox": {
    "timeout_seconds": 30,
    "memory_limit": "256m",
    "cpu_limit": 0.5,
    "use_docker": true,
    "docker_image": "python:3.11-slim",
    "use_subprocess": true,
    "network_enabled": false
  },
  "bead_ledger_path": "./beads/ledger.jsonl",
  "output_dir": "./output",
  "debug": false,
  "dry_run": false
}
```

---

## CLI Reference

### Commands

```bash
# Run single agent analysis
adversarial-debate analyze <agent> <target>
  agent: exploit | break | chaos
  target: file or directory path

# Create attack plan only
adversarial-debate orchestrate <target>

# Run arbiter on findings
# (accepts either a raw findings list, or a full bundle containing a "findings" key)
adversarial-debate verdict <findings.json|bundle.json>

# Run full pipeline
adversarial-debate run <target>
```

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version |
| `-c, --config FILE` | Configuration file |
| `--log-level LEVEL` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `--json-output` | Output as JSON |
| `--dry-run` | Show what would be done |
| `-o, --output PATH` | Output file or directory |

### Examples

```bash
# Analyze a single file for security issues
adversarial-debate analyze exploit src/api/users.py

# Create attack plan for a directory
adversarial-debate orchestrate src/ --time-budget 300

# Run full pipeline with JSON output
adversarial-debate run src/api/ --output results/ --json-output

# Use mock provider for testing
LLM_PROVIDER=mock adversarial-debate run examples/mini-app/
```

---

## Exceptions

All exceptions inherit from `AdversarialDebateError`.

```python
from adversarial_debate.exceptions import (
    AdversarialDebateError,  # Base exception
    AgentError,              # Agent execution errors
    ProviderError,           # LLM provider errors
    SandboxError,            # Sandbox execution errors
    StoreError,              # Bead store errors
)

try:
    output = await agent.run(context)
except AgentError as e:
    print(f"Agent failed: {e}")
except ProviderError as e:
    print(f"LLM error: {e}")
```

### Exception Hierarchy

```
AdversarialDebateError
├── AgentError
│   ├── AgentTimeoutError
│   └── AgentParseError
├── ProviderError
│   ├── RateLimitError
│   └── APIError
├── SandboxError
│   ├── SandboxTimeoutError
│   └── SandboxSecurityError
└── StoreError
    ├── LedgerCorruptError
    └── IdempotencyError
```

---

## Related Documentation

- [Architecture Deep Dive](architecture.md) - System overview and design principles
- [Agent System Documentation](agents.md) - Detailed agent behavior
- [Data Structures Reference](data-structures.md) - Complete type definitions
- [Pipeline Execution Guide](pipeline.md) - Step-by-step walkthrough
