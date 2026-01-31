# Glossary

Key terms used in Adversarial Debate documentation.

---

## A

### Agent
A specialised AI component that analyses code from a specific perspective. Each agent has a defined role (security, logic, resilience) and produces structured findings.

### AgentContext
The input data passed to an agent for analysis, including the code to examine, policy constraints, and bead history.

### AgentOutput
The structured result returned by an agent after analysis, containing findings, beads to emit, and confidence scores.

### Arbiter
The final decision-making agent that reviews all findings from attack agents and renders a verdict (BLOCK, WARN, or PASS).

### Artefact
A reference to an external object (file, commit, PR) associated with a bead, providing traceability.

### Attack Plan
A structured document created by the ChaosOrchestrator that assigns analysis work to agents with priorities, dependencies, and parallelisation guidance.

### Attack Surface
The total set of points where untrusted input could enter a system, representing potential vulnerability locations.

### Attack Vector
A specific method or approach for exploiting a vulnerability, such as SQL injection or path traversal.

---

## B

### Baseline
A saved bundle of findings from a previous analysis run, used for comparison to detect new issues or regressions.

### Bead
The atomic unit of the event sourcing system—an immutable record of an agent action or decision stored in the ledger.

### BeadStore
The append-only JSONL storage system for beads, providing the audit trail and coordination mechanism.

### BeadType
The category of a bead, indicating what kind of event it represents (e.g., `attack_plan`, `exploit_analysis`, `arbiter_verdict`).

### BLOCK
A verdict indicating critical issues that must be fixed before the code can ship. The most severe verdict.

### BreakAgent
An agent specialised in finding logic bugs, edge cases, race conditions, and state corruption issues.

### Bundle
The complete output of an analysis run, containing metadata, findings, verdict, and attack plan in a structured JSON format.

---

## C

### ChaosAgent
An agent that designs chaos engineering experiments to test system resilience against infrastructure failures.

### ChaosOrchestrator
The coordinating agent that analyses code, assesses risk, and creates attack plans assigning work to other agents.

### Confidence
A numerical score (0.0-1.0) indicating certainty in a finding or verdict. Higher values indicate stronger evidence.

### Cross-Examination
The process where the CrossExaminationAgent challenges findings from attack agents to reduce false positives.

### CrossExaminationAgent
An agent that validates findings by examining evidence, checking assumptions, and identifying potential false positives.

### CryptoAgent
An agent specialised in finding cryptographic weaknesses, including weak algorithms, hardcoded secrets, and JWT issues.

### CWE
Common Weakness Enumeration—a standardised list of software security weaknesses used to categorise vulnerabilities.

---

## D

### Dry Run
An execution mode that simulates analysis without making actual API calls or writing output.

---

## E

### Event Sourcing
An architectural pattern where system state is captured as a sequence of immutable events (beads) rather than current state.

### ExploitAgent
An agent specialised in finding security vulnerabilities based on OWASP Top 10 categories, generating working exploit payloads.

### Exploitation Difficulty
A rating of how hard it is to exploit a vulnerability: TRIVIAL, EASY, MODERATE, DIFFICULT, or THEORETICAL.

---

## F

### False Positive
A reported finding that, upon examination, is not actually a real vulnerability or bug.

### Finding
A specific security issue, bug, or concern identified by an agent during analysis.

### Formatter
A component that transforms the results bundle into a specific output format (JSON, SARIF, HTML, Markdown).

---

## G

### Git Integration
The ability to use git to identify changed files for incremental analysis.

---

## H

### Hint
Guidance provided by the ChaosOrchestrator to attack agents, suggesting what to look for in specific code.

---

## I

### Idempotency Key
A unique identifier ensuring an operation is only performed once, preventing duplicate beads on retry.

### IDOR
Insecure Direct Object Reference—a vulnerability where users can access objects (files, records) they shouldn't by manipulating identifiers.

---

## L

### Ledger
The append-only JSONL file (`beads/ledger.jsonl`) that stores all beads in the event sourcing system.

### LLM
Large Language Model—the AI models (Claude, GPT, etc.) that power the agents' analysis capabilities.

---

## M

### Mock Provider
A testing provider that returns predefined responses without making actual API calls.

### Model Tier
A classification of LLM models by capability: `HOSTED_SMALL` (fast/cheap), `HOSTED_LARGE` (powerful), `LOCAL` (self-hosted).

---

## O

### OWASP Top 10
The Open Web Application Security Project's list of the ten most critical web application security risks.

---

## P

### Parallel Group
A set of attacks that can execute concurrently because they have no dependencies on each other.

### PASS
A verdict indicating no actionable security or quality issues were found.

### Payload
Actual exploit code or input that demonstrates a vulnerability is real and exploitable.

### Pipeline
The sequence of stages in an analysis: orchestration → agent analysis → cross-examination → verdict.

### Proof of Concept (PoC)
Demonstration code that shows how a vulnerability can be exploited.

### Provider
An implementation of the LLM interface for a specific service (Anthropic, OpenAI, Azure, Ollama).

---

## R

### Remediation
The fix or mitigation for a security finding, including suggested code changes.

### Remediation Effort
An estimate of how long a fix will take: MINUTES, HOURS, DAYS, or WEEKS.

### Risk Level
The overall risk assessment for a codebase or file: LOW, MEDIUM, HIGH, or CRITICAL.

### Risk Score
A numerical rating (0-100) of how risky a file or codebase is based on various factors.

---

## S

### Sandbox
A secure, isolated Docker container where generated payloads can be safely executed without risking the host system.

### SARIF
Static Analysis Results Interchange Format—a standardised JSON format for security tool output, supported by many IDEs.

### Severity
The impact level of a finding: CRITICAL, HIGH, MEDIUM, or LOW.

### Skip Reason
Documentation of why a potential target was not assigned to any agent for analysis.

### SSRF
Server-Side Request Forgery—a vulnerability where an attacker can make the server send requests to unintended locations.

### Suppression
A rule that prevents certain findings from being reported, typically for accepted risks or known false positives.

---

## T

### Thread ID
An identifier linking related beads together, typically corresponding to a single analysis run.

### Trust Boundary
A conceptual border between zones of different trust levels, such as between user input and system internals.

---

## V

### Validated Finding
A finding that has been reviewed and confirmed (or adjusted) by the Arbiter.

### Verdict
The final decision on code quality: BLOCK (must fix), WARN (should fix), or PASS (acceptable).

### VerdictDecision
The enum type representing possible verdicts: BLOCK, WARN, or PASS.

---

## W

### WARN
A verdict indicating issues that should be fixed but don't block shipping. Less severe than BLOCK.

### Watch Mode
A continuous analysis mode that monitors files for changes and re-analyses automatically.

---

## X

### XSS
Cross-Site Scripting—a vulnerability where attackers can inject malicious scripts into web pages viewed by other users.

---

## See Also

- [FAQ](faq.md) — Common questions
- [How It Works](../concepts/how-it-works.md) — System overview
- [Attack Coverage](../concepts/attack-coverage.md) — What's detected
