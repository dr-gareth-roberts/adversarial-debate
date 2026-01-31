# Security Policy

## Supported Versions

The following versions of Adversarial Debate are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

**Use [GitHub's private vulnerability reporting](https://github.com/dr-gareth-roberts/adverserial-debate/security/advisories/new)**

This is the preferred method. The form will guide you through the process.

### What to Include

When reporting a vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Impact**: What an attacker could achieve by exploiting this vulnerability
3. **Steps to Reproduce**: Detailed steps to reproduce the issue
4. **Affected Versions**: Which versions are affected
5. **Potential Fix**: If you have suggestions for fixing the vulnerability

### Response Timeline

- **Acknowledgment**: Within 48 hours of report receipt
- **Initial Assessment**: Within 5 business days
- **Status Updates**: Every 7 days until resolution
- **Resolution Target**: Within 90 days for most vulnerabilities

### Disclosure Policy

- We follow [coordinated disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure)
- We will work with you to understand and validate the issue
- We will develop and test a fix before public disclosure
- We will credit reporters in the security advisory (unless anonymity is requested)

---

## Security Model

### Threat Model

Adversarial Debate is designed for security testing. The framework processes potentially malicious code, so security is paramount.

#### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRUSTED ZONE                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Config    │    │   Agents    │    │   Store     │         │
│  │   System    │    │   (LLM)     │    │   (Beads)   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                    ┌───────┴───────┐                           │
│                    │    Sandbox    │                           │
│                    │  (Execution)  │                           │
│                    └───────┬───────┘                           │
└────────────────────────────┼────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │  UNTRUSTED ZONE │
                    │                 │
                    │  - User Code    │
                    │  - LLM Output   │
                    │  - External I/O │
                    └─────────────────┘
```

#### Threats Addressed

| Threat | Mitigation |
|--------|------------|
| **Code Execution Escape** | Docker isolation, resource limits, process sandboxing |
| **Path Traversal** | Input validation, symlink detection, path canonicalization |
| **Resource Exhaustion** | Memory/CPU limits, timeout enforcement, input size limits |
| **Injection Attacks** | Input sanitization, parameterized queries in store |
| **Sensitive Data Exposure** | API key hiding, secure temp file handling |
| **Denial of Service** | Rate limiting, resource limits, timeout handling |

### Sandbox Security

The sandbox execution environment implements multiple layers of defense:

#### 1. Input Validation
- **Identifier Validation**: Blocks dangerous Python builtins (`exec`, `eval`, `__import__`, etc.)
- **Code Size Limits**: Maximum 1MB of code input
- **Input Size Limits**: Maximum 10MB total, 1MB per value
- **Path Validation**: No symlinks, no directory traversal

#### 2. Execution Isolation

**Docker Mode (Recommended)**:
```python
# Resource limits enforced
- Memory: Configurable (default 256MB)
- CPU: Configurable (default 1 core)
- Network: Disabled by default
- Capabilities: Dropped
- Read-only filesystem: Enabled
```

**Subprocess Mode (Fallback)**:
```python
# setrlimit restrictions
- RLIMIT_AS: Virtual memory limit
- RLIMIT_CPU: CPU time limit
- RLIMIT_FSIZE: File size limit
- RLIMIT_NOFILE: Open file descriptor limit
```

#### 3. File System Security
- **Atomic Creation**: Files created with `O_CREAT | O_EXCL` flags
- **Secure Permissions**: 0o600 (owner read/write only)
- **Secure Random Names**: `secrets.token_hex(16)` for temp files
- **Automatic Cleanup**: Temp files removed after execution

#### 4. Process Control
- **SIGKILL Termination**: Reliable process termination (not SIGTERM)
- **Timeout Enforcement**: Strict timeout with automatic kill
- **Resource Monitoring**: Memory and CPU usage tracking

### API Key Security

- API keys are loaded from environment variables or secure config files
- Keys are **never** logged in plaintext
- Keys are **never** included in bead store entries
- `config.to_dict()` automatically redacts sensitive values

### Bead Store Security

- **Read-only Intent**: The bead store is append-only by design
- **SQL Injection Prevention**: All queries use parameterized statements
- **FTS5 Safe Queries**: Full-text search uses SQLite's built-in escaping
- **File Permissions**: Database files created with restricted permissions

---

## Secure Configuration

### Environment Variables

```bash
# .env file should have restricted permissions
chmod 600 .env

# Never commit .env to version control
# Use .env.example as a template
```

### Production Recommendations

1. **Use Docker Mode**: Always use Docker sandbox in production
2. **Network Isolation**: Run in isolated network environment
3. **Resource Limits**: Set appropriate memory/CPU limits
4. **Logging**: Enable audit logging for compliance
5. **Access Control**: Restrict who can run analyses
6. **Input Validation**: Validate all code inputs before analysis

### Dangerous Configurations

**Avoid these configurations in production:**

```python
# DON'T: Disable sandbox
sandbox_config = SandboxConfig(enabled=False)  # Dangerous!

# DON'T: Allow network access in sandbox
sandbox_config = SandboxConfig(network_enabled=True)  # Risk of data exfiltration

# DON'T: Set unlimited resources
sandbox_config = SandboxConfig(
    memory_limit_mb=0,  # No limit - risk of resource exhaustion
    timeout_seconds=0,  # No timeout - risk of hanging
)
```

---

## Security Checklist

### For Users

- [ ] Store API keys in environment variables, not code
- [ ] Use Docker sandbox mode in production
- [ ] Set appropriate resource limits
- [ ] Run in an isolated environment
- [ ] Review findings before acting on them
- [ ] Keep the framework updated

### For Contributors

- [ ] Never log sensitive data (API keys, tokens, credentials)
- [ ] Validate all inputs, especially file paths and code
- [ ] Use parameterized queries for database operations
- [ ] Follow the principle of least privilege
- [ ] Add security tests for new features
- [ ] Document security implications of changes

---

## Security Acknowledgments

We thank the following individuals for responsibly disclosing security issues:

*No security issues have been reported yet.*

---

## Related Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.org/dev/security/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
