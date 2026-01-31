# Security Model

This guide explains the security architecture of Adversarial Debate, including the threat model, trust boundaries, and hardening measures.

## Threat Model

### Assets to Protect

1. **Your source code** — Sent to LLM providers for analysis
2. **API keys** — Provider credentials
3. **Analysis results** — Findings and vulnerabilities discovered
4. **System integrity** — When executing code in sandbox

### Threat Actors

| Actor | Capability | Motivation |
|-------|------------|------------|
| Malicious code | Attempts escape from sandbox | System compromise |
| LLM provider | Sees your code | Data retention |
| Network attacker | Intercepts API traffic | Code theft |
| Supply chain | Compromised dependencies | Backdoor |

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR ENVIRONMENT                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    ADVERSARIAL-DEBATE                         │   │
│  │                                                               │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │                     AGENTS                               │ │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │ │   │
│  │  │  │ Exploit │ │  Break  │ │  Chaos  │ │ Crypto  │        │ │   │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  │                              │                                │   │
│  │                              ▼                                │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │                    SANDBOX                              │ │   │
│  │  │                                                         │ │   │
│  │  │  ┌───────────────────────────────────────────────────┐  │ │   │
│  │  │  │              DOCKER CONTAINER                      │  │ │   │
│  │  │  │  • Isolated network                                │  │ │   │
│  │  │  │  • Read-only filesystem                            │  │ │   │
│  │  │  │  • Limited resources                               │  │ │   │
│  │  │  │  • Dropped capabilities                            │  │ │   │
│  │  │  └───────────────────────────────────────────────────┘  │ │   │
│  │  └─────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
         ══════════════════════╪══════════════════════════ NETWORK
                               │
                               ▼
                    ┌─────────────────────┐
                    │    LLM PROVIDER     │
                    │  (Anthropic, etc.)  │
                    │                     │
                    │  Sees: Your code    │
                    │  Returns: Analysis  │
                    └─────────────────────┘
```

## Data Flow

### What's Sent to the LLM

When analysing code, the following is sent to the LLM provider:

1. **Source code** — The code being analysed
2. **File paths** — Names and locations
3. **System prompts** — Agent instructions
4. **Task context** — Analysis parameters

### What's NOT Sent

1. **API keys** — Never included in prompts
2. **Environment variables** — Filtered before sending
3. **Git history** — Not transmitted
4. **Other files** — Only files in scope

### Data at Rest

| Data | Location | Protection |
|------|----------|------------|
| Bead ledger | `beads/ledger.jsonl` | Local file, user permissions |
| Results | `output/` | Local files, user permissions |
| Cache | `cache/` | Local files, user permissions |
| Config | `.env`, `config.json` | Should be in `.gitignore` |

## Sandbox Security

The sandbox provides isolation when executing code during analysis.

### Docker Backend (Recommended)

```
Host System
│
└── Docker Container
    │
    ├── Network: --network none
    ├── Filesystem: --read-only
    ├── Resources: --memory 256m --cpus 0.5
    ├── User: --user 1000:1000 (non-root)
    ├── Capabilities: --cap-drop ALL
    └── Security: --security-opt no-new-privileges
```

**Security features:**

| Feature | Protection |
|---------|------------|
| Network isolation | Prevents exfiltration |
| Read-only root | Prevents persistence |
| Memory limits | Prevents DoS |
| CPU limits | Prevents DoS |
| Dropped capabilities | Reduces attack surface |
| Non-root user | Limits privilege |
| No new privileges | Prevents escalation |

### Subprocess Backend (Fallback)

When Docker isn't available, a subprocess-based sandbox is used:

| Feature | Protection |
|---------|------------|
| Resource limits | `setrlimit` for memory/CPU |
| Timeout | Hard kill after limit |
| Temp directory | Isolated working directory |

**Limitations:** Less isolation than Docker. Use only when Docker isn't available.

### Sandbox Configuration

```json
{
  "sandbox": {
    "use_docker": true,
    "docker_image": "python:3.11-slim",
    "memory_limit": "256m",
    "cpu_limit": 0.5,
    "timeout_seconds": 30,
    "network_enabled": false,
    "read_only": true
  }
}
```

## API Key Security

### Best Practices

1. **Use environment variables**
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

2. **Never commit keys**
   ```gitignore
   # .gitignore
   .env
   *.env
   config.json
   ```

3. **Use secrets managers in CI**
   ```yaml
   env:
     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
   ```

4. **Rotate regularly**
   - Create new keys periodically
   - Revoke old keys

5. **Use separate keys**
   - Different keys for dev/staging/prod
   - Easier to trace and revoke

### Key Storage

| Environment | Storage Method |
|-------------|----------------|
| Development | `.env` file (gitignored) |
| CI/CD | Secrets manager |
| Production | Vault/SSM/Secrets Manager |

## Input Validation

The framework validates all inputs:

### Code Input

```python
def validate_code_input(code: str) -> None:
    if len(code) > MAX_CODE_SIZE:
        raise InputValidationError("Code exceeds maximum size")
    if contains_null_bytes(code):
        raise InputValidationError("Code contains null bytes")
```

### Path Validation

```python
def validate_path(path: str) -> Path:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(allowed_root):
        raise PathTraversalError("Path outside allowed root")
    if resolved.is_symlink():
        raise SymlinkError("Symlinks not allowed")
    return resolved
```

### Identifier Validation

```python
def validate_bead_id(bead_id: str) -> None:
    if not BEAD_ID_PATTERN.match(bead_id):
        raise ValidationError("Invalid bead ID format")
```

## Provider Security

### Anthropic

- **Data handling:** No training on API data
- **Encryption:** TLS 1.2+ in transit
- **Compliance:** SOC 2, GDPR

### OpenAI

- **Data handling:** No training on API data
- **Encryption:** TLS 1.2+ in transit
- **Compliance:** SOC 2, GDPR

### Azure OpenAI

- **Data handling:** Enterprise controls
- **Encryption:** TLS 1.2+, optional CMK
- **Compliance:** SOC 2, HIPAA, FedRAMP

### Ollama

- **Data handling:** Fully local
- **Encryption:** N/A (local)
- **Compliance:** Your responsibility

## Audit Trail

All actions are recorded in the bead ledger:

```json
{
  "bead_id": "B-20240115-143022-000001",
  "timestamp_iso": "2024-01-15T14:30:22Z",
  "agent": "ExploitAgent",
  "bead_type": "EXPLOIT_ANALYSIS",
  "payload": {
    "findings": [...]
  }
}
```

This enables:
- **Forensics** — What was analysed and when
- **Accountability** — Who ran what analysis
- **Compliance** — Audit trail for reviews

## Security Recommendations

### For Development

1. Use mock provider for testing
2. Keep `.env` in `.gitignore`
3. Use Docker sandbox when possible

### For CI/CD

1. Store API keys in secrets manager
2. Use ephemeral environments
3. Don't log findings to public CI

### For Production

1. Use enterprise provider (Azure OpenAI)
2. Implement baseline suppression
3. Monitor API key usage
4. Set spending limits

### For Air-Gapped Environments

1. Use Ollama with local models
2. Disable network in sandbox
3. Audit all data flows

## Known Limitations

### LLM Inherent Risks

- **Prompt injection** — Malicious code could influence analysis
- **Hallucination** — False positives possible
- **Context limits** — Large files may be truncated

### Sandbox Limitations

- **Docker escapes** — Theoretical with kernel vulnerabilities
- **Resource limits** — Not foolproof on all systems
- **Subprocess backend** — Weaker isolation

### Network Trust

- **TLS required** — Depends on CA trust
- **Provider trust** — Code visible to provider

## Reporting Security Issues

See [SECURITY.md](../../SECURITY.md) for responsible disclosure.

## See Also

- [How It Works](how-it-works.md) — System overview
- [Configuration](../guides/configuration.md) — Security settings
- [Troubleshooting](../support/troubleshooting.md) — Security errors
