# Data Structures Reference

This document provides a comprehensive reference for all data structures used in the Adversarial Debate framework, including type definitions, field descriptions, and usage examples.

## Table of Contents

- [Attack Planning Types](#attack-planning-types)
- [Verdict Types](#verdict-types)
- [Event Sourcing Types](#event-sourcing-types)
- [Agent Types](#agent-types)
- [Provider Types](#provider-types)
- [Enumerations](#enumerations)

---

## Attack Planning Types

These types are defined in `src/adversarial_debate/attack_plan.py` and are used by the ChaosOrchestrator to coordinate red team agent activities.

### AttackPlan

The top-level structure representing a complete attack plan for a set of code changes.

```python
@dataclass
class AttackPlan:
    plan_id: str
    thread_id: str
    task_id: str
    risk_level: RiskLevel
    risk_factors: list[str]
    risk_score: int
    attacks: list[Attack]
    parallel_groups: list[ParallelGroup]
    execution_order: list[str]
    skipped: list[SkipReason]
    estimated_total_duration_seconds: int
    attack_surface_summary: str
    recommendations: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `plan_id` | `str` | Unique identifier (format: `PLAN-YYYYMMDD-HHMMSS`) |
| `thread_id` | `str` | Workstream identifier for traceability |
| `task_id` | `str` | Specific task within the thread |
| `risk_level` | `RiskLevel` | Overall risk assessment (LOW/MEDIUM/HIGH/CRITICAL) |
| `risk_factors` | `list[str]` | Human-readable risk factors identified |
| `risk_score` | `int` | Numeric risk score (0-100) |
| `attacks` | `list[Attack]` | Individual attack assignments |
| `parallel_groups` | `list[ParallelGroup]` | Groups of attacks that can run concurrently |
| `execution_order` | `list[str]` | Ordered list of attack IDs |
| `skipped` | `list[SkipReason]` | Items skipped with explanations |
| `estimated_total_duration_seconds` | `int` | Expected total runtime |
| `attack_surface_summary` | `str` | Human-readable summary of attack surface |
| `recommendations` | `list[str]` | Strategic recommendations |

**Key Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_attack_by_id(id)` | `Attack | None` | Find attack by ID |
| `get_attacks_by_agent(agent_type)` | `list[Attack]` | Get attacks for specific agent |
| `get_attacks_by_priority(priority)` | `list[Attack]` | Get attacks with specific priority |
| `get_ready_attacks(completed)` | `list[Attack]` | Get attacks whose dependencies are satisfied |
| `get_critical_path()` | `list[Attack]` | Get longest dependency chain |

---

### Attack

Represents a single attack assignment for a red team agent.

```python
@dataclass
class Attack:
    id: str
    agent: AgentType
    target_file: str
    target_function: str | None
    priority: AttackPriority
    attack_vectors: list[AttackVector]
    time_budget_seconds: int
    rationale: str
    depends_on: list[str]
    can_parallel_with: list[str]
    code_context: str | None
    hints: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique attack identifier (format: `ATK-NNN`) |
| `agent` | `AgentType` | Which agent should execute (EXPLOIT/BREAK/CHAOS) |
| `target_file` | `str` | File path to analyze |
| `target_function` | `str | None` | Specific function to focus on |
| `priority` | `AttackPriority` | Execution priority (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL) |
| `attack_vectors` | `list[AttackVector]` | Specific attack methods to try |
| `time_budget_seconds` | `int` | Maximum time for this attack |
| `rationale` | `str` | Why this attack was assigned |
| `depends_on` | `list[str]` | Attack IDs that must complete first |
| `can_parallel_with` | `list[str]` | Attack IDs safe to run alongside |
| `code_context` | `str | None` | Relevant code snippet |
| `hints` | `list[str]` | Hints for the executing agent |

---

### AttackVector

Describes a specific attack method within an Attack.

```python
@dataclass
class AttackVector:
    name: str
    description: str
    category: str
    payload_hints: list[str]
    expected_behavior: str
    success_indicators: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Attack vector name (e.g., "SQL Injection") |
| `description` | `str` | Detailed description of the attack |
| `category` | `str` | Category code (e.g., "A03:2021" for OWASP) |
| `payload_hints` | `list[str]` | Example payloads to try |
| `expected_behavior` | `str` | What should happen if vulnerable |
| `success_indicators` | `list[str]` | Signs that attack succeeded |

---

### ParallelGroup

Identifies attacks that can be executed concurrently.

```python
@dataclass
class ParallelGroup:
    group_id: str
    attack_ids: list[str]
    estimated_duration_seconds: int
    resource_requirements: dict[str, Any]
```

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | `str` | Unique group identifier (format: `PG-NNN`) |
| `attack_ids` | `list[str]` | IDs of attacks in this group |
| `estimated_duration_seconds` | `int` | Expected runtime (max of group) |
| `resource_requirements` | `dict` | CPU, memory, network needs |

---

### SkipReason

Documents why a potential target was not included in the attack plan.

```python
@dataclass
class SkipReason:
    target: str
    reason: str
    category: str
```

| Field | Type | Description |
|-------|------|-------------|
| `target` | `str` | File or function that was skipped |
| `reason` | `str` | Human-readable explanation |
| `category` | `str` | Category (e.g., "low_risk", "out_of_scope", "time_constraint") |

---

### FileRiskProfile

Per-file risk assessment used in attack surface analysis.

```python
@dataclass
class FileRiskProfile:
    file_path: str
    risk_score: int
    risk_factors: list[str]
    recommended_agents: list[AgentType]
    attack_vectors: list[str]
    exposure: str
    data_sensitivity: str
```

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `str` | Path to the file |
| `risk_score` | `int` | Risk score (0-100) |
| `risk_factors` | `list[str]` | Identified risk factors |
| `recommended_agents` | `list[AgentType]` | Agents that should analyze this file |
| `attack_vectors` | `list[str]` | Potential attack vectors |
| `exposure` | `str` | Exposure level (public/authenticated/internal) |
| `data_sensitivity` | `str` | Data sensitivity (high/medium/low) |

---

### AttackSurface

Aggregated attack surface analysis for all changed files.

```python
@dataclass
class AttackSurface:
    files: list[FileRiskProfile]
    total_risk_score: int
    highest_risk_file: str
    primary_concerns: list[str]
    recommended_focus_areas: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `files` | `list[FileRiskProfile]` | Risk profiles for each file |
| `total_risk_score` | `int` | Aggregate risk score |
| `highest_risk_file` | `str` | File with highest risk |
| `primary_concerns` | `list[str]` | Top security concerns |
| `recommended_focus_areas` | `list[str]` | Where to focus testing |

---

## Verdict Types

These types are defined in `src/adversarial_debate/verdict.py` and are used by the Arbiter to render verdicts and create remediation tasks.

### ArbiterVerdict

The complete verdict output from the Arbiter.

```python
@dataclass
class ArbiterVerdict:
    verdict_id: str
    thread_id: str
    task_id: str
    decision: VerdictDecision
    decision_rationale: str
    blocking_issues: list[ValidatedFinding]
    warnings: list[ValidatedFinding]
    passed_findings: list[ValidatedFinding]
    false_positives: list[RejectedFinding]
    remediation_tasks: list[RemediationTask]
    total_remediation_effort: str
    summary: str
    key_concerns: list[str]
    recommendations: list[str]
    findings_analyzed: int
    confidence: float
    assumptions: list[str]
    limitations: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `verdict_id` | `str` | Unique verdict identifier |
| `thread_id` | `str` | Workstream identifier |
| `task_id` | `str` | Task identifier |
| `decision` | `VerdictDecision` | BLOCK, WARN, or PASS |
| `decision_rationale` | `str` | Explanation of the decision |
| `blocking_issues` | `list[ValidatedFinding]` | Issues that must be fixed |
| `warnings` | `list[ValidatedFinding]` | Issues to track |
| `passed_findings` | `list[ValidatedFinding]` | Validated but acceptable |
| `false_positives` | `list[RejectedFinding]` | Rejected findings |
| `remediation_tasks` | `list[RemediationTask]` | Actionable fix tasks |
| `total_remediation_effort` | `str` | Estimated total fix time |
| `summary` | `str` | Executive summary |
| `key_concerns` | `list[str]` | Top concerns |
| `recommendations` | `list[str]` | Recommendations |
| `findings_analyzed` | `int` | Total findings reviewed |
| `confidence` | `float` | Confidence in verdict (0.0-1.0) |
| `assumptions` | `list[str]` | Assumptions made |
| `limitations` | `list[str]` | Known limitations |

**Key Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `should_block()` | `bool` | Whether verdict should block merge |
| `generate_summary_report()` | `str` | Human-readable summary report |

---

### ValidatedFinding

A finding that has been validated by the Arbiter.

```python
@dataclass
class ValidatedFinding:
    original_id: str
    original_agent: str
    original_title: str
    original_severity: str
    validation_status: FindingValidation
    validated_severity: str
    adjusted_severity_reason: str | None
    exploitation_difficulty: ExploitationDifficulty
    exploitation_prerequisites: list[str]
    real_world_exploitability: float
    impact_description: str
    affected_components: list[str]
    data_at_risk: list[str]
    remediation_effort: RemediationEffort
    suggested_fix: str
    fix_code_example: str | None
    workaround: str | None
    confidence: float
```

| Field | Type | Description |
|-------|------|-------------|
| `original_id` | `str` | ID from the original agent |
| `original_agent` | `str` | Which agent found this |
| `original_title` | `str` | Original finding title |
| `original_severity` | `str` | Original severity assessment |
| `validation_status` | `FindingValidation` | CONFIRMED, LIKELY, or UNCERTAIN |
| `validated_severity` | `str` | Arbiter's severity assessment |
| `adjusted_severity_reason` | `str | None` | Why severity was changed |
| `exploitation_difficulty` | `ExploitationDifficulty` | How hard to exploit |
| `exploitation_prerequisites` | `list[str]` | What attacker needs |
| `real_world_exploitability` | `float` | Likelihood of real exploit (0.0-1.0) |
| `impact_description` | `str` | What happens if exploited |
| `affected_components` | `list[str]` | Components affected |
| `data_at_risk` | `list[str]` | Data that could be compromised |
| `remediation_effort` | `RemediationEffort` | Time to fix |
| `suggested_fix` | `str` | How to fix |
| `fix_code_example` | `str | None` | Example fix code |
| `workaround` | `str | None` | Temporary mitigation |
| `confidence` | `float` | Confidence in validation (0.0-1.0) |

---

### RejectedFinding

A finding that was determined to be a false positive.

```python
@dataclass
class RejectedFinding:
    original_id: str
    original_agent: str
    original_title: str
    original_severity: str
    rejection_reason: str
    rejection_category: str
    evidence: str
    duplicate_of: str | None
```

| Field | Type | Description |
|-------|------|-------------|
| `original_id` | `str` | ID from the original agent |
| `original_agent` | `str` | Which agent found this |
| `original_title` | `str` | Original finding title |
| `original_severity` | `str` | Original severity |
| `rejection_reason` | `str` | Why it was rejected |
| `rejection_category` | `str` | Category of rejection |
| `evidence` | `str` | Evidence supporting rejection |
| `duplicate_of` | `str | None` | ID if duplicate of another finding |

**Rejection Categories:**

| Category | Description |
|----------|-------------|
| `NOT_EXPLOITABLE` | Cannot be exploited in practice |
| `FALSE_POSITIVE` | Incorrect detection |
| `OUT_OF_SCOPE` | Not relevant to this analysis |
| `DUPLICATE` | Same as another finding |
| `MITIGATED` | Already has sufficient mitigation |

---

### RemediationTask

An actionable task to fix a security issue.

```python
@dataclass
class RemediationTask:
    finding_id: str
    title: str
    description: str
    priority: str
    estimated_effort: RemediationEffort
    assigned_to: str | None
    deadline: str | None
    fix_guidance: str
    acceptance_criteria: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `finding_id` | `str` | Related finding ID |
| `title` | `str` | Task title |
| `description` | `str` | Detailed description |
| `priority` | `str` | Priority (CRITICAL/HIGH/MEDIUM/LOW) |
| `estimated_effort` | `RemediationEffort` | Time estimate |
| `assigned_to` | `str | None` | Assignee (if known) |
| `deadline` | `str | None` | Due date (if applicable) |
| `fix_guidance` | `str` | Step-by-step fix instructions |
| `acceptance_criteria` | `list[str]` | How to verify the fix |

---

## Event Sourcing Types

These types are defined in `src/adversarial_debate/store/beads.py` and implement the event sourcing system.

### Bead

The fundamental unit of the event sourcing system - an immutable record of an agent action.

```python
@dataclass
class Bead:
    bead_id: str
    parent_bead_id: str | None
    thread_id: str
    task_id: str
    timestamp_iso: str
    agent: str
    bead_type: BeadType
    payload: dict[str, Any]
    artefacts: list[Artefact]
    idempotency_key: str
    confidence: float
    assumptions: list[str]
    unknowns: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `bead_id` | `str` | Unique identifier (format: `B-YYYYMMDD-HHMMSS-NNNNNN`) |
| `parent_bead_id` | `str | None` | Parent bead for chaining |
| `thread_id` | `str` | Workstream identifier |
| `task_id` | `str` | Task within thread |
| `timestamp_iso` | `str` | ISO 8601 timestamp |
| `agent` | `str` | Agent that created this bead |
| `bead_type` | `BeadType` | Classification of bead |
| `payload` | `dict` | Agent-specific data |
| `artefacts` | `list[Artefact]` | External references |
| `idempotency_key` | `str` | For duplicate detection |
| `confidence` | `float` | Agent's confidence (0.0-1.0) |
| `assumptions` | `list[str]` | Assumptions made |
| `unknowns` | `list[str]` | Things that couldn't be determined |

**Key Methods:**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `to_json()` | `str` | Serialize to JSON string |
| `from_json(json_str)` | `Bead` | Deserialize from JSON (class method) |
| `to_dict()` | `dict` | Convert to dictionary |
| `from_dict(data)` | `Bead` | Create from dictionary (class method) |

---

### Artefact

Reference to an external resource associated with a bead.

```python
@dataclass
class Artefact:
    type: ArtefactType
    ref: str
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | `ArtefactType` | Type of artefact |
| `ref` | `str` | Reference string (path, URL, hash, etc.) |

---

### BeadStore

Manages the append-only bead ledger.

```python
class BeadStore:
    def __init__(self, ledger_path: str | Path = "beads/ledger.jsonl"):
        ...
```

**Key Methods:**

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `append(bead)` | `Bead` | `None` | Thread-safe append single bead |
| `append_many(beads)` | `list[Bead]` | `None` | Atomic append multiple beads |
| `iter_all()` | - | `Iterator[Bead]` | Iterate over all beads |
| `query(...)` | filters | `list[Bead]` | Query with filters |
| `has_idempotency_key(key)` | `str` | `bool` | Check if key exists |
| `get_by_id(bead_id)` | `str` | `Bead | None` | Get bead by ID |
| `get_children(parent_id)` | `str` | `list[Bead]` | Get beads with parent |
| `generate_bead_id()` | - | `str` | Generate unique bead ID |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `thread_id` | `str | None` | Filter by thread |
| `task_id` | `str | None` | Filter by task |
| `bead_type` | `BeadType | None` | Filter by type |
| `agent` | `str | None` | Filter by agent |
| `idempotency_key` | `str | None` | Filter by idempotency key |
| `since` | `str | None` | Filter by timestamp (ISO) |
| `limit` | `int | None` | Maximum results |

---

## Agent Types

These types are defined in `src/adversarial_debate/agents/base.py` and are used by all agents.

### AgentContext

Input context provided to agents.

```python
@dataclass
class AgentContext:
    run_id: str
    timestamp_iso: str
    policy: dict[str, Any]
    thread_id: str
    task_id: str
    parent_bead_id: str = ""
    recent_beads: list[Bead] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    repo_files: dict[str, str] = field(default_factory=dict)
```

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Unique run identifier |
| `timestamp_iso` | `str` | ISO timestamp for ordering |
| `policy` | `dict` | Security policies to enforce |
| `thread_id` | `str` | Workstream identifier |
| `task_id` | `str` | Task within thread |
| `parent_bead_id` | `str` | Parent bead for chaining |
| `recent_beads` | `list[Bead]` | Recent context beads |
| `inputs` | `dict` | Task-specific inputs |
| `repo_files` | `dict[str, str]` | File path to content mapping |

---

### AgentOutput

Standardized output from all agents.

```python
@dataclass
class AgentOutput:
    agent_name: str
    result: dict[str, Any]
    beads_out: list[Bead]
    confidence: float
    assumptions: list[str]
    unknowns: list[str]
    errors: list[str]
```

| Field | Type | Description |
|-------|------|-------------|
| `agent_name` | `str` | Name of the agent |
| `result` | `dict` | Agent-specific result data |
| `beads_out` | `list[Bead]` | Beads to append to ledger |
| `confidence` | `float` | Confidence score (0.0-1.0) |
| `assumptions` | `list[str]` | Assumptions made |
| `unknowns` | `list[str]` | Things that couldn't be determined |
| `errors` | `list[str]` | Errors encountered |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `success` | `bool` | True if no errors |

---

## Provider Types

These types are defined in `src/adversarial_debate/providers/base.py` and abstract LLM interactions.

### Message

A message in an LLM conversation.

```python
@dataclass
class Message:
    role: str
    content: str
```

| Field | Type | Description |
|-------|------|-------------|
| `role` | `str` | Message role: "system", "user", or "assistant" |
| `content` | `str` | Message content |

---

### ProviderConfig

Configuration for an LLM provider.

```python
@dataclass
class ProviderConfig:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 120.0
    extra: dict[str, Any] = field(default_factory=dict)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | `str | None` | `None` | API key for authentication |
| `base_url` | `str | None` | `None` | Custom API base URL |
| `model` | `str | None` | `None` | Model name override |
| `temperature` | `float` | `0.7` | Sampling temperature |
| `max_tokens` | `int` | `4096` | Maximum output tokens |
| `timeout` | `float` | `120.0` | Request timeout in seconds |
| `extra` | `dict` | `{}` | Provider-specific options |

---

### LLMResponse

Response from an LLM provider.

```python
@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str | None = None
    raw_response: Any = None
```

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Generated text content |
| `model` | `str` | Model that generated response |
| `usage` | `dict[str, int]` | Token usage (input_tokens, output_tokens) |
| `finish_reason` | `str | None` | Why generation stopped |
| `raw_response` | `Any` | Raw provider response |

---

## Enumerations

### AgentType

```python
class AgentType(str, Enum):
    BREAK_AGENT = "BREAK_AGENT"
    EXPLOIT_AGENT = "EXPLOIT_AGENT"
    CHAOS_AGENT = "CHAOS_AGENT"
```

### AttackPriority

```python
class AttackPriority(int, Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    MINIMAL = 5
```

### RiskLevel

```python
class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

### VerdictDecision

```python
class VerdictDecision(str, Enum):
    BLOCK = "BLOCK"    # Must fix before merge
    WARN = "WARN"      # Track, fix in follow-up
    PASS = "PASS"      # Approved to merge
```

### ExploitationDifficulty

```python
class ExploitationDifficulty(str, Enum):
    TRIVIAL = "TRIVIAL"        # Script kiddie level
    EASY = "EASY"              # Basic skills needed
    MODERATE = "MODERATE"      # Intermediate skills
    DIFFICULT = "DIFFICULT"    # Expert skills needed
    THEORETICAL = "THEORETICAL" # Requires ideal conditions
```

### RemediationEffort

```python
class RemediationEffort(str, Enum):
    MINUTES = "MINUTES"  # < 30 minutes
    HOURS = "HOURS"      # 30 min - 8 hours
    DAYS = "DAYS"        # 1-5 days
    WEEKS = "WEEKS"      # > 1 week
```

### FindingValidation

```python
class FindingValidation(str, Enum):
    CONFIRMED = "CONFIRMED"    # Definitely exploitable
    LIKELY = "LIKELY"          # Probably exploitable
    UNCERTAIN = "UNCERTAIN"    # Needs more investigation
```

### BeadType

```python
class BeadType(str, Enum):
    ATTACK_PLAN = "ATTACK_PLAN"
    BREAK_ANALYSIS = "BREAK_ANALYSIS"
    EXPLOIT_ANALYSIS = "EXPLOIT_ANALYSIS"
    CHAOS_ANALYSIS = "CHAOS_ANALYSIS"
    ARBITER_VERDICT = "ARBITER_VERDICT"
    PROPOSAL = "PROPOSAL"
    CRITIQUE = "CRITIQUE"
    DECISION = "DECISION"
```

### ArtefactType

```python
class ArtefactType(str, Enum):
    FILE = "FILE"
    COMMIT = "COMMIT"
    PR = "PR"
    URL = "URL"
    LOG = "LOG"
```

### ModelTier

```python
class ModelTier(str, Enum):
    LOCAL_SMALL = "local_small"    # Fast, cheap
    HOSTED_SMALL = "hosted_small"  # Balanced
    HOSTED_LARGE = "hosted_large"  # Most capable
```

---

## Type Relationships

The following diagram shows how the main types relate to each other:

```
                    AttackPlan
                        |
        +---------------+---------------+
        |               |               |
    Attack          ParallelGroup   SkipReason
        |
    AttackVector
        
        
                  ArbiterVerdict
                        |
    +-------------------+-------------------+
    |                   |                   |
ValidatedFinding  RejectedFinding  RemediationTask


                    BeadStore
                        |
                      Bead
                        |
                    Artefact


                AgentContext
                    |
                  Agent
                    |
                AgentOutput
                    |
                  Bead
```

---

## Next Steps

For more information, see:

- [Architecture Deep Dive](architecture.md) - System overview
- [Agent System Documentation](agents.md) - Deep dive into each agent
- [Pipeline Execution Guide](pipeline.md) - Step-by-step walkthrough
- [API Reference](api.md) - Python API documentation
