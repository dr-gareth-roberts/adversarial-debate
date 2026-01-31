# Data Structures Reference

Complete reference for all types, enums, and data structures in Adversarial Debate.

## Overview

The framework uses strongly-typed dataclasses and enums throughout:

| Module | Purpose |
|--------|---------|
| `adversarial_debate.store.beads` | Event sourcing types |
| `adversarial_debate.attack_plan` | Attack coordination types |
| `adversarial_debate.verdict` | Verdict and finding types |
| `adversarial_debate.agents` | Agent context and output |
| `adversarial_debate.providers` | LLM provider types |

---

## Bead Types

### BeadType (Enum)

Types of beads in the event sourcing system.

```python
from adversarial_debate.store.beads import BeadType

class BeadType(str, Enum):
    # General coordination
    BOARD_HEALTH = "board_health"
    PROPOSAL = "proposal"
    CRITIQUE = "critique"
    DECISION = "decision"
    PLAN = "plan"
    TASK = "task"
    PATCH = "patch"
    REVIEW = "review"
    INTEGRATION = "integration"
    POSTHOOK = "posthook"
    REFLECTION = "reflection"

    # Adversarial analysis
    ATTACK_PLAN = "attack_plan"
    BREAK_ANALYSIS = "break_analysis"
    EXPLOIT_ANALYSIS = "exploit_analysis"
    CRYPTO_ANALYSIS = "crypto_analysis"
    CHAOS_ANALYSIS = "chaos_analysis"
    ARBITER_VERDICT = "arbiter_verdict"
    CROSS_EXAMINATION = "cross_examination"
```

### ArtefactType (Enum)

Types of artefacts referenced by beads.

```python
from adversarial_debate.store.beads import ArtefactType

class ArtefactType(str, Enum):
    TRELLO_CARD = "trello_card"
    FILE = "file"
    COMMIT = "commit"
    PR = "pr"
    EVAL = "eval"
    PATCH_BUNDLE = "patch_bundle"
    OTHER = "other"
```

### Artefact (Dataclass)

Reference to an artefact produced or consumed by a bead.

```python
from adversarial_debate.store.beads import Artefact, ArtefactType

@dataclass
class Artefact:
    type: ArtefactType    # Type of artefact
    ref: str              # Reference (path, URL, ID, etc.)

    def to_dict(self) -> dict[str, str]
    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Artefact"

# Example
artefact = Artefact(
    type=ArtefactType.FILE,
    ref="src/api/users.py",
)
```

### Bead (Dataclass)

The atomic unit of the event sourcing system.

```python
from adversarial_debate.store.beads import Bead, BeadType

@dataclass
class Bead:
    bead_id: str              # Unique identifier (min 3 chars)
    parent_bead_id: str       # Parent bead or "root"
    thread_id: str            # Analysis run identifier (min 3 chars)
    task_id: str              # Task identifier
    timestamp_iso: str        # ISO 8601 timestamp
    agent: str                # Agent that created the bead
    bead_type: BeadType       # Type of bead
    payload: dict[str, Any]   # Agent-specific data
    artefacts: list[Artefact] # Referenced artefacts
    idempotency_key: str      # Deduplication key (min 3 chars)
    confidence: float         # Confidence 0.0-1.0
    assumptions: list[str] = []  # Assumptions made
    unknowns: list[str] = []     # Unknown factors

    def to_dict(self) -> dict[str, Any]
    def to_json(self) -> str
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Bead"
    @classmethod
    def from_json(cls, line: str) -> "Bead"

# Example
bead = Bead(
    bead_id="B-20240115-143022-123456",
    parent_bead_id="root",
    thread_id="run-20240115-143022",
    task_id="analyse-users-py",
    timestamp_iso="2024-01-15T14:30:22.123456Z",
    agent="ExploitAgent",
    bead_type=BeadType.EXPLOIT_ANALYSIS,
    payload={"findings": [...]},
    artefacts=[],
    idempotency_key="exploit-users-py-v1",
    confidence=0.92,
)
```

### BeadStore (Class)

Append-only JSONL store for beads.

```python
from adversarial_debate.store.beads import BeadStore

class BeadStore:
    def __init__(self, ledger_path: str | Path | None = None)

    # Append operations
    def append(self, bead: Bead) -> None
    def append_idempotent(self, bead: Bead) -> None  # Raises DuplicateBeadError
    def append_many(self, beads: list[Bead]) -> None

    # Query operations
    def iter_all(self) -> Iterator[Bead]
    def get_all(self) -> list[Bead]
    def get_by_id(self, bead_id: str) -> Bead | None
    def get_bead(self, bead_id: str) -> Bead | None  # Alias
    def get_children(self, parent_bead_id: str) -> list[Bead]
    def query(
        self,
        *,
        thread_id: str | None = None,
        task_id: str | None = None,
        bead_type: BeadType | None = None,
        agent: str | None = None,
        idempotency_key: str | None = None,
        limit: int | None = None,
    ) -> list[Bead]
    def search(self, query: str, *, limit: int | None = None) -> list[Bead]

    # Utility
    def has_idempotency_key(self, key: str) -> bool
    def count(self) -> int

    # Static methods
    @staticmethod
    def generate_bead_id(prefix: str = "B") -> str
    @staticmethod
    def now_iso() -> str
```

---

## Attack Plan Types

### AgentType (Enum)

Types of red team agents.

```python
from adversarial_debate.attack_plan import AgentType

class AgentType(str, Enum):
    BREAK_AGENT = "BreakAgent"
    EXPLOIT_AGENT = "ExploitAgent"
    CHAOS_AGENT = "ChaosAgent"
    CRYPTO_AGENT = "CryptoAgent"
```

### AttackPriority (Enum)

Priority levels for attack assignments. Lower values = higher priority.

```python
from adversarial_debate.attack_plan import AttackPriority

class AttackPriority(int, Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    MINIMAL = 5
```

### RiskLevel (Enum)

Overall risk level assessment.

```python
from adversarial_debate.attack_plan import RiskLevel

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

### AttackVector (Dataclass)

A specific attack vector to test.

```python
from adversarial_debate.attack_plan import AttackVector

@dataclass
class AttackVector:
    name: str                          # Vector name
    description: str                   # What to test
    category: str                      # injection, auth, crypto, etc.
    payload_hints: list[str] = []      # Suggested payloads
    expected_behavior: str = ""        # What should happen
    success_indicators: list[str] = [] # Signs of vulnerability

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackVector"

# Example
vector = AttackVector(
    name="SQL Injection",
    description="Test user_id for SQL injection",
    category="injection",
    payload_hints=["' OR '1'='1", "'; DROP TABLE--"],
    expected_behavior="Query should be parameterised",
    success_indicators=["returns all rows"],
)
```

### Attack (Dataclass)

A single attack assignment for a red team agent.

```python
from adversarial_debate.attack_plan import Attack, AgentType, AttackPriority

@dataclass
class Attack:
    id: str                              # Attack identifier
    agent: AgentType                     # Assigned agent
    target_file: str                     # File to analyse
    target_function: str | None          # Specific function
    priority: AttackPriority             # Priority level
    attack_vectors: list[AttackVector]   # Vectors to test
    time_budget_seconds: int             # Time budget
    rationale: str                       # Why this attack
    depends_on: list[str] = []           # Dependency IDs
    can_parallel_with: list[str] = []    # Parallel IDs
    code_context: dict[str, Any] = {}    # Additional context
    hints: list[str] = []                # Analysis hints

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attack"
```

### ParallelGroup (Dataclass)

A group of attacks that can run in parallel.

```python
from adversarial_debate.attack_plan import ParallelGroup

@dataclass
class ParallelGroup:
    group_id: str                            # Group identifier
    attack_ids: list[str]                    # Attack IDs in group
    estimated_duration_seconds: int          # Estimated duration
    resource_requirements: dict[str, Any] = {}  # Resource needs

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParallelGroup"
```

### SkipReason (Dataclass)

Why a potential target was skipped.

```python
from adversarial_debate.attack_plan import SkipReason

@dataclass
class SkipReason:
    target: str       # Skipped target
    reason: str       # Why skipped
    category: str     # low_risk, out_of_scope, already_covered

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkipReason"
```

### FileRiskProfile (Dataclass)

Risk assessment for a single file.

```python
from adversarial_debate.attack_plan import FileRiskProfile, AgentType

@dataclass
class FileRiskProfile:
    file_path: str                       # Path to file
    risk_score: int                      # 0-100
    risk_factors: list[str]              # Why risky
    recommended_agents: list[AgentType]  # Which agents
    attack_vectors: list[str]            # Suggested vectors
    exposure: str                        # public, authenticated, internal
    data_sensitivity: str                # high, medium, low

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileRiskProfile"
```

### AttackSurface (Dataclass)

Analysis of the attack surface.

```python
from adversarial_debate.attack_plan import AttackSurface

@dataclass
class AttackSurface:
    files: list[FileRiskProfile]         # File profiles
    total_risk_score: int                # 0-100
    highest_risk_file: str | None        # Most risky file
    primary_concerns: list[str]          # Main concerns
    recommended_focus_areas: list[str]   # Where to focus

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackSurface"
```

### AttackPlan (Dataclass)

Complete attack plan from ChaosOrchestrator.

```python
from adversarial_debate.attack_plan import AttackPlan, RiskLevel

@dataclass
class AttackPlan:
    plan_id: str                              # Plan identifier
    thread_id: str                            # Bead thread ID
    task_id: str                              # Task identifier
    risk_level: RiskLevel                     # Overall risk
    risk_factors: list[str]                   # Risk factors
    risk_score: int                           # 0-100
    attacks: list[Attack]                     # All attacks
    parallel_groups: list[ParallelGroup]      # Parallelisation
    execution_order: list[str]                # Attack ID order
    skipped: list[SkipReason]                 # Skipped targets
    estimated_total_duration_seconds: int     # Time estimate
    attack_surface_summary: str               # Summary
    recommendations: list[str] = []           # Recommendations

    # Methods
    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttackPlan"
    def get_attack_by_id(self, attack_id: str) -> Attack | None
    def get_attacks_by_agent(self, agent_type: AgentType) -> list[Attack]
    def get_attacks_by_priority(self, priority: AttackPriority) -> list[Attack]
    def get_ready_attacks(self, completed: set[str]) -> list[Attack]
    def get_critical_path(self) -> list[Attack]
```

---

## Verdict Types

### VerdictDecision (Enum)

Final verdict decision.

```python
from adversarial_debate.verdict import VerdictDecision

class VerdictDecision(str, Enum):
    BLOCK = "BLOCK"  # Critical issues, must fix
    WARN = "WARN"    # Issues to track
    PASS = "PASS"    # No actionable issues
```

### ExploitationDifficulty (Enum)

How difficult to exploit a vulnerability.

```python
from adversarial_debate.verdict import ExploitationDifficulty

class ExploitationDifficulty(str, Enum):
    TRIVIAL = "TRIVIAL"      # Script kiddie level
    EASY = "EASY"            # Straightforward
    MODERATE = "MODERATE"    # Requires effort
    DIFFICULT = "DIFFICULT"  # Expert knowledge
    THEORETICAL = "THEORETICAL"  # Impractical
```

### RemediationEffort (Enum)

Estimated time to remediate.

```python
from adversarial_debate.verdict import RemediationEffort

class RemediationEffort(str, Enum):
    MINUTES = "MINUTES"  # < 1 hour
    HOURS = "HOURS"      # Same day
    DAYS = "DAYS"        # Multi-day
    WEEKS = "WEEKS"      # Significant refactor
```

### FindingValidation (Enum)

Validation status of a finding.

```python
from adversarial_debate.verdict import FindingValidation

class FindingValidation(str, Enum):
    CONFIRMED = "CONFIRMED"  # Definitely real
    LIKELY = "LIKELY"        # Probably real
    UNCERTAIN = "UNCERTAIN"  # Needs investigation
```

### ValidatedFinding (Dataclass)

A finding validated by the Arbiter.

```python
from adversarial_debate.verdict import ValidatedFinding

@dataclass
class ValidatedFinding:
    original_id: str                     # Original finding ID
    original_agent: str                  # Source agent
    original_title: str                  # Original title
    original_severity: str               # Original severity
    validation_status: FindingValidation # Validation result
    validated_severity: str              # Adjusted severity
    adjusted_severity_reason: str        # Why adjusted
    exploitation_difficulty: ExploitationDifficulty
    exploitation_prerequisites: list[str]
    real_world_exploitability: float     # 0.0-1.0
    impact_description: str
    affected_components: list[str]
    data_at_risk: list[str]
    remediation_effort: RemediationEffort
    suggested_fix: str
    fix_code_example: str
    workaround: str
    confidence: float                    # 0.0-1.0

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidatedFinding"
```

### RejectedFinding (Dataclass)

A finding rejected as false positive.

```python
from adversarial_debate.verdict import RejectedFinding

@dataclass
class RejectedFinding:
    original_id: str           # Original finding ID
    original_agent: str        # Source agent
    original_title: str        # Original title
    original_severity: str     # Original severity
    rejection_reason: str      # Why rejected
    rejection_category: str    # not_exploitable, false_positive, etc.
    evidence: str              # Supporting evidence
    duplicate_of: str = ""     # If duplicate

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RejectedFinding"
```

### RemediationTask (Dataclass)

A task to remediate a finding.

```python
from adversarial_debate.verdict import RemediationTask

@dataclass
class RemediationTask:
    finding_id: str                     # Related finding
    title: str                          # Task title
    description: str                    # Task description
    priority: str                       # CRITICAL, HIGH, MEDIUM, LOW
    estimated_effort: RemediationEffort # Time estimate
    assigned_to: str                    # Assignee
    deadline: str                       # Due date
    fix_guidance: str                   # How to fix
    acceptance_criteria: list[str]      # Done criteria

    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RemediationTask"
```

### ArbiterVerdict (Dataclass)

Complete verdict from the Arbiter.

```python
from adversarial_debate.verdict import ArbiterVerdict

@dataclass
class ArbiterVerdict:
    verdict_id: str                         # Verdict identifier
    thread_id: str                          # Bead thread ID
    task_id: str                            # Task identifier
    decision: VerdictDecision               # BLOCK, WARN, PASS
    decision_rationale: str                 # Why this decision
    blocking_issues: list[ValidatedFinding] # Must fix
    warnings: list[ValidatedFinding]        # Should fix
    passed_findings: list[ValidatedFinding] # No action needed
    false_positives: list[RejectedFinding]  # Rejected
    remediation_tasks: list[RemediationTask]
    total_remediation_effort: RemediationEffort
    summary: str
    key_concerns: list[str]
    recommendations: list[str]
    findings_analyzed: int
    confidence: float                       # 0.0-1.0
    assumptions: list[str] = []
    limitations: list[str] = []

    # Methods
    def should_block(self) -> bool
    def to_dict(self) -> dict[str, Any]
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArbiterVerdict"
    def generate_summary_report(self) -> str
```

---

## Agent Types

### AgentContext (Dataclass)

Context passed to an agent for execution.

```python
from adversarial_debate.agents import AgentContext

@dataclass
class AgentContext:
    run_id: str                            # Run identifier
    timestamp_iso: str                     # ISO timestamp
    policy: dict[str, Any]                 # Policy constraints
    thread_id: str                         # Bead thread ID
    task_id: str = ""                      # Task identifier
    parent_bead_id: str = ""               # Parent bead
    recent_beads: list[Bead] = []          # Recent context
    inputs: dict[str, Any] = {}            # Agent inputs
    repo_files: dict[str, str] = {}        # File contents

    def to_dict(self) -> dict[str, Any]

# Example
context = AgentContext(
    run_id="run-20240115-143022",
    timestamp_iso="2024-01-15T14:30:22Z",
    policy={"max_findings": 50},
    thread_id="thread-001",
    task_id="analyse-users",
    inputs={
        "code": "def get_user(id): ...",
        "file_path": "src/api/users.py",
        "language": "python",
    },
)
```

### AgentOutput (Dataclass)

Output from agent execution.

```python
from adversarial_debate.agents import AgentOutput

@dataclass
class AgentOutput:
    agent_name: str            # Agent identifier
    result: dict[str, Any]     # Agent-specific output
    beads_out: list[Bead]      # Beads to emit
    confidence: float          # 0.0-1.0
    assumptions: list[str] = []
    unknowns: list[str] = []
    errors: list[str] = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0
```

---

## Provider Types

### ModelTier (Enum)

Model performance tiers.

```python
from adversarial_debate.providers import ModelTier

class ModelTier(str, Enum):
    HOSTED_SMALL = "hosted_small"   # Fast, cheap
    HOSTED_LARGE = "hosted_large"   # Powerful, expensive
    LOCAL = "local"                 # Self-hosted
```

### Message (Dataclass)

Chat message for LLM.

```python
from adversarial_debate.providers import Message

@dataclass
class Message:
    role: str      # "system", "user", "assistant"
    content: str   # Message content

# Example
messages = [
    Message(role="system", content="You are a security expert."),
    Message(role="user", content="Analyse this code: ..."),
]
```

### LLMResponse (Dataclass)

Response from LLM completion.

```python
from adversarial_debate.providers import LLMResponse

@dataclass
class LLMResponse:
    content: str                  # Response text
    model: str                    # Model used
    usage: dict[str, int]         # Token usage
    raw_response: Any = None      # Original response

# Example usage
{
    "input_tokens": 1500,
    "output_tokens": 500,
}
```

---

## Results Bundle

The canonical output format for analysis results.

```python
bundle = {
    "metadata": {
        "run_id": "run-20240115-143022",
        "target": "src/",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "started_at": "2024-01-15T14:30:22Z",
        "finished_at": "2024-01-15T14:32:45Z",
        "files_analysed": ["src/api/users.py"],
        "version": "0.1.0",
    },
    "summary": {
        "verdict": "WARN",  # BLOCK, WARN, PASS
        "total_findings": 5,
        "by_severity": {
            "CRITICAL": 1,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
        },
        "should_block": False,
    },
    "findings": [
        {
            "finding_id": "EXP-001",
            "agent": "ExploitAgent",
            "title": "SQL Injection",
            "severity": "CRITICAL",
            "owasp_category": "A03:2021",
            "cwe_id": "CWE-89",
            "confidence": 0.95,
            "description": "...",
            "location": {
                "file": "src/api/users.py",
                "line": 42,
                "function": "get_user",
            },
            "evidence": "cursor.execute('SELECT ... ' + user_id)",
            "remediation": "Use parameterised queries",
            "proof_of_concept": "' OR '1'='1",
        }
    ],
    "verdict": {
        "decision": "WARN",
        "rationale": "...",
        "blocking_issues": [],
        "warnings": [...],
    },
    "attack_plan": {
        "risk_level": "HIGH",
        "attacks": [...],
    },
}
```

## See Also

- [Agent Reference](agents.md) — Agent behaviour
- [Event Sourcing](../developers/event-sourcing.md) — Bead system
- [Output Formats](../guides/output-formats.md) — Bundle format
