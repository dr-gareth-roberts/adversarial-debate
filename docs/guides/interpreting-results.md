# Interpreting Results

This guide explains how to read and understand the findings, verdicts, and recommendations produced by Adversarial Debate.

## Understanding Verdicts

The Arbiter renders one of three verdicts:

| Verdict | Meaning | Action |
|---------|---------|--------|
| **BLOCK** | Critical or high-severity issues found | Must fix before deployment |
| **WARN** | Moderate issues or uncertain findings | Track and address in follow-up |
| **PASS** | No significant security concerns | Safe to proceed |

### Verdict Rationale

Each verdict includes a rationale explaining the decision:

```json
{
  "decision": "BLOCK",
  "decision_rationale": "Critical SQL injection vulnerability in public API endpoint requires immediate remediation before deployment."
}
```

## Understanding Findings

Each finding contains several key pieces of information.

### Finding Structure

```json
{
  "finding_id": "EXP-001",
  "title": "SQL injection in user lookup",
  "severity": "CRITICAL",
  "owasp_category": "A03:2021",
  "cwe_id": "CWE-89",
  "description": "User input is directly concatenated into SQL query without sanitisation",
  "vulnerable_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
  "location": {
    "file": "src/api/users.py",
    "line": 42,
    "function": "get_user"
  },
  "exploit_payload": "1 OR 1=1; DROP TABLE users;--",
  "proof_of_concept": "curl 'http://localhost:5000/user?id=1%20OR%201=1'",
  "impact": "Full database access, data exfiltration, data destruction",
  "remediation": "Use parameterised queries or an ORM",
  "confidence": 0.95
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `finding_id` | Unique identifier for tracking |
| `title` | Brief description of the issue |
| `severity` | CRITICAL, HIGH, MEDIUM, LOW, or INFO |
| `owasp_category` | OWASP Top 10 classification |
| `cwe_id` | Common Weakness Enumeration ID |
| `location` | Exact file, line, and function |
| `exploit_payload` | Example attack input |
| `proof_of_concept` | Command to demonstrate the issue |
| `impact` | What an attacker could achieve |
| `remediation` | How to fix the issue |
| `confidence` | Agent's confidence (0.0-1.0) |

## Severity Levels

### CRITICAL

**Meaning:** Easily exploitable, severe impact. Requires immediate attention.

**Examples:**
- Remote code execution
- SQL injection in public endpoints
- Authentication bypass
- Exposed credentials

**Action:** Stop deployment. Fix immediately.

### HIGH

**Meaning:** Exploitable with moderate effort, significant impact.

**Examples:**
- Stored XSS
- Privilege escalation
- Insecure direct object references
- Weak cryptography

**Action:** Fix before next release.

### MEDIUM

**Meaning:** Harder to exploit or moderate impact.

**Examples:**
- Reflected XSS
- Information disclosure
- Missing rate limiting
- CSRF vulnerabilities

**Action:** Include in next sprint.

### LOW

**Meaning:** Difficult to exploit or minimal impact.

**Examples:**
- Missing security headers
- Verbose error messages
- Outdated dependencies (no known exploits)

**Action:** Track for future fix.

### INFO

**Meaning:** Best practice recommendation, not a vulnerability.

**Examples:**
- Missing HTTPS redirect
- Suboptimal configuration
- Code quality suggestions

**Action:** Consider addressing.

## Exploitation Difficulty

The Arbiter assesses how hard a vulnerability is to exploit:

| Difficulty | Meaning | Typical Attacker |
|------------|---------|------------------|
| **TRIVIAL** | Public tools exist; script kiddie can exploit | Automated scanners |
| **EASY** | Basic security knowledge required | Junior attacker |
| **MODERATE** | Intermediate skills needed | Experienced attacker |
| **DIFFICULT** | Expert knowledge required | Security researcher |
| **THEORETICAL** | Requires ideal conditions rarely met | Nation-state |

## Confidence Scores

Agents report their confidence in each finding:

| Range | Interpretation |
|-------|----------------|
| 0.9-1.0 | Very confident; likely true positive |
| 0.7-0.9 | Confident; worth investigating |
| 0.5-0.7 | Moderate; may be false positive |
| Below 0.5 | Low confidence; verify manually |

**Example:**

```json
{
  "finding_id": "EXP-001",
  "confidence": 0.95  // Very confident
}
```

## OWASP Categories

Findings are mapped to OWASP Top 10 2021:

| Category | Code | Description |
|----------|------|-------------|
| Broken Access Control | A01:2021 | Authorisation failures |
| Cryptographic Failures | A02:2021 | Weak encryption/hashing |
| Injection | A03:2021 | SQL, command, XSS |
| Insecure Design | A04:2021 | Architectural flaws |
| Security Misconfiguration | A05:2021 | Improper settings |
| Vulnerable Components | A06:2021 | Outdated dependencies |
| Authentication Failures | A07:2021 | Broken auth |
| Data Integrity Failures | A08:2021 | Untrusted data |
| Logging Failures | A09:2021 | Missing audit |
| SSRF | A10:2021 | Server-side request forgery |

## Agent-Specific Findings

### ExploitAgent Findings

Focus on security vulnerabilities:
- SQL injection, command injection, XSS
- Authentication and authorisation issues
- Cryptographic weaknesses
- SSRF, CSRF, path traversal

**Key fields:** `owasp_category`, `cwe_id`, `exploit_payload`

### BreakAgent Findings

Focus on logic bugs:
- Boundary conditions (off-by-one, overflow)
- Race conditions and concurrency issues
- State machine violations
- Type confusion

**Key fields:** `category`, `trigger_condition`, `expected_behavior`, `actual_behavior`

### ChaosAgent Findings

Focus on resilience issues:
- Missing error handling
- Resource exhaustion risks
- Failure mode analysis
- Recovery gaps

**Key fields:** `experiment_id`, `hypothesis`, `blast_radius`, `safety_checks`

### CryptoAgent Findings

Focus on cryptographic issues:
- Weak algorithms
- Hardcoded keys/secrets
- Predictable randomness
- Token/JWT vulnerabilities

**Key fields:** `crypto_issue_type`, `affected_algorithm`, `recommended_replacement`

## Validated vs Rejected Findings

The Arbiter categorises findings:

### Validated Findings

Confirmed as real issues:

```json
{
  "validation_status": "CONFIRMED",
  "validated_severity": "CRITICAL",
  "exploitation_difficulty": "TRIVIAL",
  "real_world_exploitability": 0.95
}
```

### Rejected Findings

Determined to be false positives:

```json
{
  "rejection_reason": "Input is validated by middleware before reaching this code",
  "rejection_category": "NOT_EXPLOITABLE",
  "evidence": "See validation in middleware.py:45"
}
```

**Rejection categories:**
- `NOT_EXPLOITABLE` — Cannot be exploited in practice
- `FALSE_POSITIVE` — Incorrect detection
- `OUT_OF_SCOPE` — Not relevant to this analysis
- `DUPLICATE` — Same as another finding
- `MITIGATED` — Already has sufficient mitigation

## Remediation Tasks

The Arbiter creates actionable tasks:

```json
{
  "finding_id": "EXP-001",
  "title": "Fix SQL injection in user lookup",
  "priority": "CRITICAL",
  "estimated_effort": "HOURS",
  "fix_guidance": "Replace string concatenation with parameterised query",
  "fix_code_example": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
  "acceptance_criteria": [
    "No string concatenation in SQL queries",
    "All user input sanitised",
    "SQL injection test suite passes"
  ]
}
```

### Effort Estimates

| Effort | Meaning |
|--------|---------|
| MINUTES | Less than 30 minutes |
| HOURS | 30 minutes to 8 hours |
| DAYS | 1-5 days |
| WEEKS | More than 1 week |

## Working with Results

### Prioritising Fixes

1. **Start with blocking issues** — These prevent deployment
2. **Address by severity** — CRITICAL before HIGH before MEDIUM
3. **Consider confidence** — High-confidence findings first
4. **Check exploitation difficulty** — TRIVIAL issues are most urgent

### Verifying Fixes

After applying fixes:

```bash
# Re-run analysis
adversarial-debate run src/ --output results-v2/

# Compare with baseline
adversarial-debate run src/ --baseline results/bundle.json
```

### Tracking Progress

Use the bundle file to track resolution:

```python
import json

bundle = json.loads(open("bundle.json").read())
blocking = len(bundle["verdict"]["blocking_issues"])
warnings = len(bundle["verdict"]["warnings"])

print(f"Blocking: {blocking}, Warnings: {warnings}")
```

## Common Scenarios

### "I think this is a false positive"

1. Check the `location` — is this the right code?
2. Review the `description` — does the issue exist?
3. Look for mitigations — is input validated elsewhere?
4. Check `confidence` — low confidence suggests uncertainty

If it's truly a false positive, document it for baseline suppression.

### "The severity seems wrong"

The Arbiter may adjust severity based on context:
- `adjusted_severity_reason` explains changes
- Original severity is in `original_severity`
- Consider your threat model

### "I don't understand the remediation"

1. Check `fix_guidance` for steps
2. Look at `fix_code_example` for reference
3. Search for the CWE ID for more information
4. Consult OWASP guidance for the category

## See Also

- [Output Formats](output-formats.md) — Understanding output files
- [Attack Coverage](../concepts/attack-coverage.md) — What each agent detects
- [Troubleshooting](../support/troubleshooting.md) — Common issues
