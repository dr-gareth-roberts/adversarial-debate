# Your First Analysis

This tutorial walks you through a complete security analysis, explaining each step and how to interpret the results.

## What We'll Cover

1. Understanding the analysis pipeline
2. Running a full security scan
3. Interpreting findings and verdicts
4. Taking action on results

## The Sample Application

We'll analyse a deliberately vulnerable Flask application included in the repository. This app contains common security issues for demonstration purposes.

```bash
# If you cloned from source
cd adversarial-debate
ls examples/mini-app/
```

The mini-app contains:
- `app.py` — A Flask application with SQL injection, command injection, and other vulnerabilities
- `requirements.txt` — Dependencies

**Warning:** This code is intentionally vulnerable. Never deploy it in production.

## Step 1: Run the Analysis

Let's run a full analysis pipeline:

```bash
# Using mock provider (no API key needed)
LLM_PROVIDER=mock adversarial-debate run examples/mini-app/ --output output

# Or with a real provider
ANTHROPIC_API_KEY=your-key adversarial-debate run examples/mini-app/ --output output
```

You'll see progress output as each stage completes:

```
[1/4] Orchestrating attack plan...
[2/4] Running ExploitAgent...
[2/4] Running BreakAgent...
[2/4] Running ChaosAgent...
[2/4] Running CryptoAgent...
[3/4] Running cross-examination...
[4/4] Rendering verdict...
```

## Step 2: Understanding the Pipeline

The analysis runs in four stages:

### Stage 1: Attack Planning (ChaosOrchestrator)

The orchestrator examines your code and creates an attack plan. It:
- Identifies high-risk areas (public endpoints, database access, authentication)
- Assigns specialised agents to specific files and functions
- Prioritises attacks based on risk factors

**Output:** `attack_plan.json`

### Stage 2: Red Team Analysis

Four specialised agents analyse the code in parallel:

| Agent | Focus | Example Findings |
|-------|-------|------------------|
| **ExploitAgent** | Security vulnerabilities | SQL injection, XSS, auth bypass |
| **BreakAgent** | Logic bugs | Integer overflow, race conditions |
| **ChaosAgent** | Resilience | Missing timeouts, resource exhaustion |
| **CryptoAgent** | Cryptographic issues | Weak hashing, hardcoded secrets |

**Outputs:** `exploit_findings.json`, `break_findings.json`, `chaos_findings.json`, `crypto_findings.json`

### Stage 3: Cross-Examination (Optional)

The CrossExaminationAgent debates conflicting findings, resolving duplicates and validating exploitability claims.

**Output:** `findings.debated.json` (if cross-examination produces changes)

### Stage 4: Verdict (Arbiter)

The Arbiter reviews all findings and renders a final verdict:
- **BLOCK** — Critical issues that must be fixed before deployment
- **WARN** — Issues to track and address in follow-up
- **PASS** — No significant security concerns

**Output:** `verdict.json`

## Step 3: Examining the Results

Navigate to your output directory:

```bash
cd output/run-*/
ls -la
```

### The Verdict

Open `verdict.json` to see the final decision:

```json
{
  "verdict_id": "VERDICT-20240115-143522",
  "decision": "BLOCK",
  "decision_rationale": "Critical SQL injection vulnerability requires immediate remediation",
  "blocking_issues": [
    {
      "original_id": "EXP-001",
      "original_title": "SQL injection in user lookup",
      "validated_severity": "CRITICAL",
      "exploitation_difficulty": "TRIVIAL",
      "impact_description": "Full database access, data exfiltration possible",
      "suggested_fix": "Use parameterised queries instead of string concatenation",
      "fix_code_example": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
    }
  ],
  "warnings": [...],
  "remediation_tasks": [...]
}
```

### Individual Agent Findings

Each agent produces detailed findings. Here's an example from `exploit_findings.json`:

```json
{
  "findings": [
    {
      "finding_id": "EXP-001",
      "title": "SQL injection in user lookup",
      "severity": "CRITICAL",
      "owasp_category": "A03:2021",
      "cwe_id": "CWE-89",
      "description": "User input is directly concatenated into SQL query without sanitisation",
      "vulnerable_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
      "location": {
        "file": "examples/mini-app/app.py",
        "line": 42,
        "function": "get_user"
      },
      "exploit_payload": "1 OR 1=1; DROP TABLE users;--",
      "proof_of_concept": "curl 'http://localhost:5000/user?id=1%20OR%201=1'",
      "impact": "Full database access, data exfiltration, data destruction",
      "remediation": "Use parameterised queries or an ORM",
      "confidence": 0.95
    }
  ]
}
```

### The Results Bundle

The `bundle.json` file contains a canonical representation of all results, suitable for:
- CI/CD integration
- Baseline comparison
- External tooling

## Step 4: Interpreting Severity

Findings are classified by severity:

| Severity | Meaning | Action |
|----------|---------|--------|
| **CRITICAL** | Easily exploitable, high impact | Fix immediately |
| **HIGH** | Exploitable, significant impact | Fix before deployment |
| **MEDIUM** | Harder to exploit or moderate impact | Fix in next sprint |
| **LOW** | Difficult to exploit or minimal impact | Track for future fix |
| **INFO** | Best practice suggestion | Consider addressing |

Exploitation difficulty is also assessed:

| Difficulty | Meaning |
|------------|---------|
| **TRIVIAL** | Script kiddie can exploit; public tools exist |
| **EASY** | Basic security knowledge required |
| **MODERATE** | Intermediate skills needed |
| **DIFFICULT** | Expert knowledge required |
| **THEORETICAL** | Requires ideal conditions |

## Step 5: Taking Action

### For Blocking Issues

1. **Read the finding details** — Understand what's vulnerable and why
2. **Check the location** — Go to the exact file and line number
3. **Review the suggested fix** — Most findings include remediation guidance
4. **Apply the fix** — Use parameterised queries, input validation, etc.
5. **Re-run the analysis** — Verify the fix resolved the issue

### For Warnings

1. **Create tracking tickets** — Don't lose track of these issues
2. **Prioritise based on context** — Consider your threat model
3. **Address in upcoming sprints** — Don't let them accumulate

### For the Audit Trail

All analysis actions are recorded in the bead ledger (`beads/ledger.jsonl`). This provides:
- Complete audit trail of all findings
- Reproducibility of analysis runs
- History for trend analysis

## Running Different Analyses

### Single Agent

Target a specific type of analysis:

```bash
# Only look for security vulnerabilities
adversarial-debate analyze exploit src/

# Only look for logic bugs
adversarial-debate analyze break src/

# Only look for resilience issues
adversarial-debate analyze chaos src/

# Only look for cryptographic issues
adversarial-debate analyze crypto src/
```

### Specific Files

Focus on particular files:

```bash
adversarial-debate analyze exploit src/api/auth.py src/api/users.py
```

### Skip the Verdict

If you only want agent findings without arbitration:

```bash
adversarial-debate run src/ --skip-verdict
```

### Different Output Formats

Generate reports in various formats:

```bash
# SARIF (for IDE integration)
adversarial-debate run src/ --format sarif --report-file findings.sarif

# HTML (for sharing)
adversarial-debate run src/ --format html --report-file report.html

# Markdown (for Git)
adversarial-debate run src/ --format markdown --report-file SECURITY.md
```

## Next Steps

- **[CLI Reference](../guides/cli-reference.md)** — Explore all commands and options
- **[Interpreting Results](../guides/interpreting-results.md)** — Deep dive into findings
- **[CI/CD Integration](../integration/ci-cd.md)** — Automate security checks
- **[Python API](../developers/python-api.md)** — Use the framework programmatically
