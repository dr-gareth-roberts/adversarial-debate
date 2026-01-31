# Agent Reference

Detailed reference for all agents in the Adversarial Debate framework.

## Agent Overview

| Agent | Purpose | Bead Type | Model Tier |
|-------|---------|-----------|------------|
| [ChaosOrchestrator](#chaosorchestrator) | Coordinates attacks | `attack_plan` | Large |
| [ExploitAgent](#exploitagent) | Security vulnerabilities | `exploit_analysis` | Large |
| [BreakAgent](#breakagent) | Logic bugs & edge cases | `break_analysis` | Large |
| [ChaosAgent](#chaosagent) | Resilience testing | `chaos_analysis` | Large |
| [CryptoAgent](#cryptoagent) | Cryptographic weaknesses | `crypto_analysis` | Large |
| [CrossExaminationAgent](#crossexaminationagent) | Challenge findings | `cross_examination` | Large |
| [Arbiter](#arbiter) | Final verdict | `arbiter_verdict` | Large |

## Agent Pipeline

```
                    ┌──────────────────────┐
                    │  ChaosOrchestrator   │
                    │  (Attack Planning)   │
                    └──────────┬───────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │ExploitAgent │     │ BreakAgent  │     │ ChaosAgent  │
    │ (Security)  │     │  (Logic)    │     │(Resilience) │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │CrossExaminationAgent │
                    │ (Challenge Findings) │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Arbiter        │
                    │  (Final Verdict)     │
                    └──────────────────────┘
```

---

## ChaosOrchestrator

The ChaosOrchestrator analyses target code and creates attack plans that coordinate the work of attack agents.

### Purpose

- Analyse attack surface of code changes
- Assign work to appropriate agents
- Prioritise attacks by risk
- Enable parallel execution where possible

### Bead Type

`attack_plan`

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | str | Code to analyse |
| `file_path` | str | Path to file |
| `language` | str | Programming language |
| `exposure` | str | `public`, `authenticated`, `internal` |
| `data_sensitivity` | str | `high`, `medium`, `low` |
| `related_files` | dict | Related code for context |

### Output Schema

```python
{
    "attack_surface_analysis": {
        "files": [
            {
                "file_path": "src/api/users.py",
                "risk_score": 85,  # 0-100
                "risk_factors": ["handles user input", "database queries"],
                "recommended_agents": ["ExploitAgent", "BreakAgent"],
                "attack_vectors": ["SQL injection", "boundary values"],
                "exposure": "public",
                "data_sensitivity": "high",
            }
        ],
        "total_risk_score": 85,
        "highest_risk_file": "src/api/users.py",
        "primary_concerns": ["SQL injection", "missing auth"],
        "recommended_focus_areas": ["Database layer", "Input validation"],
    },
    "risk_level": "HIGH",  # LOW, MEDIUM, HIGH, CRITICAL
    "risk_factors": ["User input handling", "Database access"],
    "attacks": [
        {
            "id": "ATK-001",
            "agent": "ExploitAgent",  # ExploitAgent, BreakAgent, ChaosAgent, CryptoAgent
            "target_file": "src/api/users.py",
            "target_function": "get_user",
            "priority": 1,  # 1-5, 1 = highest
            "attack_vectors": [
                {
                    "name": "SQL Injection",
                    "description": "Test user_id for SQL injection",
                    "category": "injection",
                    "payload_hints": ["' OR '1'='1", "'; DROP TABLE--"],
                    "expected_behavior": "Query should be parameterised",
                    "success_indicators": ["returns all rows"],
                }
            ],
            "time_budget_seconds": 60,
            "rationale": "High risk SQL query with user input",
            "depends_on": [],
            "can_parallel_with": ["ATK-002"],
            "hints": ["Check line 42"],
        }
    ],
    "parallel_groups": [
        {
            "group_id": "PG-001",
            "attack_ids": ["ATK-001", "ATK-002"],
            "estimated_duration_seconds": 120,
        }
    ],
    "execution_order": ["ATK-001", "ATK-002", "ATK-003"],
    "skipped": [
        {
            "target": "src/config.py",
            "reason": "Static configuration",
            "category": "low_risk",
        }
    ],
    "recommendations": ["Focus on database layer"],
    "confidence": 0.8,
    "assumptions": [],
    "unknowns": [],
}
```

### Risk Assessment Factors

The orchestrator considers:

1. **Exposure** — Public APIs vs internal services
2. **Data sensitivity** — PII, credentials, financial data
3. **Complexity** — Complex logic more likely to have bugs
4. **Change size** — Larger changes have more attack surface
5. **Historical patterns** — Similar code with past vulnerabilities

---

## ExploitAgent

The ExploitAgent finds exploitable security vulnerabilities based on OWASP Top 10 categories.

### Purpose

- Identify security vulnerabilities
- Generate working exploit payloads
- Map findings to OWASP and CWE
- Provide concrete remediation

### Bead Type

`exploit_analysis`

### OWASP Coverage

| Category | Description | Detection |
|----------|-------------|-----------|
| A01:2021 | Broken Access Control | IDOR, path traversal, missing auth |
| A02:2021 | Cryptographic Failures | Weak hashing, hardcoded secrets |
| A03:2021 | Injection | SQL, command, XSS, template |
| A04:2021 | Insecure Design | Missing rate limits, business logic |
| A05:2021 | Security Misconfiguration | Debug mode, CORS, verbose errors |
| A06:2021 | Vulnerable Components | Known CVEs in dependencies |
| A07:2021 | Authentication Failures | Session issues, JWT problems |
| A08:2021 | Data Integrity Failures | Insecure deserialisation |
| A09:2021 | Logging Failures | Sensitive data in logs |
| A10:2021 | SSRF | User-controlled URLs |

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | str | Code to analyse |
| `file_path` | str | Path to file |
| `function_name` | str | Specific function (optional) |
| `language` | str | Programming language |
| `exposure` | str | Exposure level |
| `data_sensitivity` | str | Data sensitivity |
| `framework` | str | Framework in use |
| `security_context` | dict | Auth, input handling flags |
| `attack_hints` | list | Hints from orchestrator |
| `payload_hints` | list | Suggested payloads |

### Output Schema

```python
{
    "target": {
        "file_path": "src/api/users.py",
        "function_name": "get_user",
        "exposure": "public",
    },
    "findings": [
        {
            "id": "EXPLOIT-001",
            "title": "SQL Injection in user lookup",
            "severity": "CRITICAL",  # CRITICAL, HIGH, MEDIUM, LOW
            "owasp_category": "A03:2021-Injection",
            "cwe_id": "CWE-89",
            "confidence": 0.9,
            "description": "User ID is interpolated into SQL query",
            "vulnerable_code": {
                "file": "src/api/users.py",
                "line_start": 42,
                "line_end": 45,
                "snippet": "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
            },
            "exploit": {
                "description": "Extract password hashes",
                "payload": "1' UNION SELECT password FROM users--",
                "curl_command": "curl 'http://target/api/user?id=1%27%20UNION...'",
                "prerequisites": ["Valid session"],
                "impact": "Full database read access",
            },
            "remediation": {
                "immediate": "Use parameterised queries",
                "code_fix": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
                "defense_in_depth": ["Add WAF rule", "Least-privilege DB user"],
            },
        }
    ],
    "attack_surface_analysis": {
        "user_inputs": ["query parameters", "POST body"],
        "external_calls": ["database", "external API"],
        "sensitive_data": ["passwords", "tokens"],
    },
    "confidence": 0.85,
    "assumptions": ["No WAF in place"],
    "unknowns": ["Runtime configuration"],
}
```

### Severity Guidelines

| Severity | Examples |
|----------|----------|
| CRITICAL | RCE, full database access, authentication bypass |
| HIGH | Significant data access, privilege escalation |
| MEDIUM | Limited data access, information disclosure |
| LOW | Theoretical issues, requires unlikely conditions |

---

## BreakAgent

The BreakAgent finds logic bugs and edge cases through systematic probing.

### Purpose

- Find logic errors and edge cases
- Identify race conditions
- Detect state corruption vulnerabilities
- Test boundary conditions

### Bead Type

`break_analysis`

### Attack Categories

| Category | Description | Examples |
|----------|-------------|----------|
| Boundary | Boundary value errors | Off-by-one, MAX_INT, empty input |
| Type Confusion | Type handling issues | Unicode, numeric strings, NaN |
| Concurrency | Race conditions | TOCTOU, double-submit, lost updates |
| State | State machine issues | Wrong order, partial completion |
| Resource | Resource exhaustion | Memory, connections, file handles |

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | str | Code to analyse |
| `file_path` | str | Path to file |
| `function_name` | str | Specific function |
| `language` | str | Programming language |
| `attack_hints` | list | Suggested attack vectors |
| `focus_areas` | list | Areas to focus on |
| `code_context` | dict | Dependencies, async, state info |

### Output Schema

```python
{
    "target": {
        "file_path": "src/cart.py",
        "function_name": "add_item",
        "code_analyzed": "Shopping cart item addition",
    },
    "findings": [
        {
            "id": "BREAK-001",
            "title": "Negative quantity allows price bypass",
            "severity": "HIGH",
            "category": "boundary",  # boundary, concurrency, state, resource, type_confusion
            "confidence": 0.9,
            "description": "No validation on quantity allows negative values",
            "attack_vector": "Submit negative quantity to get credit",
            "proof_of_concept": {
                "description": "Add item with negative quantity",
                "code": "cart.add_item(product_id='123', quantity=-5)",
                "expected_behavior": "Reject negative quantity",
                "vulnerable_behavior": "Subtracts from total price",
            },
            "impact": "Financial loss through price manipulation",
            "remediation": {
                "immediate": "Add quantity validation",
                "proper": "Use unsigned integers for quantities",
                "code_example": "if quantity <= 0: raise ValueError('Invalid quantity')",
            },
            "line_numbers": [42, 43],
        }
    ],
    "attack_vectors_tried": [
        "Negative values",
        "Zero values",
        "MAX_INT overflow",
        "Empty strings",
    ],
    "code_quality_observations": [
        "No input validation pattern",
        "Missing type hints",
    ],
    "confidence": 0.85,
    "assumptions": [],
    "unknowns": [],
}
```

---

## ChaosAgent

The ChaosAgent tests system resilience through chaos engineering experiments.

### Purpose

- Design chaos experiments
- Identify resilience gaps
- Test failure handling
- Verify fallback behaviour

### Bead Type

`chaos_analysis`

### Experiment Categories

| Category | Description | Examples |
|----------|-------------|----------|
| Dependency Failure | External system failures | Database down, API timeout |
| Network Chaos | Network issues | Latency, packet loss, partition |
| Resource Pressure | Resource exhaustion | Memory, CPU, connections |
| Time Chaos | Time-related issues | Clock skew, timezone |
| State Chaos | Data corruption | Corrupt cache, duplicates |

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | str | Code to analyse |
| `file_path` | str | Path to file |
| `function_name` | str | Specific function |
| `language` | str | Programming language |
| `infrastructure_context` | dict | Database, cache, API info |

### Output Schema

```python
{
    "target": {
        "file_path": "src/services/user_service.py",
        "function_name": "get_user",
        "code_analyzed": "User lookup with caching",
    },
    "dependencies_detected": [
        {
            "name": "PostgreSQL Database",
            "type": "database",  # database, cache, api, filesystem, queue
            "evidence": ["psycopg2.connect()", "cursor.execute()"],
            "criticality": "critical",  # critical, important, optional
        }
    ],
    "resilience_analysis": {
        "has_timeouts": True,
        "has_retries": False,
        "has_circuit_breaker": False,
        "has_fallbacks": True,
        "has_health_checks": False,
        "overall_resilience_score": 40,  # 0-100
    },
    "experiments": [
        {
            "id": "CHAOS-001",
            "title": "Database connection timeout",
            "category": "dependency_failure",
            "target_dependency": "PostgreSQL Database",
            "failure_mode": "timeout",  # unavailable, timeout, slow, error, corrupt
            "severity_if_vulnerable": "HIGH",
            "experiment": {
                "description": "Add 10s latency to database connections",
                "method": "Use toxiproxy to add latency",
                "duration_seconds": 60,
                "safe_to_automate": False,
                "requires_isolation": True,
                "rollback": "Remove toxiproxy proxy",
            },
            "hypothesis": {
                "expected_resilient_behavior": "Return cached data or graceful error",
                "predicted_actual_behavior": "Request hangs indefinitely",
                "prediction_confidence": 0.8,
            },
            "evidence": {
                "code_location": "user_service.py:42",
                "problematic_code": "No timeout on connection",
                "missing_patterns": ["connection timeout", "circuit breaker"],
            },
            "remediation": {
                "immediate": "Add connection timeout",
                "proper": "Implement circuit breaker pattern",
                "code_example": "conn = connect(timeout=5)",
            },
        }
    ],
    "confidence": 0.75,
    "assumptions": ["No existing chaos testing"],
    "unknowns": ["Infrastructure configuration"],
}
```

---

## CryptoAgent

The CryptoAgent finds cryptographic and authentication-related weaknesses.

### Purpose

- Identify weak cryptographic algorithms
- Find hardcoded secrets
- Detect insecure randomness
- Analyse token/JWT handling

### Bead Type

`crypto_analysis`

### Detection Categories

| Category | Examples |
|----------|----------|
| Weak Algorithms | MD5, SHA1 for passwords, DES, RC4 |
| Hardcoded Secrets | API keys, passwords in code |
| Insecure Randomness | `random()` for tokens |
| JWT Issues | Algorithm confusion, weak secrets |
| Key Management | Weak key generation, exposed keys |

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `code` | str | Code to analyse |
| `file_path` | str | Path to file |
| `function_name` | str | Specific function |
| `language` | str | Programming language |
| `exposure` | str | Exposure level |

### Output Schema

```python
{
    "target": {
        "file_path": "src/auth/password.py",
        "function_name": "hash_password",
        "exposure": "internal",
    },
    "findings": [
        {
            "id": "CRYPTO-001",
            "title": "Weak hashing for passwords",
            "severity": "HIGH",
            "cwe_id": "CWE-327",
            "confidence": 0.95,
            "description": "MD5 used for password hashing",
            "evidence": {
                "file": "src/auth/password.py",
                "line_start": 10,
                "line_end": 12,
                "snippet": "hashlib.md5(password.encode()).hexdigest()",
            },
            "attack": {
                "description": "Rainbow table attack",
                "prerequisites": ["Access to hashed passwords"],
                "impact": "Password recovery in seconds",
            },
            "remediation": {
                "immediate": "Switch to bcrypt",
                "code_fix": "bcrypt.hashpw(password.encode(), bcrypt.gensalt())",
                "defense_in_depth": ["Add pepper", "Enforce strong passwords"],
            },
        }
    ],
    "confidence": 0.9,
    "assumptions": [],
    "unknowns": [],
}
```

---

## CrossExaminationAgent

The CrossExaminationAgent challenges findings from attack agents to reduce false positives.

### Purpose

- Validate findings from attack agents
- Challenge assumptions
- Identify false positives
- Adjust confidence levels

### Bead Type

`cross_examination`

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `findings` | list | Findings to examine |
| `code` | str | Original code |
| `code_context` | dict | Additional context |

### Output Schema

```python
{
    "examined_findings": [
        {
            "original_id": "EXPLOIT-001",
            "original_agent": "ExploitAgent",
            "validation_status": "CONFIRMED",  # CONFIRMED, LIKELY, UNLIKELY, REJECTED
            "adjusted_confidence": 0.85,
            "examination_notes": "Verified SQL injection is exploitable",
            "counter_arguments": [],
            "supporting_evidence": ["No parameterised queries", "User input reaches query"],
            "recommended_action": "BLOCK",
        },
        {
            "original_id": "BREAK-002",
            "original_agent": "BreakAgent",
            "validation_status": "REJECTED",
            "adjusted_confidence": 0.1,
            "examination_notes": "Edge case cannot occur in practice",
            "counter_arguments": ["Input is validated upstream"],
            "supporting_evidence": [],
            "recommended_action": "DISMISS",
        }
    ],
    "summary": {
        "confirmed": 3,
        "likely": 1,
        "unlikely": 1,
        "rejected": 2,
    },
    "confidence": 0.8,
}
```

---

## Arbiter

The Arbiter is the final judge that renders verdicts on all findings.

### Purpose

- Review all findings
- Make final decisions
- Create remediation tasks
- Render BLOCK/WARN/PASS verdict

### Bead Type

`arbiter_verdict`

### Verdict Decisions

| Verdict | Criteria |
|---------|----------|
| **BLOCK** | Definitely exploitable, significant impact, cannot ship |
| **WARN** | Real but mitigated, requires conditions, track but ship |
| **PASS** | False positive, theoretical, already mitigated |

### Input Context

| Field | Type | Description |
|-------|------|-------------|
| `findings` | list | All findings from agents |
| `cross_examination` | dict | Cross-examination results |
| `code_context` | dict | Code and environment context |

### Output Schema

```python
{
    "decision": "WARN",  # BLOCK, WARN, PASS
    "decision_rationale": "Issues found but have mitigations",
    "blocking_issues": [],
    "warnings": [
        {
            "original_id": "EXPLOIT-001",
            "original_agent": "ExploitAgent",
            "original_title": "SQL Injection",
            "original_severity": "CRITICAL",
            "validation_status": "CONFIRMED",
            "validated_severity": "HIGH",  # May differ from original
            "adjusted_severity_reason": "Behind WAF and auth",
            "exploitation_difficulty": "MODERATE",  # TRIVIAL, EASY, MODERATE, DIFFICULT, THEORETICAL
            "exploitation_prerequisites": ["Authenticated", "Bypass WAF"],
            "real_world_exploitability": 0.5,
            "impact_description": "Database access if exploited",
            "affected_components": ["user_service"],
            "data_at_risk": ["user_emails"],
            "remediation_effort": "HOURS",  # MINUTES, HOURS, DAYS, WEEKS
            "suggested_fix": "Use parameterised queries",
            "fix_code_example": "cursor.execute('...', (param,))",
            "workaround": "Strengthen WAF rules",
            "confidence": 0.85,
        }
    ],
    "passed_findings": [],
    "false_positives": [
        {
            "original_id": "BREAK-003",
            "original_agent": "BreakAgent",
            "original_title": "Integer overflow",
            "original_severity": "MEDIUM",
            "rejection_reason": "Counter reset daily, cannot overflow",
            "rejection_category": "false_positive",
            "evidence": "Max daily value is 10K, overflow at 2B",
        }
    ],
    "remediation_tasks": [
        {
            "finding_id": "EXPLOIT-001",
            "title": "Fix SQL injection",
            "description": "Replace string concat with parameters",
            "priority": "HIGH",  # CRITICAL, HIGH, MEDIUM, LOW
            "estimated_effort": "HOURS",
            "fix_guidance": "Step-by-step instructions",
            "acceptance_criteria": ["Uses parameterised queries"],
        }
    ],
    "summary": "One high severity issue requiring attention",
    "key_concerns": ["SQL injection in user service"],
    "recommendations": ["Review all database queries"],
    "confidence": 0.85,
    "assumptions": [],
    "limitations": ["Could not test runtime behaviour"],
}
```

---

## Base Agent Class

All agents inherit from the `Agent` base class:

```python
from adversarial_debate.agents import Agent, AgentContext, AgentOutput

class Agent(ABC):
    """Base class for all agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        ...

    @property
    @abstractmethod
    def bead_type(self) -> BeadType:
        """Type of bead this agent produces."""
        ...

    @property
    def model_tier(self) -> ModelTier:
        """Model tier for this agent."""
        return ModelTier.HOSTED_SMALL

    @abstractmethod
    def _build_prompt(self, context: AgentContext) -> list[Message]:
        """Build prompt messages."""
        ...

    @abstractmethod
    def _parse_response(self, response: str, context: AgentContext) -> AgentOutput:
        """Parse LLM response."""
        ...

    async def run(self, context: AgentContext) -> AgentOutput:
        """Execute the agent."""
        ...
```

### AgentContext

```python
@dataclass
class AgentContext:
    run_id: str                    # Run identifier
    timestamp_iso: str             # ISO timestamp
    policy: dict[str, Any]         # Policy constraints
    thread_id: str                 # Bead thread ID
    task_id: str = ""              # Task identifier
    parent_bead_id: str = ""       # Parent bead
    recent_beads: list[Bead] = []  # Recent context
    inputs: dict[str, Any] = {}    # Agent-specific inputs
    repo_files: dict[str, str] = {}  # File contents
```

### AgentOutput

```python
@dataclass
class AgentOutput:
    agent_name: str            # Agent identifier
    result: dict[str, Any]     # Agent-specific output
    beads_out: list[Bead]      # Beads to emit
    confidence: float          # Confidence 0.0-1.0
    assumptions: list[str] = []  # Assumptions made
    unknowns: list[str] = []   # Unknown factors
    errors: list[str] = []     # Any errors

    @property
    def success(self) -> bool:
        return len(self.errors) == 0
```

## See Also

- [Extending Agents](../developers/extending-agents.md) — Creating custom agents
- [Attack Coverage](../concepts/attack-coverage.md) — Vulnerability coverage
- [Data Structures](data-structures.md) — Type definitions
- [Architecture](architecture.md) — System design
