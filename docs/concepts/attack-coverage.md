# Attack Coverage

This guide details what vulnerabilities and issues each agent detects, mapped to industry standards.

## Coverage Overview

| Agent | Focus | Standards |
|-------|-------|-----------|
| ExploitAgent | Security vulnerabilities | OWASP Top 10, CWE |
| BreakAgent | Logic bugs | Bug taxonomies |
| ChaosAgent | Resilience issues | SRE practices |
| CryptoAgent | Cryptographic weaknesses | NIST, CWE |

## ExploitAgent Coverage

### OWASP Top 10 2021 Mapping

| Category | Coverage | Detection Examples |
|----------|----------|-------------------|
| **A01:2021 Broken Access Control** | ✓ Full | IDOR, missing authorisation, privilege escalation, path traversal |
| **A02:2021 Cryptographic Failures** | ✓ Full | Weak hashing, hardcoded secrets, insecure random |
| **A03:2021 Injection** | ✓ Full | SQL, command, XSS, LDAP, template injection |
| **A04:2021 Insecure Design** | ◐ Partial | Missing security controls, unsafe defaults |
| **A05:2021 Security Misconfiguration** | ✓ Full | Debug mode, permissive CORS, verbose errors |
| **A06:2021 Vulnerable Components** | ◐ Partial | Known CVEs in imports (limited) |
| **A07:2021 Authentication Failures** | ✓ Full | Weak passwords, session issues, credential stuffing |
| **A08:2021 Data Integrity Failures** | ✓ Full | Insecure deserialisation, unsigned data |
| **A09:2021 Logging Failures** | ◐ Partial | Missing audit logs, sensitive data in logs |
| **A10:2021 SSRF** | ✓ Full | Unvalidated URLs, internal service access |

### Detailed Detection Categories

#### Injection (A03:2021)

| Type | CWE | Detection |
|------|-----|-----------|
| SQL Injection | CWE-89 | String concatenation in queries, ORM misuse |
| Command Injection | CWE-78 | Shell commands with user input |
| Cross-Site Scripting | CWE-79 | Unescaped output, DOM manipulation |
| LDAP Injection | CWE-90 | LDAP queries with user input |
| XPath Injection | CWE-643 | XPath queries with user input |
| Template Injection | CWE-94 | User input in templates |
| Code Injection | CWE-94 | eval(), exec() with user input |

#### Broken Access Control (A01:2021)

| Type | CWE | Detection |
|------|-----|-----------|
| IDOR | CWE-639 | Direct object references without authorisation |
| Path Traversal | CWE-22 | ../../../ patterns in file paths |
| Privilege Escalation | CWE-269 | Role bypass, admin function access |
| CORS Misconfiguration | CWE-942 | Overly permissive Access-Control headers |
| Missing Function-Level Access | CWE-285 | Endpoints without authorisation checks |

#### Cryptographic Failures (A02:2021)

| Type | CWE | Detection |
|------|-----|-----------|
| Hardcoded Credentials | CWE-798 | Passwords, API keys in code |
| Weak Hashing | CWE-328 | MD5, SHA1 for passwords |
| Insecure Random | CWE-330 | random() for security purposes |
| Missing Encryption | CWE-311 | Sensitive data in plaintext |
| Weak TLS | CWE-326 | SSLv3, TLS 1.0 |

## BreakAgent Coverage

### Attack Taxonomy

| Category | Coverage | Detection Examples |
|----------|----------|-------------------|
| **Boundary** | ✓ Full | Off-by-one, integer overflow, empty collections |
| **Type Confusion** | ✓ Full | Null handling, type coercion, NaN |
| **Concurrency** | ✓ Full | Race conditions, deadlocks, TOCTOU |
| **State** | ✓ Full | Invalid transitions, use-after-free |
| **Resource** | ◐ Partial | Memory leaks, handle exhaustion |

### Boundary Value Analysis

| Type | Detection |
|------|-----------|
| Integer Overflow | MAX_INT + 1, multiplication overflow |
| Integer Underflow | MIN_INT - 1, subtraction underflow |
| Off-by-One | Loop bounds, array indexing |
| Empty Input | Empty strings, arrays, maps |
| Null/None | Null pointer, None checks |
| Large Input | Buffer overflow, stack overflow |

### Concurrency Issues

| Type | CWE | Detection |
|------|-----|-----------|
| Race Condition | CWE-362 | Check-then-act, shared mutable state |
| Deadlock | CWE-833 | Lock ordering, nested locks |
| Time-of-Check Time-of-Use | CWE-367 | File operations, permissions |
| Double-Checked Locking | — | Broken singleton patterns |

### State Machine Issues

| Type | Detection |
|------|-----------|
| Invalid Transition | Unexpected state changes |
| Missing Validation | State not checked before operation |
| Double Operations | Double free, double close |
| Use After | Use after free, use after close |

## ChaosAgent Coverage

### Resilience Categories

| Category | Coverage | Detection Examples |
|----------|----------|-------------------|
| **Dependency Failure** | ✓ Full | Database down, API errors |
| **Network Issues** | ✓ Full | Timeout, latency, packet loss |
| **Resource Exhaustion** | ✓ Full | Memory, connections, files |
| **Time Issues** | ◐ Partial | Clock skew, timezone |
| **Recovery** | ✓ Full | Crash recovery, state restoration |

### Failure Mode Analysis

| Dependency | Tested Failures |
|------------|-----------------|
| Database | Connection failure, slow queries, deadlocks |
| Cache | Miss, corruption, expiry |
| External API | 5xx errors, timeout, malformed response |
| Message Queue | Full queue, consumer lag, ordering |
| File System | Disk full, permission denied, corruption |

### Resilience Patterns Checked

| Pattern | Detection |
|---------|-----------|
| Retry Logic | Missing or unlimited retries |
| Circuit Breaker | Missing or misconfigured |
| Timeout | Missing or too long |
| Fallback | Missing graceful degradation |
| Bulkhead | Missing isolation |
| Rate Limiting | Missing or bypassable |

## CryptoAgent Coverage

### Cryptographic Categories

| Category | Coverage | Detection Examples |
|----------|----------|-------------------|
| **Algorithms** | ✓ Full | Weak hash, broken cipher |
| **Key Management** | ✓ Full | Hardcoded keys, weak generation |
| **Randomness** | ✓ Full | Predictable, insecure source |
| **Tokens/JWT** | ✓ Full | Algorithm confusion, weak signing |
| **TLS/SSL** | ◐ Partial | Version, cipher suite |

### Algorithm Weaknesses

| Weak | Replacement | Detection |
|------|-------------|-----------|
| MD5 | SHA-256+ | Hash function usage |
| SHA1 | SHA-256+ | Hash function usage |
| DES | AES | Cipher usage |
| 3DES | AES | Cipher usage |
| RC4 | AES-GCM | Cipher usage |
| RSA-1024 | RSA-2048+ | Key size check |
| ECDSA-160 | ECDSA-256+ | Curve size check |

### Token/JWT Issues

| Issue | CWE | Detection |
|-------|-----|-----------|
| Algorithm Confusion | CWE-327 | alg=none, HS256 vs RS256 |
| Weak Secret | CWE-326 | Short or guessable keys |
| Missing Validation | CWE-347 | Signature not verified |
| Improper Expiry | CWE-613 | Long or missing exp |
| Sensitive Data | CWE-311 | PII in payload |

### Randomness Issues

| Issue | CWE | Detection |
|-------|-----|-----------|
| Insecure Random | CWE-330 | random() for tokens |
| Predictable Seed | CWE-335 | Time-based seeding |
| Insufficient Entropy | CWE-331 | Short random values |

## What's NOT Covered

### Limitations

| Area | Reason |
|------|--------|
| Binary analysis | Text-based analysis only |
| Network scanning | Static analysis only |
| Dynamic testing | No runtime execution (sandbox is for payloads) |
| Infrastructure | Focus is on code |
| Third-party code | Limited to imports visible in code |
| Business logic specific | General patterns only |

### Complementary Tools

| Gap | Recommended Tools |
|-----|-------------------|
| Dependency vulnerabilities | Dependabot, Snyk, pip-audit |
| Container security | Trivy, Grype |
| Infrastructure scanning | Terraform Sentinel, AWS Config |
| Dynamic testing | OWASP ZAP, Burp Suite |
| Penetration testing | Manual, specialised tools |

## Coverage by Language

Primary coverage is Python, with partial support for:

| Language | Coverage | Notes |
|----------|----------|-------|
| Python | ✓ Full | Primary focus |
| JavaScript | ◐ Partial | Common patterns |
| TypeScript | ◐ Partial | Common patterns |
| Java | ◐ Partial | Common patterns |
| Go | ◐ Partial | Common patterns |
| Ruby | ○ Limited | Basic patterns |
| PHP | ○ Limited | Basic patterns |

## See Also

- [How It Works](how-it-works.md) — System overview
- [Agent Reference](../reference/agents.md) — Detailed agent behaviour
- [Interpreting Results](../guides/interpreting-results.md) — Understanding findings
