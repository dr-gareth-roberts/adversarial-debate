# Event Sourcing with Beads

The Bead system provides an append-only audit trail for all agent activities, enabling reproducibility, debugging, and compliance.

## Overview

Every significant action in Adversarial Debate is recorded as a **Bead**—an immutable event in a JSONL ledger. This event-sourcing pattern provides:

- **Complete audit trail** — Every agent decision is recorded
- **Reproducibility** — Replay analysis from stored beads
- **Idempotency** — Prevent duplicate operations on retry
- **Debugging** — Trace exactly what happened and why
- **Compliance** — Evidence for security audits

## Core Concepts

### What is a Bead?

A bead is the atomic unit of the system—representing a single agent action or decision:

```
┌─────────────────────────────────────────────────────────────┐
│                           Bead                              │
├─────────────────────────────────────────────────────────────┤
│ bead_id:         B-20240115-143022-123456                   │
│ parent_bead_id:  B-20240115-143020-000001                   │
│ thread_id:       run-20240115-143022                        │
│ task_id:         analyse-src-api                            │
│ timestamp_iso:   2024-01-15T14:30:22.123456Z                │
│ agent:           ExploitAgent                               │
│ bead_type:       exploit_analysis                           │
│ confidence:      0.85                                       │
│ payload:         { ... agent-specific data ... }            │
│ artefacts:       [{ type: "file", ref: "src/api/users.py" }]│
│ idempotency_key: exploit-src-api-users-v1                   │
│ assumptions:     ["User input not sanitised"]               │
│ unknowns:        ["Runtime configuration"]                  │
└─────────────────────────────────────────────────────────────┘
```

### Bead Types

The system defines specific bead types for different activities:

```python
from adversarial_debate.store.beads import BeadType

# General coordination types
BeadType.PLAN          # Attack plan from orchestrator
BeadType.TASK          # Individual analysis task
BeadType.DECISION      # Final verdict decision

# Agent analysis types
BeadType.ATTACK_PLAN       # ChaosOrchestrator's attack strategy
BeadType.EXPLOIT_ANALYSIS  # ExploitAgent findings
BeadType.BREAK_ANALYSIS    # BreakAgent findings
BeadType.CHAOS_ANALYSIS    # ChaosAgent findings
BeadType.CRYPTO_ANALYSIS   # CryptoAgent findings

# Verdict types
BeadType.CROSS_EXAMINATION # CrossExaminationAgent review
BeadType.ARBITER_VERDICT   # Arbiter's final decision
```

### The Ledger

Beads are stored in an append-only JSONL file:

```
beads/
└── ledger.jsonl    # One JSON object per line
```

Each line is a complete bead:

```json
{"bead_id":"B-20240115-143022-123456","parent_bead_id":"root","thread_id":"run-001","task_id":"analyse","timestamp_iso":"2024-01-15T14:30:22Z","agent":"ExploitAgent","bead_type":"exploit_analysis","payload":{"findings":[...]},"artefacts":[],"idempotency_key":"exp-001","confidence":0.9,"assumptions":[],"unknowns":[]}
```

## Using the Bead Store

### Basic Operations

```python
from adversarial_debate.store.beads import BeadStore, Bead, BeadType, Artefact, ArtefactType

# Initialise store (auto-discovers ledger.jsonl)
store = BeadStore()

# Or specify explicit path
store = BeadStore("./my-analysis/beads/ledger.jsonl")
```

### Creating Beads

```python
# Create a bead
bead = Bead(
    bead_id=BeadStore.generate_bead_id(),
    parent_bead_id="root",  # Or ID of parent bead
    thread_id="run-20240115-143022",
    task_id="analyse-users-py",
    timestamp_iso=BeadStore.now_iso(),
    agent="ExploitAgent",
    bead_type=BeadType.EXPLOIT_ANALYSIS,
    payload={
        "target": "src/api/users.py",
        "findings": [
            {
                "title": "SQL Injection",
                "severity": "CRITICAL",
                "line": 42,
            }
        ],
    },
    artefacts=[
        Artefact(type=ArtefactType.FILE, ref="src/api/users.py"),
    ],
    idempotency_key="exploit-users-py-v1",
    confidence=0.92,
    assumptions=["Database queries use string concatenation"],
    unknowns=["ORM configuration"],
)

# Append to ledger
store.append(bead)
```

### Idempotent Operations

For operations that may be retried, use idempotent append:

```python
from adversarial_debate.exceptions import DuplicateBeadError

try:
    store.append_idempotent(bead)
except DuplicateBeadError:
    # Bead already exists, skip
    print(f"Already processed: {bead.idempotency_key}")
```

Check before executing:

```python
# Check if operation already done
if store.has_idempotency_key("exploit-users-py-v1"):
    print("Already analysed, skipping")
else:
    # Perform analysis...
    store.append(bead)
```

### Querying Beads

```python
# Get all beads
all_beads = store.get_all()

# Query with filters
findings = store.query(
    thread_id="run-20240115-143022",
    bead_type=BeadType.EXPLOIT_ANALYSIS,
    agent="ExploitAgent",
    limit=10,  # Most recent 10
)

# Get specific bead
bead = store.get_by_id("B-20240115-143022-123456")

# Get child beads
children = store.get_children("B-20240115-143022-123456")

# Full-text search
matches = store.search("SQL Injection", limit=5)
```

### Batch Operations

```python
# Append multiple beads atomically
beads = [bead1, bead2, bead3]
store.append_many(beads)
```

### Iteration

```python
# Memory-efficient iteration
for bead in store.iter_all():
    if bead.bead_type == BeadType.EXPLOIT_ANALYSIS:
        process_finding(bead)
```

## Bead Structure

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `bead_id` | str | Unique identifier (min 3 chars) |
| `parent_bead_id` | str | Parent bead or "root" |
| `thread_id` | str | Analysis run identifier (min 3 chars) |
| `task_id` | str | Specific task identifier |
| `timestamp_iso` | str | ISO 8601 timestamp |
| `agent` | str | Agent that created the bead |
| `bead_type` | BeadType | Type of bead |
| `payload` | dict | Agent-specific data |
| `artefacts` | list[Artefact] | Referenced files, commits, etc. |
| `idempotency_key` | str | Unique key for deduplication (min 3 chars) |
| `confidence` | float | Confidence score 0.0-1.0 |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `assumptions` | list[str] | Assumptions made during analysis |
| `unknowns` | list[str] | Unknown factors that may affect results |

### Artefact Types

```python
from adversarial_debate.store.beads import ArtefactType

ArtefactType.FILE         # Source file reference
ArtefactType.COMMIT       # Git commit
ArtefactType.PR           # Pull request
ArtefactType.EVAL         # Evaluation result
ArtefactType.PATCH_BUNDLE # Collection of patches
ArtefactType.OTHER        # Custom artefact type
```

## Bead Chains

Beads form chains through parent references:

```
root
  └── B-001 (ATTACK_PLAN)
        ├── B-002 (EXPLOIT_ANALYSIS)
        │     └── B-005 (CROSS_EXAMINATION)
        ├── B-003 (BREAK_ANALYSIS)
        │     └── B-006 (CROSS_EXAMINATION)
        └── B-004 (CHAOS_ANALYSIS)
              └── B-007 (CROSS_EXAMINATION)
                    └── B-008 (ARBITER_VERDICT)
```

Traverse the chain:

```python
def get_chain(store: BeadStore, bead_id: str) -> list[Bead]:
    """Get all ancestors of a bead."""
    chain = []
    current = store.get_by_id(bead_id)

    while current and current.parent_bead_id != "root":
        chain.append(current)
        current = store.get_by_id(current.parent_bead_id)

    if current:
        chain.append(current)

    return list(reversed(chain))
```

## Validation

Beads are validated on creation:

```python
from adversarial_debate.exceptions import BeadValidationError

try:
    bead = Bead(
        bead_id="x",  # Too short!
        confidence=1.5,  # Out of range!
        # ...
    )
except BeadValidationError as e:
    print(f"Invalid bead: {e}")
    print(f"Field: {e.field}")
    print(f"Details: {e.details}")
```

Validation rules:
- `bead_id`: Minimum 3 characters
- `thread_id`: Minimum 3 characters
- `idempotency_key`: Minimum 3 characters
- `confidence`: Must be between 0.0 and 1.0

## Thread Safety

The BeadStore uses file locking for thread-safe operations:

```python
# Safe for concurrent appends from multiple processes
store.append(bead)  # Uses fcntl.LOCK_EX
```

This allows multiple agents to write to the same ledger safely.

## Custom Agent Integration

When creating a custom agent, emit beads for your analysis:

```python
from adversarial_debate.agents.base import BaseAttackAgent
from adversarial_debate.store.beads import (
    Bead, BeadStore, BeadType, Artefact, ArtefactType
)

class MyCustomAgent(BaseAttackAgent):
    def analyse(self, target: str, context: dict) -> dict:
        store = BeadStore()

        # Generate bead ID
        bead_id = BeadStore.generate_bead_id("MCA")  # Custom prefix

        # Perform analysis
        findings = self._do_analysis(target)

        # Record bead
        bead = Bead(
            bead_id=bead_id,
            parent_bead_id=context.get("parent_bead_id", "root"),
            thread_id=context["run_id"],
            task_id=f"custom-{target}",
            timestamp_iso=BeadStore.now_iso(),
            agent=self.__class__.__name__,
            bead_type=BeadType.PROPOSAL,  # Or custom type
            payload={
                "target": target,
                "findings": findings,
            },
            artefacts=[
                Artefact(type=ArtefactType.FILE, ref=target),
            ],
            idempotency_key=f"custom-{target}-{context['run_id']}",
            confidence=self._calculate_confidence(findings),
            assumptions=self.assumptions,
            unknowns=self.unknowns,
        )

        store.append_idempotent(bead)

        return {
            "bead_id": bead_id,
            "findings": findings,
        }
```

## Analysing the Ledger

### Command-Line Tools

```bash
# Count beads
wc -l beads/ledger.jsonl

# View recent beads
tail -5 beads/ledger.jsonl | jq .

# Find all critical findings
grep -i "critical" beads/ledger.jsonl | jq .

# Count by agent
jq -s 'group_by(.agent) | map({agent: .[0].agent, count: length})' \
  beads/ledger.jsonl
```

### Python Analysis

```python
from collections import Counter
from adversarial_debate.store.beads import BeadStore, BeadType

store = BeadStore()

# Statistics
beads = store.get_all()
print(f"Total beads: {len(beads)}")

# Count by type
type_counts = Counter(b.bead_type for b in beads)
for bead_type, count in type_counts.most_common():
    print(f"  {bead_type.value}: {count}")

# Count by agent
agent_counts = Counter(b.agent for b in beads)
for agent, count in agent_counts.most_common():
    print(f"  {agent}: {count}")

# Average confidence by agent
from statistics import mean
for agent in set(b.agent for b in beads):
    agent_beads = [b for b in beads if b.agent == agent]
    avg_conf = mean(b.confidence for b in agent_beads)
    print(f"  {agent}: {avg_conf:.2f}")
```

### Replay Analysis

Rebuild state from beads:

```python
def replay_run(store: BeadStore, run_id: str) -> dict:
    """Reconstruct analysis results from beads."""
    beads = store.query(thread_id=run_id)

    findings = []
    verdict = None

    for bead in beads:
        if bead.bead_type in [
            BeadType.EXPLOIT_ANALYSIS,
            BeadType.BREAK_ANALYSIS,
            BeadType.CHAOS_ANALYSIS,
            BeadType.CRYPTO_ANALYSIS,
        ]:
            findings.extend(bead.payload.get("findings", []))
        elif bead.bead_type == BeadType.ARBITER_VERDICT:
            verdict = bead.payload

    return {
        "run_id": run_id,
        "findings": findings,
        "verdict": verdict,
    }
```

## Ledger Maintenance

### Archiving Old Runs

```bash
# Archive runs older than 30 days
mkdir -p beads/archive

# Extract old beads (by date in bead_id)
jq -c 'select(.bead_id | test("B-202401"))' beads/ledger.jsonl \
  > beads/archive/2024-01.jsonl

# Remove from main ledger (create new file)
jq -c 'select(.bead_id | test("B-202401") | not)' beads/ledger.jsonl \
  > beads/ledger.jsonl.new
mv beads/ledger.jsonl.new beads/ledger.jsonl
```

### Backup

```bash
# Simple backup
cp beads/ledger.jsonl beads/ledger.jsonl.bak

# Compressed backup
gzip -k beads/ledger.jsonl
```

### Integrity Check

```python
def verify_ledger(store: BeadStore) -> list[str]:
    """Verify ledger integrity."""
    errors = []
    seen_ids = set()

    for bead in store.iter_all():
        # Check for duplicate IDs
        if bead.bead_id in seen_ids:
            errors.append(f"Duplicate bead_id: {bead.bead_id}")
        seen_ids.add(bead.bead_id)

        # Check parent exists (unless root)
        if bead.parent_bead_id != "root":
            if bead.parent_bead_id not in seen_ids:
                errors.append(
                    f"Missing parent {bead.parent_bead_id} "
                    f"for bead {bead.bead_id}"
                )

    return errors
```

## Best Practices

### 1. Use Meaningful Idempotency Keys

```python
# Good - descriptive and unique
idempotency_key = f"exploit-{file_path}-{run_id}"

# Bad - not descriptive
idempotency_key = str(uuid.uuid4())
```

### 2. Record Assumptions and Unknowns

```python
bead = Bead(
    # ...
    assumptions=[
        "Input validation is performed at API gateway",
        "Database uses parameterised queries",
    ],
    unknowns=[
        "WAF configuration",
        "Rate limiting settings",
    ],
)
```

### 3. Link Related Artefacts

```python
artefacts = [
    Artefact(type=ArtefactType.FILE, ref="src/api/users.py"),
    Artefact(type=ArtefactType.FILE, ref="src/models/user.py"),
    Artefact(type=ArtefactType.COMMIT, ref="abc123"),
]
```

### 4. Set Appropriate Confidence

```python
# High confidence - clear evidence
confidence = 0.95

# Medium confidence - likely but uncertain
confidence = 0.70

# Low confidence - possible issue
confidence = 0.40
```

### 5. Use Proper Bead Chains

```python
# Always reference parent when creating child beads
child_bead = Bead(
    bead_id=BeadStore.generate_bead_id(),
    parent_bead_id=parent_bead.bead_id,  # Link to parent
    # ...
)
```

## See Also

- [Architecture](../reference/architecture.md) — System internals
- [Extending Agents](extending-agents.md) — Creating custom agents
- [Data Structures](../reference/data-structures.md) — Type definitions
