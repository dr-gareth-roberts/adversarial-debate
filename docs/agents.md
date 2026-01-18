# Agent System Documentation

This document provides a comprehensive guide to the agent system in Adversarial Debate, explaining how each specialized agent works, what it analyzes, and how agents coordinate to produce security assessments.

## Table of Contents

- [Agent Architecture Overview](#agent-architecture-overview)
- [Base Agent Contract](#base-agent-contract)
- [ChaosOrchestrator](#chaosorchestrator)
- [ExploitAgent](#exploitagent)
- [BreakAgent](#breakagent)
- [ChaosAgent](#chaosagent)
- [Arbiter](#arbiter)
- [Agent Coordination Patterns](#agent-coordination-patterns)

---

## Agent Architecture Overview

The agent system follows a hierarchical structure where the ChaosOrchestrator acts as the strategic planner, three specialized "red team" agents perform targeted analysis, and the Arbiter consolidates findings into actionable verdicts.

```
                    +---------------------+
                    |  ChaosOrchestrator  |
                    |   (Strategic Plan)  |
                    +----------+----------+
                               |
                               | AttackPlan
                               |
         +---------------------+---------------------+
         |                     |                     |
         v                     v                     v
+----------------+    +----------------+    +----------------+
|  ExploitAgent  |    |   BreakAgent   |    |   ChaosAgent   |
|   (Security)   |    |    (Logic)     |    |  (Resilience)  |
+-------+--------+    +-------+--------+    +-------+--------+
        |                     |                     |
        |   Findings          |   Findings          |   Experiments
        |                     |                     |
        +---------------------+---------------------+
                              |
                              v
                    +---------------------+
                    |      Arbiter        |
                    |  (Verdict & Tasks)  |
                    +---------------------+
```

### Agent Specializations

| Agent | Domain | Focus Areas | Model Tier |
|-------|--------|-------------|------------|
| **ChaosOrchestrator** | Planning | Risk assessment, agent assignment, parallelization | HOSTED_SMALL |
| **ExploitAgent** | Security | OWASP Top 10, CVEs, exploit payloads | HOSTED_LARGE |
| **BreakAgent** | Correctness | Logic bugs, edge cases, race conditions | HOSTED_LARGE |
| **ChaosAgent** | Resilience | Failure modes, chaos experiments | HOSTED_SMALL |
| **Arbiter** | Judgment | Validation, severity calibration, remediation | HOSTED_LARGE |

---

## Base Agent Contract

All agents inherit from the abstract `Agent` base class, which defines the contract that every agent must fulfill.

### Required Properties

```python
class Agent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name (e.g., 'ExploitAgent')."""
        ...
    
    @property
    @abstractmethod
    def bead_type(self) -> BeadType:
        """Type of bead this agent produces."""
        ...
    
    @property
    @abstractmethod
    def model_tier(self) -> ModelTier:
        """Required model capability tier."""
        ...
```

### Required Methods

```python
class Agent(ABC):
    @abstractmethod
    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Construct the LLM prompt from context.
        
        Returns a list of Message objects, typically:
        1. System message defining role and output format
        2. User message with task details and code
        """
        ...
    
    @abstractmethod
    def _parse_response(self, response: str, context: AgentContext) -> dict[str, Any]:
        """Parse LLM response into structured output.
        
        Validates JSON structure and normalizes findings.
        """
        ...
```

### Execution Flow

The `run()` method orchestrates the agent lifecycle:

```python
async def run(self, context: AgentContext) -> AgentOutput:
    # 1. Build prompt from context
    messages = self._build_prompt(context)
    
    # 2. Get model for this agent's tier
    model = self.provider.get_model_for_tier(self.model_tier)
    
    # 3. Call LLM with JSON mode
    response = await self.provider.complete(
        messages,
        model=model,
        json_mode=True
    )
    
    # 4. Parse response into structured output
    result = self._parse_response(response.content, context)
    
    # 5. Create bead for audit trail
    bead = self._create_bead(context, result)
    
    # 6. Append to ledger
    self.bead_store.append(bead)
    
    # 7. Return standardized output
    return AgentOutput(
        agent_name=self.name,
        result=result,
        beads_out=[bead],
        confidence=result.get("confidence", 0.5),
        assumptions=result.get("assumptions", []),
        unknowns=result.get("unknowns", []),
        errors=[]
    )
```

---

## ChaosOrchestrator

The ChaosOrchestrator is the strategic brain of the system. It analyzes code changes, assesses risk, and creates a coordinated attack plan that assigns work to specialized agents.

### Purpose

The orchestrator's job is to answer: "Given these code changes, what should we test, who should test it, and in what order?" It performs risk-based prioritization to focus testing effort where it matters most.

### Input Context

The ChaosOrchestrator expects these inputs in `context.inputs`:

| Field | Type | Description |
|-------|------|-------------|
| `changed_files` | `list[dict]` | Files that changed with metadata |
| `patches` | `dict[str, str]` | File path to diff/content mapping |
| `exposure` | `str` | Code exposure level (public/authenticated/internal) |
| `time_budget_seconds` | `int` | Total time available for analysis |
| `historical_findings` | `list[dict]` | Previous findings for context |

### Output: AttackPlan

The orchestrator produces an `AttackPlan` containing:

```python
@dataclass
class AttackPlan:
    plan_id: str                    # Unique plan identifier
    thread_id: str                  # Workstream identifier
    task_id: str                    # Task identifier
    risk_level: RiskLevel           # Overall risk assessment
    risk_factors: list[str]         # Identified risk factors
    risk_score: int                 # Numeric risk score (0-100)
    attacks: list[Attack]           # Individual attack assignments
    parallel_groups: list[ParallelGroup]  # Concurrent execution groups
    execution_order: list[str]      # Ordered attack IDs
    skipped: list[SkipReason]       # Items skipped with reasons
    estimated_total_duration_seconds: int
    attack_surface_summary: str     # Human-readable summary
    recommendations: list[str]      # Strategic recommendations
```

### Risk Assessment Logic

The orchestrator evaluates risk based on multiple factors:

```
Risk Score Calculation:
+------------------+--------+------------------------------------------+
| Factor           | Weight | Criteria                                 |
+------------------+--------+------------------------------------------+
| Exposure Level   | 30%    | public=high, authenticated=med, internal=low |
| Data Sensitivity | 25%    | PII, credentials, financial data         |
| Code Complexity  | 20%    | Cyclomatic complexity, nesting depth     |
| Change Magnitude | 15%    | Lines changed, files affected            |
| Historical Issues| 10%    | Previous vulnerabilities in same area    |
+------------------+--------+------------------------------------------+
```

### Agent Assignment Logic

The orchestrator assigns agents based on file characteristics:

```
File Analysis -> Agent Assignment:

+------------------------+------------------+--------------------------------+
| File Characteristic    | Assigned Agent   | Rationale                      |
+------------------------+------------------+--------------------------------+
| SQL queries, ORM calls | ExploitAgent     | SQL injection risk             |
| User input handling    | ExploitAgent     | Input validation vulnerabilities|
| Authentication code    | ExploitAgent     | Auth bypass, privilege escalation|
| Business logic         | BreakAgent       | Logic errors, edge cases       |
| State management       | BreakAgent       | State corruption, race conditions|
| Numeric calculations   | BreakAgent       | Overflow, precision errors     |
| External API calls     | ChaosAgent       | Dependency failure handling    |
| Database connections   | ChaosAgent       | Connection pool exhaustion     |
| File I/O operations    | ChaosAgent       | Resource exhaustion            |
+------------------------+------------------+--------------------------------+
```

### Prompt Structure

The orchestrator's prompt follows this structure:

```
SYSTEM MESSAGE:
- Role: Strategic security analyst
- Task: Create attack plan for code changes
- Output format: JSON schema for AttackPlan

USER MESSAGE:
- Changed files with metadata
- Code patches/diffs
- Exposure level and context
- Time budget constraints
- Historical findings (if any)
- Codebase context (related files)
```

### Example Output

```json
{
  "plan_id": "PLAN-20240115-143022",
  "risk_level": "HIGH",
  "risk_score": 78,
  "risk_factors": [
    "Public API endpoint handling user input",
    "SQL query construction from request parameters",
    "No input validation visible in diff"
  ],
  "attacks": [
    {
      "id": "ATK-001",
      "agent": "EXPLOIT_AGENT",
      "target_file": "src/api/users.py",
      "target_function": "get_user",
      "priority": "CRITICAL",
      "attack_vectors": [
        {
          "name": "SQL Injection",
          "category": "A03:2021",
          "payload_hints": ["' OR '1'='1", "'; DROP TABLE users;--"]
        }
      ],
      "time_budget_seconds": 60
    }
  ],
  "parallel_groups": [
    {
      "group_id": "PG-001",
      "attack_ids": ["ATK-001", "ATK-002"],
      "estimated_duration_seconds": 60
    }
  ]
}
```

---

## ExploitAgent

The ExploitAgent is a security specialist focused on finding exploitable vulnerabilities, particularly those in the OWASP Top 10.

### Purpose

The ExploitAgent answers: "Can an attacker exploit this code to compromise security?" It generates working exploit payloads and maps findings to industry-standard vulnerability classifications.

### OWASP Top 10 Coverage

| Category | Code | Description | Detection Focus |
|----------|------|-------------|-----------------|
| **A01:2021** | Broken Access Control | Unauthorized access to resources | Missing auth checks, IDOR |
| **A02:2021** | Cryptographic Failures | Weak or missing encryption | Hardcoded secrets, weak algorithms |
| **A03:2021** | Injection | SQL, NoSQL, OS, LDAP injection | Unsanitized input in queries |
| **A04:2021** | Insecure Design | Flawed architecture | Missing security controls |
| **A05:2021** | Security Misconfiguration | Improper settings | Debug enabled, default creds |
| **A06:2021** | Vulnerable Components | Outdated dependencies | Known CVEs in imports |
| **A07:2021** | Auth Failures | Broken authentication | Weak passwords, session issues |
| **A08:2021** | Data Integrity Failures | Untrusted data | Deserialization, unsigned updates |
| **A09:2021** | Logging Failures | Insufficient monitoring | Missing audit logs |
| **A10:2021** | SSRF | Server-side request forgery | Unvalidated URLs |

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Target code to analyze |
| `file_path` | `str` | Path to the file |
| `file_paths` | `list[str]` | All files in scope |
| `focus_areas` | `list[str]` | Specific areas to focus on |
| `attack_vectors` | `list[dict]` | Hints from orchestrator |
| `security_context` | `dict` | Auth mechanisms, data sensitivity |

### Output: Exploit Findings

Each finding includes:

```python
{
    "finding_id": "EXP-001",
    "title": "SQL Injection in user lookup",
    "severity": "CRITICAL",  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    "owasp_category": "A03:2021",
    "cwe_id": "CWE-89",
    "description": "User input directly concatenated into SQL query",
    "vulnerable_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
    "location": {
        "file": "src/api/users.py",
        "line": 42,
        "function": "get_user"
    },
    "exploit_payload": "1 OR 1=1; DROP TABLE users;--",
    "proof_of_concept": "curl 'http://api/users?id=1%20OR%201=1'",
    "impact": "Full database access, data exfiltration, data destruction",
    "remediation": "Use parameterized queries or ORM",
    "confidence": 0.95
}
```

### Severity Classification

```
Severity Determination Matrix:
+----------+------------------+------------------+------------------+
|          | High Impact      | Medium Impact    | Low Impact       |
+----------+------------------+------------------+------------------+
| Easy     | CRITICAL         | HIGH             | MEDIUM           |
| Exploit  | (RCE, SQLi)      | (Auth bypass)    | (Info disclosure)|
+----------+------------------+------------------+------------------+
| Moderate | HIGH             | MEDIUM           | LOW              |
| Exploit  | (Stored XSS)     | (CSRF)           | (Verbose errors) |
+----------+------------------+------------------+------------------+
| Hard     | MEDIUM           | LOW              | INFO             |
| Exploit  | (Race condition) | (Timing attack)  | (Best practice)  |
+----------+------------------+------------------+------------------+
```

### Prompt Structure

```
SYSTEM MESSAGE:
- Role: Expert penetration tester and security researcher
- Task: Find exploitable security vulnerabilities
- Focus: OWASP Top 10, working exploits, real-world impact
- Output: JSON array of findings with exploit payloads

USER MESSAGE:
- Target code with line numbers
- File context and imports
- Security context (auth, data sensitivity)
- Attack hints from orchestrator
- Related code for context
```

---

## BreakAgent

The BreakAgent specializes in finding logic bugs, edge cases, and correctness issues that could cause unexpected behavior or data corruption.

### Purpose

The BreakAgent answers: "What inputs or conditions could cause this code to behave incorrectly?" It uses a systematic attack taxonomy to probe for weaknesses.

### Attack Taxonomy

The BreakAgent employs five categories of attacks:

```
+------------------+--------------------------------+---------------------------+
| Category         | Description                    | Example Attacks           |
+------------------+--------------------------------+---------------------------+
| BOUNDARY         | Values at limits of ranges     | MAX_INT, empty string,    |
|                  |                                | array bounds, zero        |
+------------------+--------------------------------+---------------------------+
| TYPE_CONFUSION   | Unexpected types or formats    | null vs undefined,        |
|                  |                                | string vs number, NaN     |
+------------------+--------------------------------+---------------------------+
| CONCURRENCY      | Race conditions, deadlocks     | Parallel writes, lock     |
|                  |                                | ordering, check-then-use  |
+------------------+--------------------------------+---------------------------+
| STATE            | Invalid state transitions      | Double-free, use after    |
|                  |                                | close, inconsistent state |
+------------------+--------------------------------+---------------------------+
| RESOURCE         | Resource exhaustion            | Memory leaks, file handle |
|                  |                                | exhaustion, infinite loops|
+------------------+--------------------------------+---------------------------+
```

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Target code to analyze |
| `file_path` | `str` | Path to the file |
| `attack_hints` | `list[dict]` | Hints from orchestrator |
| `focus_areas` | `list[str]` | Specific areas to probe |
| `related_code` | `dict[str, str]` | Related files for context |

### Output: Break Findings

Each finding includes:

```python
{
    "finding_id": "BRK-001",
    "title": "Integer overflow in balance calculation",
    "category": "BOUNDARY",
    "severity": "HIGH",
    "description": "Adding large values can overflow int32, causing negative balance",
    "vulnerable_code": "new_balance = current_balance + deposit_amount",
    "location": {
        "file": "src/accounts/balance.py",
        "line": 87,
        "function": "add_funds"
    },
    "trigger_condition": "deposit_amount > MAX_INT - current_balance",
    "proof_of_concept": "add_funds(account, 2147483647)",
    "expected_behavior": "Reject deposit or use larger integer type",
    "actual_behavior": "Balance becomes negative, allowing unlimited withdrawals",
    "impact": "Financial loss, data corruption",
    "remediation": "Use checked arithmetic or BigInt",
    "confidence": 0.88
}
```

### Category-Specific Probes

**Boundary Value Analysis:**
```
For numeric inputs:
- Zero, negative zero
- MIN_VALUE, MAX_VALUE
- MIN_VALUE - 1, MAX_VALUE + 1
- Floating point: NaN, Infinity, -Infinity, epsilon

For strings:
- Empty string, whitespace only
- Very long strings (buffer overflow)
- Unicode edge cases (null bytes, RTL)

For collections:
- Empty collection
- Single element
- Maximum size
- Duplicate elements
```

**Concurrency Probes:**
```
Race condition patterns:
- Check-then-act (TOCTOU)
- Read-modify-write without locks
- Double-checked locking
- Shared mutable state
- Callback ordering assumptions
```

### Prompt Structure

```
SYSTEM MESSAGE:
- Role: Quality assurance engineer and bug hunter
- Task: Find logic bugs and edge cases
- Focus: Attack taxonomy categories
- Output: JSON array of findings with PoC

USER MESSAGE:
- Target code with line numbers
- Function signatures and types
- Attack hints from orchestrator
- Related code for state understanding
```

---

## ChaosAgent

The ChaosAgent designs experiments to test system resilience against failures and adverse conditions.

### Purpose

The ChaosAgent answers: "How does this code behave when things go wrong?" It designs safe chaos experiments that can be run in controlled environments.

### Experiment Categories

```
+------------------+--------------------------------+---------------------------+
| Category         | Failure Mode                   | Example Experiments       |
+------------------+--------------------------------+---------------------------+
| DEPENDENCY       | External service failures      | Database down, API 500,   |
|                  |                                | cache miss, queue full    |
+------------------+--------------------------------+---------------------------+
| NETWORK          | Network issues                 | Latency injection,        |
|                  |                                | packet loss, DNS failure  |
+------------------+--------------------------------+---------------------------+
| RESOURCE         | Resource constraints           | Memory pressure, CPU      |
|                  |                                | throttle, disk full       |
+------------------+--------------------------------+---------------------------+
| TIME             | Time-related failures          | Clock skew, timeout,      |
|                  |                                | leap second, DST          |
+------------------+--------------------------------+---------------------------+
| STATE            | State corruption               | Partial writes, stale     |
|                  |                                | cache, split brain        |
+------------------+--------------------------------+---------------------------+
```

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Target code to analyze |
| `file_path` | `str` | Path to the file |
| `infrastructure_context` | `dict` | Dependencies, deployment info |
| `focus_areas` | `list[str]` | Specific failure modes to test |

### Output: Chaos Experiments

Each experiment includes:

```python
{
    "experiment_id": "CHAOS-001",
    "title": "Database connection pool exhaustion",
    "category": "RESOURCE",
    "description": "Test behavior when all DB connections are in use",
    "hypothesis": "System should queue requests and return 503 after timeout",
    "target_component": "src/db/connection_pool.py",
    "injection_point": "ConnectionPool.acquire()",
    "failure_injection": {
        "type": "delay",
        "parameters": {
            "delay_ms": 30000,
            "probability": 1.0
        }
    },
    "expected_behavior": {
        "graceful_degradation": true,
        "error_handling": "Return 503 Service Unavailable",
        "recovery": "Automatic when connections freed"
    },
    "actual_behavior_unknown": true,
    "blast_radius": "All database operations",
    "rollback_procedure": "Remove delay injection",
    "safety_checks": [
        "Monitor error rate",
        "Set maximum experiment duration",
        "Have kill switch ready"
    ],
    "risk_level": "MEDIUM",
    "confidence": 0.75
}
```

### Resilience Assessment

The ChaosAgent also assesses overall resilience:

```python
{
    "resilience_score": 65,
    "strengths": [
        "Retry logic present for API calls",
        "Circuit breaker pattern implemented"
    ],
    "weaknesses": [
        "No timeout on database queries",
        "Missing fallback for cache failures",
        "No graceful degradation path"
    ],
    "recommendations": [
        "Add query timeouts to prevent connection exhaustion",
        "Implement cache-aside pattern with fallback",
        "Add health checks for dependencies"
    ]
}
```

### Prompt Structure

```
SYSTEM MESSAGE:
- Role: Site reliability engineer and chaos engineer
- Task: Design safe chaos experiments
- Focus: Failure modes and resilience
- Output: JSON with experiments and assessment

USER MESSAGE:
- Target code with dependencies
- Infrastructure context
- Current error handling patterns
- Deployment environment details
```

---

## Arbiter

The Arbiter is the final judge that reviews all findings, validates their exploitability, and renders a verdict.

### Purpose

The Arbiter answers: "Which findings are real, how severe are they, and should this code be allowed to merge?" It acts as the senior security reviewer making the final call.

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `findings` | `list[dict]` | All findings from red team agents |
| `original_task` | `str` | Description of the code change |
| `changed_files` | `list[dict]` | Files that were changed |
| `codebase_context` | `dict` | Security controls, mitigations |
| `historical_data` | `dict` | Previous findings, false positive rate |

### Validation Process

The Arbiter validates each finding through multiple lenses:

```
Validation Pipeline:
+------------------+     +------------------+     +------------------+
|  Exploitability  | --> |  Context Check   | --> |  Severity Adjust |
|  Assessment      |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
  Can this be          Are there existing       What's the real-
  exploited in         mitigations that         world impact given
  practice?            reduce risk?             the context?
```

### Verdict Decisions

| Decision | Criteria | Action |
|----------|----------|--------|
| **BLOCK** | Critical/High severity confirmed findings | Must fix before merge |
| **WARN** | Medium severity or uncertain findings | Track, fix in follow-up |
| **PASS** | No significant issues found | Approved to merge |

### Output: ArbiterVerdict

```python
@dataclass
class ArbiterVerdict:
    verdict_id: str
    thread_id: str
    task_id: str
    decision: VerdictDecision      # BLOCK, WARN, PASS
    decision_rationale: str        # Explanation of decision
    blocking_issues: list[ValidatedFinding]
    warnings: list[ValidatedFinding]
    passed_findings: list[ValidatedFinding]
    false_positives: list[RejectedFinding]
    remediation_tasks: list[RemediationTask]
    total_remediation_effort: str  # e.g., "2-4 hours"
    summary: str                   # Executive summary
    key_concerns: list[str]
    recommendations: list[str]
    findings_analyzed: int
    confidence: float
    assumptions: list[str]
    limitations: list[str]
```

### Finding Validation

Each finding is validated and may be:

**Confirmed (ValidatedFinding):**
```python
{
    "original_id": "EXP-001",
    "original_agent": "ExploitAgent",
    "validation_status": "CONFIRMED",
    "validated_severity": "CRITICAL",
    "exploitation_difficulty": "TRIVIAL",
    "real_world_exploitability": 0.95,
    "impact_description": "Full database compromise",
    "remediation_effort": "HOURS",
    "suggested_fix": "Use parameterized queries",
    "fix_code_example": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
}
```

**Rejected (RejectedFinding):**
```python
{
    "original_id": "BRK-003",
    "original_agent": "BreakAgent",
    "rejection_reason": "Input is validated upstream",
    "rejection_category": "NOT_EXPLOITABLE",
    "evidence": "See validation in middleware.py:45"
}
```

### Remediation Tasks

For each blocking issue, the Arbiter creates actionable tasks:

```python
{
    "finding_id": "EXP-001",
    "title": "Fix SQL injection in user lookup",
    "description": "Replace string concatenation with parameterized query",
    "priority": "CRITICAL",
    "estimated_effort": "HOURS",
    "fix_guidance": "1. Import db.parameterize\n2. Replace query construction\n3. Add input validation",
    "acceptance_criteria": [
        "No string concatenation in SQL queries",
        "All user input sanitized",
        "Passing SQL injection test suite"
    ]
}
```

### Prompt Structure

```
SYSTEM MESSAGE:
- Role: Senior security architect and code reviewer
- Task: Validate findings and render verdict
- Focus: Real-world exploitability, context-aware assessment
- Output: JSON verdict with validated findings

USER MESSAGE:
- All findings from red team agents
- Original code and changes
- Codebase security context
- Existing mitigations and controls
- Historical false positive data
```

---

## Agent Coordination Patterns

### Sequential Dependency

Some analyses must complete before others can begin:

```
ChaosOrchestrator
        |
        | (must complete first to create plan)
        v
[ExploitAgent, BreakAgent, ChaosAgent]  <- parallel
        |
        | (must complete to have findings)
        v
    Arbiter
```

### Parallel Execution

Red team agents run concurrently when analyzing independent targets:

```python
async def run_red_team(attack_plan: AttackPlan) -> list[AgentOutput]:
    tasks = []
    for attack in attack_plan.attacks:
        agent = get_agent_for_type(attack.agent)
        context = create_context_for_attack(attack)
        tasks.append(agent.run(context))
    
    return await asyncio.gather(*tasks)
```

### Information Sharing

Agents share context through the bead ledger:

```
ChaosOrchestrator
    |
    +-- writes ATTACK_PLAN bead
            |
            +-- ExploitAgent reads for attack hints
            +-- BreakAgent reads for focus areas
            +-- ChaosAgent reads for infrastructure context
            |
            +-- All write analysis beads
                    |
                    +-- Arbiter reads all for verdict
```

### Error Handling

Agent failures are isolated and don't block other agents:

```python
async def run_with_fallback(agent: Agent, context: AgentContext) -> AgentOutput:
    try:
        return await asyncio.wait_for(
            agent.run(context),
            timeout=context.inputs.get("timeout", 120)
        )
    except asyncio.TimeoutError:
        return AgentOutput(
            agent_name=agent.name,
            result={"error": "timeout"},
            beads_out=[],
            confidence=0.0,
            errors=["Agent timed out"]
        )
    except Exception as e:
        return AgentOutput(
            agent_name=agent.name,
            result={"error": str(e)},
            beads_out=[],
            confidence=0.0,
            errors=[str(e)]
        )
```

---

## Next Steps

For more information, see:

- [Architecture Deep Dive](architecture.md) - System overview
- [Data Structures Reference](data-structures.md) - Complete type definitions
- [Pipeline Execution Guide](pipeline.md) - Step-by-step walkthrough
- [API Reference](api.md) - Python API documentation
