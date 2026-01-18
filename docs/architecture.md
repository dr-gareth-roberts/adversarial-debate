# Architecture Deep Dive

This document provides a comprehensive technical overview of the Adversarial Debate framework, explaining how the multi-agent system works together to identify security vulnerabilities, logic bugs, and resilience issues in code.

## Table of Contents

- [System Overview](#system-overview)
- [High-Level Architecture](#high-level-architecture)
- [Agent Execution Model](#agent-execution-model)
- [Data Flow](#data-flow)
- [Event Sourcing with Beads](#event-sourcing-with-beads)
- [LLM Provider Abstraction](#llm-provider-abstraction)
- [Parallel Execution Strategy](#parallel-execution-strategy)
- [Security Model](#security-model)

---

## System Overview

Adversarial Debate is a **multi-agent AI security testing framework** that simulates a team of expert security researchers conducting adversarial analysis through structured debate. Unlike traditional static analysis tools that rely on pattern matching, this system uses large language models to reason about vulnerabilities in context, understand code semantics, and provide nuanced security assessments.

### Core Design Principles

The framework is built on several key principles that guide its architecture:

**Separation of Concerns** means each agent specializes in a specific type of analysis. The ExploitAgent focuses on OWASP Top 10 security vulnerabilities, the BreakAgent targets logic bugs and edge cases, and the ChaosAgent designs resilience experiments. This specialization allows each agent to have deep expertise in its domain.

**Stateless Execution** ensures agents are pure functions that receive context and produce output without maintaining internal state. This design enables parallel execution, reproducibility, and easy testing. All state is externalized to the bead ledger.

**Event Sourcing** records every agent action as an immutable "bead" in an append-only ledger. This provides complete audit trails, enables replay and debugging, and supports idempotency for safe retries.

**Structured Output** requires all agents to produce JSON-formatted findings with consistent schemas. This enables automated processing, aggregation, and integration with CI/CD pipelines.

---

## High-Level Architecture

The system consists of five main layers that work together to analyze code and produce security verdicts:

```
+------------------------------------------------------------------+
|                         CLI / Python API                          |
|                    (Entry Points & Orchestration)                 |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
|                      ChaosOrchestrator                           |
|              (Attack Planning & Agent Coordination)              |
|                                                                  |
|  - Analyzes code changes and risk factors                        |
|  - Creates AttackPlan with agent assignments                     |
|  - Optimizes for parallel execution                              |
+------------------------------------------------------------------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+----------------+    +----------------+    +----------------+
|  ExploitAgent  |    |   BreakAgent   |    |   ChaosAgent   |
|                |    |                |    |                |
| OWASP Top 10   |    | Logic Bugs     |    | Resilience     |
| SQL Injection  |    | Edge Cases     |    | Failure Modes  |
| Auth Bypass    |    | Race Conds     |    | Dependencies   |
| XSS, SSRF      |    | State Corrupt  |    | Network Chaos  |
+----------------+    +----------------+    +----------------+
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                                v
+------------------------------------------------------------------+
|                           Arbiter                                |
|                (Validation & Verdict Rendering)                  |
|                                                                  |
|  - Reviews findings from all red team agents                     |
|  - Validates exploitability in context                           |
|  - Renders BLOCK / WARN / PASS verdict                           |
|  - Creates remediation tasks                                     |
+------------------------------------------------------------------+
                                |
                                v
+------------------------------------------------------------------+
|                         BeadStore                                |
|                  (Event Sourcing & Audit Trail)                  |
|                                                                  |
|  - Append-only JSONL ledger                                      |
|  - Thread-safe with file locking                                 |
|  - Idempotency key tracking                                      |
+------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Model Tier | Output |
|-----------|---------------|------------|--------|
| **ChaosOrchestrator** | Analyzes code, creates attack plan, assigns agents | HOSTED_SMALL | AttackPlan bead |
| **ExploitAgent** | Finds OWASP Top 10 security vulnerabilities | HOSTED_LARGE | Exploit findings |
| **BreakAgent** | Finds logic bugs, edge cases, race conditions | HOSTED_LARGE | Break findings |
| **ChaosAgent** | Designs resilience experiments | HOSTED_SMALL | Chaos experiments |
| **Arbiter** | Validates findings, renders verdict | HOSTED_LARGE | ArbiterVerdict |
| **BeadStore** | Persists all events for audit | N/A | JSONL ledger |

---

## Agent Execution Model

All agents inherit from the abstract `Agent` base class and follow a consistent execution pattern. This uniformity enables the framework to treat agents interchangeably while allowing each to specialize in its domain.

### Agent Lifecycle

```
                    +------------------+
                    |  AgentContext    |
                    |  (Input Data)    |
                    +--------+---------+
                             |
                             v
+------------------------------------------------------------------+
|                        Agent.run()                               |
|                                                                  |
|  1. _build_prompt(context)     Build LLM messages from context   |
|  2. provider.complete()        Call LLM with JSON mode           |
|  3. _parse_response()          Parse JSON into structured output |
|  4. _create_bead()             Create audit record               |
|  5. bead_store.append()        Persist to ledger                 |
|                                                                  |
+------------------------------------------------------------------+
                             |
                             v
                    +------------------+
                    |   AgentOutput    |
                    |  (Result Data)   |
                    +------------------+
```

### AgentContext Structure

The `AgentContext` dataclass contains all information an agent needs to perform its analysis:

```python
@dataclass
class AgentContext:
    # Run metadata
    run_id: str              # Unique identifier for this run
    timestamp_iso: str       # ISO timestamp for ordering
    
    # Policy and constraints
    policy: dict[str, Any]   # Security policies to enforce
    
    # Bead context for traceability
    thread_id: str           # Workstream identifier
    task_id: str             # Specific task within thread
    parent_bead_id: str      # Parent bead for chaining
    recent_beads: list[Bead] # Recent context for continuity
    
    # Task-specific inputs (varies by agent)
    inputs: dict[str, Any]   # Code, file paths, hints, etc.
    
    # Repository context
    repo_files: dict[str, str]  # path -> content mapping
```

### AgentOutput Structure

Every agent produces an `AgentOutput` with a consistent structure:

```python
@dataclass
class AgentOutput:
    agent_name: str              # Which agent produced this
    result: dict[str, Any]       # Agent-specific findings
    beads_out: list[Bead]        # Beads to append to ledger
    confidence: float            # 0.0 to 1.0 confidence score
    assumptions: list[str]       # Assumptions made during analysis
    unknowns: list[str]          # Things that couldn't be determined
    errors: list[str]            # Any errors encountered
```

### Model Tier Selection

Different agents require different levels of reasoning capability. The framework uses a tiered model system to balance cost and capability:

| Tier | Use Case | Typical Model | Agents |
|------|----------|---------------|--------|
| **LOCAL_SMALL** | Fast, cheap tasks | Local LLM | (Reserved for future) |
| **HOSTED_SMALL** | Balanced reasoning | Claude Haiku | ChaosOrchestrator, ChaosAgent |
| **HOSTED_LARGE** | Deep analysis | Claude Sonnet | ExploitAgent, BreakAgent, Arbiter |

The rationale for tier assignment is based on the complexity of reasoning required. Security vulnerability detection (ExploitAgent) and logic bug finding (BreakAgent) require understanding subtle code patterns and potential attack vectors, necessitating stronger models. The Arbiter must make nuanced judgments about exploitability and impact, also requiring strong reasoning. The ChaosOrchestrator and ChaosAgent perform more structured tasks with clearer patterns, allowing the use of smaller models.

---

## Data Flow

Understanding how data flows through the system is essential for debugging and extending the framework.

### Full Pipeline Execution

```
Input: Source Code / Changed Files
         |
         v
+------------------+
| 1. ORCHESTRATE   |  ChaosOrchestrator analyzes code
|                  |  Creates AttackPlan with assignments
|                  |  Emits: ATTACK_PLAN bead
+--------+---------+
         |
         | AttackPlan
         v
+------------------+
| 2. ANALYZE       |  Red team agents run in parallel
|                  |  Each agent analyzes assigned targets
|    +----------+  |
|    | Exploit  |--+-> Emits: EXPLOIT_ANALYSIS bead
|    +----------+  |
|    +----------+  |
|    | Break    |--+-> Emits: BREAK_ANALYSIS bead
|    +----------+  |
|    +----------+  |
|    | Chaos    |--+-> Emits: CHAOS_ANALYSIS bead
|    +----------+  |
+--------+---------+
         |
         | Combined Findings
         v
+------------------+
| 3. ARBITRATE     |  Arbiter reviews all findings
|                  |  Validates exploitability
|                  |  Renders verdict
|                  |  Emits: ARBITER_VERDICT bead
+--------+---------+
         |
         v
Output: ArbiterVerdict (BLOCK / WARN / PASS)
        + Remediation Tasks
```

### Data Transformation at Each Stage

**Stage 1: Orchestration**

| Input | Processing | Output |
|-------|------------|--------|
| Changed files list | Risk assessment | AttackPlan |
| Code patches | Attack surface analysis | Attack assignments |
| Historical findings | Agent selection | Parallel groups |
| Time budget | Priority ranking | Skip reasons |

**Stage 2: Analysis**

| Agent | Input | Processing | Output |
|-------|-------|------------|--------|
| ExploitAgent | Code + security context | OWASP vulnerability scan | Exploit findings with payloads |
| BreakAgent | Code + attack hints | Edge case probing | Logic bug findings with PoC |
| ChaosAgent | Code + infra context | Failure mode analysis | Chaos experiments |

**Stage 3: Arbitration**

| Input | Processing | Output |
|-------|------------|--------|
| All findings | Validation against context | Blocking issues |
| Codebase context | Exploitability assessment | Warnings |
| Security controls | Severity calibration | False positives |
| Historical data | Remediation planning | Remediation tasks |

---

## Event Sourcing with Beads

The bead system is the foundation of the framework's auditability and reproducibility. Every significant action produces an immutable record.

### Bead Structure

```python
@dataclass
class Bead:
    bead_id: str           # Unique identifier (B-YYYYMMDD-HHMMSS-NNNNNN)
    parent_bead_id: str    # Links to parent for chaining
    thread_id: str         # Workstream identifier
    task_id: str           # Task within thread
    timestamp_iso: str     # When this bead was created
    agent: str             # Which agent created this
    bead_type: BeadType    # Classification of bead
    payload: dict          # Agent-specific data
    artefacts: list        # External references (files, commits, PRs)
    idempotency_key: str   # For duplicate detection
    confidence: float      # Agent's confidence in output
    assumptions: list[str] # What was assumed
    unknowns: list[str]    # What couldn't be determined
```

### Bead Types

| Type | Producer | Purpose |
|------|----------|---------|
| `ATTACK_PLAN` | ChaosOrchestrator | Records attack planning decisions |
| `EXPLOIT_ANALYSIS` | ExploitAgent | Records security vulnerability findings |
| `BREAK_ANALYSIS` | BreakAgent | Records logic bug findings |
| `CHAOS_ANALYSIS` | ChaosAgent | Records resilience experiment designs |
| `ARBITER_VERDICT` | Arbiter | Records final verdict and remediation |

### Bead Relationships

Beads form a directed acyclic graph (DAG) through parent references:

```
ATTACK_PLAN (root)
    |
    +-- EXPLOIT_ANALYSIS (parent: ATTACK_PLAN)
    |
    +-- BREAK_ANALYSIS (parent: ATTACK_PLAN)
    |
    +-- CHAOS_ANALYSIS (parent: ATTACK_PLAN)
    |
    +-- ARBITER_VERDICT (parent: ATTACK_PLAN)
            |
            +-- (references all analysis beads in payload)
```

### Idempotency

Each bead has an `idempotency_key` that prevents duplicate processing. Before executing an action, agents can check if a bead with that key already exists:

```python
if bead_store.has_idempotency_key(key):
    # Skip - already processed
    return existing_result
```

The idempotency key format varies by agent but typically includes the thread_id, task_id, and relevant input identifiers.

---

## LLM Provider Abstraction

The framework abstracts LLM interactions through a provider interface, enabling support for multiple backends.

### Provider Interface

```python
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

### Available Providers

| Provider | Use Case | Configuration |
|----------|----------|---------------|
| **AnthropicProvider** | Production use | Requires `ANTHROPIC_API_KEY` |
| **MockProvider** | Testing/demos | No API key needed, deterministic output |

### Message Format

All LLM interactions use a consistent message format:

```python
@dataclass
class Message:
    role: str      # "system", "user", or "assistant"
    content: str   # The message content
```

Agents construct prompts by building a list of messages, typically starting with a system message that defines the agent's role and output format, followed by a user message with the specific task and code to analyze.

---

## Parallel Execution Strategy

The framework optimizes execution time by running independent analyses in parallel.

### Parallel Groups

The ChaosOrchestrator creates `ParallelGroup` objects that identify attacks that can run concurrently:

```python
@dataclass
class ParallelGroup:
    group_id: str                      # Unique group identifier
    attack_ids: list[str]              # Attacks in this group
    estimated_duration_seconds: int    # Expected runtime
    resource_requirements: dict        # CPU, memory needs
```

### Execution Batching

The `get_execution_batches` method on ChaosOrchestrator returns attacks grouped for parallel execution:

```
Batch 1: [ATK-001, ATK-002, ATK-003]  <- Run in parallel
    |
    v (wait for completion)
Batch 2: [ATK-004, ATK-005]           <- Depends on Batch 1
    |
    v (wait for completion)
Batch 3: [ATK-006]                    <- Depends on Batch 2
```

### Dependency Resolution

Attacks can declare dependencies on other attacks:

```python
@dataclass
class Attack:
    id: str
    depends_on: list[str]        # Must complete before this runs
    can_parallel_with: list[str] # Safe to run alongside these
```

The framework uses these declarations to build an optimal execution schedule that maximizes parallelism while respecting dependencies.

---

## Security Model

The framework includes multiple security measures to safely analyze potentially malicious code.

### Sandbox Execution

The `SandboxExecutor` provides isolated code execution for testing exploit payloads:

| Feature | Docker Backend | Subprocess Backend |
|---------|---------------|-------------------|
| Memory limit | Configurable | setrlimit |
| CPU limit | Configurable | setrlimit |
| Network | Disabled by default | N/A |
| Filesystem | Read-only root | Temp directory |
| Capabilities | Dropped | N/A |
| User | Unprivileged | Current user |

### Input Validation

All agent inputs are validated before processing:

- Identifier format checking (bead_id, thread_id, etc.)
- Path traversal prevention
- Size limits on inputs
- JSON serialization validation

### Defense in Depth

The framework employs multiple layers of security:

1. **Input validation** at API boundaries
2. **Sandbox isolation** for code execution
3. **Idempotency checks** to prevent replay attacks
4. **Audit logging** via bead ledger
5. **Least privilege** in sandbox execution

---

## Extension Points

The framework is designed for extensibility at several points:

### Adding New Agents

1. Create a new file in `src/adversarial_debate/agents/`
2. Extend the `Agent` base class
3. Implement required properties: `name`, `bead_type`, `model_tier`
4. Implement required methods: `_build_prompt()`, `_parse_response()`
5. Export in `agents/__init__.py`
6. Add tests in `tests/unit/test_agents/`

### Adding New Providers

1. Create a new file in `src/adversarial_debate/providers/`
2. Implement the `LLMProvider` interface
3. Add to `get_provider()` factory function
4. Add configuration support in `config.py`

### Adding New Bead Types

1. Add the new type to `BeadType` enum in `store/beads.py`
2. Document the payload schema
3. Update any queries that filter by bead type

---

## Next Steps

For more detailed information, see:

- [Agent System Documentation](agents.md) - Deep dive into each agent
- [Data Structures Reference](data-structures.md) - Complete type definitions
- [API Reference](api.md) - Python API documentation
- [Pipeline Execution Guide](pipeline.md) - Step-by-step walkthrough
