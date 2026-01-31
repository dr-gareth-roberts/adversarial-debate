# How It Works

This guide explains the conceptual model of Adversarial Debate: how the multi-agent system analyses code and produces security assessments.

## The Core Idea

Adversarial Debate simulates a team of security experts reviewing your code. Each expert has a different specialisation:

- **Security Expert** (ExploitAgent) — Looks for OWASP vulnerabilities
- **Quality Analyst** (BreakAgent) — Finds logic bugs and edge cases
- **SRE** (ChaosAgent) — Identifies resilience issues
- **Cryptographer** (CryptoAgent) — Spots cryptographic weaknesses
- **Senior Reviewer** (Arbiter) — Makes the final call

A strategic planner (ChaosOrchestrator) coordinates their efforts, and the Arbiter consolidates findings into an actionable verdict.

## The Pipeline

Every analysis follows this pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR CODE                                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STAGE 1: ORCHESTRATE                           │
│                                                                  │
│  ChaosOrchestrator examines code and creates an attack plan:    │
│  • Identifies high-risk areas                                    │
│  • Assigns specialists to specific targets                       │
│  • Prioritises based on risk                                     │
│                                                                  │
│  Output: attack_plan.json                                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 2: ANALYSE                              │
│                                                                  │
│  Specialist agents run in parallel:                              │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐│
│  │ ExploitAgent │ │  BreakAgent  │ │  ChaosAgent  │ │CryptoAgent│
│  │              │ │              │ │              │ │          ││
│  │ SQL Inject   │ │ Off-by-one   │ │ Missing      │ │ Weak     ││
│  │ XSS          │ │ Race conds   │ │ timeouts     │ │ hashing  ││
│  │ Auth bypass  │ │ State bugs   │ │ No fallback  │ │ Bad keys ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘│
│                                                                  │
│  Output: *_findings.json                                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 STAGE 3: CROSS-EXAMINE (Optional)                │
│                                                                  │
│  CrossExaminationAgent debates conflicting findings:             │
│  • Resolves duplicates                                           │
│  • Validates exploitability claims                               │
│  • Produces consensus findings                                   │
│                                                                  │
│  Output: findings.debated.json                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 4: VERDICT                              │
│                                                                  │
│  Arbiter reviews all findings and renders verdict:               │
│  • Validates each finding in context                             │
│  • Assesses real-world exploitability                            │
│  • Determines BLOCK / WARN / PASS                                │
│  • Creates remediation tasks                                     │
│                                                                  │
│  Output: verdict.json                                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FINAL RESULT                               │
│                                                                  │
│  Verdict: BLOCK                                                  │
│  Blocking Issues: 2                                              │
│  Remediation Tasks: 2                                            │
│                                                                  │
│  Output: bundle.json (canonical results)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Stage 1: Orchestration

The ChaosOrchestrator acts as the strategic planner. Given your code, it:

1. **Analyses risk factors**
   - Public endpoints vs. internal code
   - Data sensitivity (PII, credentials, financial)
   - Historical issues in similar areas

2. **Creates attack assignments**
   - Which agent should examine which file
   - What attack vectors to prioritise
   - How much time to allocate

3. **Optimises execution**
   - Groups independent attacks for parallelism
   - Orders attacks by priority
   - Respects time budgets

**Example attack plan:**

```json
{
  "risk_level": "HIGH",
  "risk_factors": [
    "Public API endpoint",
    "SQL query construction",
    "No input validation visible"
  ],
  "attacks": [
    {
      "id": "ATK-001",
      "agent": "EXPLOIT_AGENT",
      "target_file": "src/api/users.py",
      "priority": "CRITICAL",
      "attack_vectors": ["SQL Injection", "IDOR"]
    }
  ]
}
```

## Stage 2: Analysis

Specialist agents run their analyses, each focusing on their domain.

### ExploitAgent

Thinks like an attacker. Looks for:
- OWASP Top 10 vulnerabilities
- Working exploit payloads
- Proof-of-concept attacks

**Approach:** "How can I compromise this system?"

### BreakAgent

Thinks like a chaos engineer. Looks for:
- Edge cases and boundary conditions
- Race conditions and concurrency bugs
- Invalid state transitions

**Approach:** "What inputs will break this code?"

### ChaosAgent

Thinks like a site reliability engineer. Looks for:
- Missing error handling
- Resource exhaustion risks
- Failure recovery gaps

**Approach:** "What happens when things go wrong?"

### CryptoAgent

Thinks like a cryptographer. Looks for:
- Weak or outdated algorithms
- Improper key management
- Predictable randomness

**Approach:** "Is the cryptography sound?"

## Stage 3: Cross-Examination

When enabled, the CrossExaminationAgent acts as a debate moderator:

1. **Collects all findings** from specialist agents
2. **Identifies conflicts** — similar findings from different agents
3. **Debates** — challenges and validates each claim
4. **Produces consensus** — merged, deduplicated findings

This reduces false positives and improves accuracy.

## Stage 4: Verdict

The Arbiter is the senior reviewer making the final call:

1. **Reviews each finding** in context of the full codebase
2. **Validates exploitability** — can this actually be exploited?
3. **Considers mitigations** — are there security controls elsewhere?
4. **Adjusts severity** — based on real-world impact
5. **Renders verdict** — BLOCK, WARN, or PASS
6. **Creates tasks** — actionable remediation steps

**Example verdict:**

```json
{
  "decision": "BLOCK",
  "decision_rationale": "Critical SQL injection requires immediate fix",
  "blocking_issues": [
    {
      "title": "SQL injection in user lookup",
      "validated_severity": "CRITICAL",
      "exploitation_difficulty": "TRIVIAL"
    }
  ],
  "remediation_tasks": [
    {
      "title": "Fix SQL injection",
      "priority": "CRITICAL",
      "estimated_effort": "HOURS"
    }
  ]
}
```

## Event Sourcing

Every action in the pipeline produces an immutable record called a "bead". These beads form an audit trail:

```
Thread: security-audit-001
│
├── ATTACK_PLAN (ChaosOrchestrator)
│   ├── EXPLOIT_ANALYSIS (ExploitAgent)
│   ├── BREAK_ANALYSIS (BreakAgent)
│   ├── CHAOS_ANALYSIS (ChaosAgent)
│   ├── CRYPTO_ANALYSIS (CryptoAgent)
│   └── ARBITER_VERDICT (Arbiter)
```

This enables:
- **Auditability** — Complete record of what was analysed
- **Reproducibility** — Re-run from any point
- **Debugging** — Trace how conclusions were reached

## Key Design Principles

### Stateless Agents

Agents are pure functions: they receive context and produce output without maintaining internal state. This enables:
- Parallel execution
- Easy testing
- Reproducible results

### Separation of Concerns

Each agent focuses on one type of analysis. This allows:
- Deep expertise in each domain
- Independent evolution
- Easy addition of new agents

### Structured Output

All agents produce JSON-formatted findings with consistent schemas. This enables:
- Automated processing
- CI/CD integration
- Trend analysis

### Defence in Depth

Multiple security measures:
- Sandbox isolation for code execution
- Input validation at all boundaries
- Idempotency for safe retries

## Comparison to Traditional Tools

| Aspect | Adversarial Debate | Traditional SAST |
|--------|-------------------|------------------|
| Detection method | LLM reasoning | Pattern matching |
| Context awareness | High | Low |
| False positive rate | Lower | Higher |
| Novel vulnerabilities | Can detect | Often misses |
| Speed | Slower | Faster |
| Remediation guidance | Detailed | Generic |

## When to Use Which Mode

### Full Pipeline (`run`)

Use for:
- Pre-deployment security review
- Pull request analysis
- Comprehensive audits

### Single Agent (`analyze`)

Use for:
- Targeted analysis
- Quick checks during development
- Specific vulnerability types

### Orchestrate Only

Use for:
- Planning attack strategy
- Understanding risk profile
- Prioritising manual review

## See Also

- [Security Model](security-model.md) — Trust boundaries and sandbox
- [Attack Coverage](attack-coverage.md) — What each agent detects
- [Architecture](../reference/architecture.md) — Technical deep dive
