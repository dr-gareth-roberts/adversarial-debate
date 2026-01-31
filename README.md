<div align="center">

# 🔴 Adversarial Debate

### AI Red Team Security Testing Framework

**Find security vulnerabilities before attackers do.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/dr-gareth-roberts/adverserial-debate/actions/workflows/ci.yml/badge.svg)](https://github.com/dr-gareth-roberts/adverserial-debate/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/dr-gareth-roberts/adverserial-debate/branch/main/graph/badge.svg)](https://codecov.io/gh/dr-gareth-roberts/adverserial-debate)
[![PyPI](https://img.shields.io/pypi/v/adversarial-debate.svg)](https://pypi.org/project/adversarial-debate/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://bandit.readthedocs.io/)

[Getting Started](#-quick-start) •
[Documentation](#-documentation) •
[Examples](examples/) •
[Contributing](CONTRIBUTING.md)

</div>

---

> [!CAUTION]
> ## ⚠️ SAFETY WARNING — READ BEFORE USE
>
> **This framework is for AUTHORISED SECURITY TESTING ONLY.**
>
> - **Potential for Serious Damage**: This tool is designed to find security vulnerabilities by simulating real attacks. If misused, it can cause serious damage to computer systems, networks, and data.
> - **Explicit Permission Required**: You MUST have explicit, written permission from the system owner before testing any system. Unauthorised security testing is illegal in most jurisdictions.
> - **Sandbox Executes Potentially Malicious Code**: The sandbox component executes code that may be intentionally malicious. Ensure proper isolation and never run untrusted code outside the hardened sandbox environment.
> - **Not for Causing Harm**: This tool is NOT intended for causing harm to others, disrupting services, or any malicious purpose. Use it only for legitimate security research and authorised penetration testing.
>
> **Legal Disclaimer**: By using this software, you accept full responsibility for your actions. The authors and contributors are not liable for any damages, legal consequences, or harm resulting from the use or misuse of this framework. Ensure compliance with all applicable laws and regulations in your jurisdiction.

---

## What is Adversarial Debate?

Adversarial Debate is a **multi-agent AI security testing framework** that uses specialised agents to attack your code from different angles, then consolidates findings with confidence scoring.

Think of it as having a team of security experts—each with different specialisations—reviewing your code simultaneously.

```
                    ┌─────────────────────────────────────┐
                    │        ChaosOrchestrator            │
                    │    (Attack Strategy & Planning)     │
                    └─────────────────┬───────────────────┘
                                      │
            ┌─────────────────────────────────────────────────────────┐
            │                                                         │
            ▼                         ▼                         ▼
   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
   │  ExploitAgent   │     │   BreakAgent    │     │   ChaosAgent    │
   │                 │     │                 │     │                 │
   │  OWASP Top 10   │     │   Logic Bugs    │     │   Resilience    │
   │  SQL Injection  │     │   Edge Cases    │     │   Failure Modes │
   │  Auth Bypass    │     │   Race Conds    │     │   Resource Bugs │
   └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    │
                                    ▼
                           ┌─────────────────┐
                           │   CryptoAgent   │
                           │                 │
                           │  Weak Crypto    │
                           │  JWT/Token Bugs │
                           │  Key Handling   │
                           └────────┬────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
                                    │
                                    ▼
                    ┌─────────────────────────────────────┐
                    │             Arbiter                 │
                    │   Consolidation • Deduplication     │
                    │  Confidence Scoring • Prioritisation│
                    └─────────────────────────────────────┘
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent Architecture** | Five specialised agents attack code from different angles |
| **OWASP Top 10 Coverage** | Comprehensive security vulnerability detection |
| **Logic Bug Detection** | Find edge cases, race conditions, and state corruption |
| **Resilience Testing** | Test failure handling and resource exhaustion scenarios |
| **Confidence Scoring** | AI-powered severity and exploitability assessment |
| **Hardened Sandbox** | Execute untrusted code safely with Docker isolation |
| **Event Sourcing** | Immutable audit trail of all findings |
| **Type Safe** | Full type hints with mypy strict mode |
| **Deterministic Demo Mode** | Mock provider for repeatable runs without API keys |

## Agents Overview

### ExploitAgent — Security Vulnerabilities
Maps findings to OWASP Top 10 2021 and CWE identifiers:

| Category | What It Finds |
|----------|---------------|
| **A01: Broken Access Control** | IDOR, missing authorization, privilege escalation |
| **A02: Cryptographic Failures** | Weak hashing, hardcoded secrets, insecure random |
| **A03: Injection** | SQL, command, XSS, LDAP, template injection |
| **A05: Security Misconfiguration** | Debug mode, permissive CORS, verbose errors |
| **A08: Integrity Failures** | Insecure deserialization, unsigned data |
| **A10: SSRF** | Server-side request forgery |

### BreakAgent — Logic Bugs
Finds bugs that security scanners miss:

- **Boundary Conditions**: Off-by-one, integer overflow, empty collections
- **State Machines**: Invalid transitions, missing state validation
- **Concurrency**: Race conditions, deadlocks, data races
- **Error Handling**: Uncaught exceptions, improper cleanup
- **Type Confusion**: Implicit conversions, null handling

### ChaosAgent — Resilience Testing
Tests how code behaves under stress:

- **Resource Exhaustion**: Memory leaks, connection pool starvation
- **Network Failures**: Timeouts, partial failures, retry storms
- **Cascading Failures**: Dependency failures, circuit breaker testing
- **Recovery**: Crash recovery, state restoration

### Arbiter — Findings Consolidation
Makes sense of all the findings:

- **Deduplication**: Merges similar findings from different agents
- **Confidence Scoring**: Rates likelihood and impact
- **Prioritisation**: Ranks by severity and exploitability
- **Remediation Roadmap**: Suggests fixes in priority order

---

## Quick Start

### Requirements

- **Python**: 3.11 or higher
- **Dependency Manager**: [uv](https://github.com/astral-sh/uv) (recommended)
- **Containerization**: [Docker](https://www.docker.com/) (required for hardened sandboxing)
- **API Key**: Anthropic API key (default provider; not required for `mock`)

### Installation

```bash
# Using uv (recommended)
uv add adversarial-debate

# Using pip
pip install adversarial-debate

# From source
git clone https://github.com/dr-gareth-roberts/adverserial-debate.git
cd adverserial-debate
uv sync --extra dev
```

### Configuration

The framework can be configured via environment variables, a `.env` file, or a configuration file.

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key (not needed for `mock`) | *Required for anthropic* |
| `OPENAI_API_KEY` | OpenAI API key | *Required for openai* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | *Required for azure* |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | *Required for azure* |
| `OLLAMA_BASE_URL` | Ollama base URL (no API key required) | `http://localhost:11434` |
| `LLM_PROVIDER` | LLM provider to use (`anthropic`, `openai`, `azure`, `ollama`, `mock`) | `anthropic` |
| `LLM_MODEL` | Model version to use | `claude-sonnet-4-20250514` |
| `LLM_TIMEOUT` | Provider request timeout (seconds) | `120` |
| `ADVERSARIAL_DEBUG` | Enable verbose debug logging | `false` |
| `ADVERSARIAL_LOG_LEVEL` | Log level | `INFO` |
| `ADVERSARIAL_LOG_FORMAT` | Log format (`text` or `json`) | `text` |
| `ADVERSARIAL_OUTPUT_DIR`| Where to store results | `./output` |
| `ADVERSARIAL_BEAD_LEDGER` | Bead ledger path | `./beads/ledger.jsonl` |

#### Using a .env file

```bash
cp .env.example .env
# Edit .env with your settings
```

### Basic Usage

#### CLI

```bash
# Analyse a single file for exploits
adversarial-debate analyse exploit src/api/users.py

# Create a coordinated attack plan for a directory
adversarial-debate orchestrate src/

# Run the full pipeline (orchestrate + analyse + verdict)
adversarial-debate run src/api/ --output results/
```

#### No-API-Key Demo (Mock Provider)

Run a deterministic demo with the intentionally vulnerable mini app in `examples/mini-app/` (do not deploy it):

```bash
# Analyse with deterministic findings
LLM_PROVIDER=mock adversarial-debate analyse exploit examples/mini-app/app.py

# Full pipeline with artefacts under ./output/run-<timestamp>/
LLM_PROVIDER=mock adversarial-debate run examples/mini-app/ --output output
```

Or run the scripted demo:

```bash
./scripts/demo.sh
# or
make demo
```

Example output:

```text
============================================================
ExploitAgent Analysis Results
============================================================
Confidence: 82%

Findings: 2
  [HIGH] SQL injection in user lookup
  [HIGH] Command injection via report runner
```

The pipeline run writes `attack_plan.json`, `exploit_findings.json`, `break_findings.json`,
`chaos_findings.json`, `crypto_findings.json`, `findings.json`, `verdict.json` (unless `--skip-verdict`), and the canonical
`bundle.json` (override with `--bundle-file`). If cross-examination produces debated findings, they
are written to `findings.debated.json`.

#### Python API

```python
import asyncio
from adversarial_debate import (
    ExploitAgent,
    BreakAgent,
    ChaosAgent,
    Arbiter,
    get_provider,
    BeadStore,
    AgentContext,
)

from datetime import UTC, datetime

async def analyse_code(code: str, file_path: str):
    """Run agents on code and get consolidated findings."""
    provider = get_provider("anthropic")  # or "mock" for a deterministic demo
    store = BeadStore()

    # Initialize agents
    exploit = ExploitAgent(provider, store)

    # Build context for the agent
    context = AgentContext(
        run_id="analysis-001",
        timestamp_iso=datetime.now(UTC).isoformat(),
        policy={},
        thread_id="analysis-001",
        task_id="security-review",
        inputs={
            "code": code,
            "file_path": file_path,
            "language": "python",
        },
    )

    # Run analysis
    result = await exploit.run(context)
    return result

# Example: Find potential issues
vulnerable_code = "def get_user(id): return db.execute(f'SELECT * FROM users WHERE id={id}')"
result = asyncio.run(analyse_code(vulnerable_code, "app.py"))
```

---

## Hardened Sandbox

The framework includes a `SandboxExecutor` to safely execute code during analysis. By default, it uses Docker for strong isolation.

```python
import asyncio
from adversarial_debate import SandboxExecutor, SandboxConfig

config = SandboxConfig(
    timeout_seconds=30,
    memory_limit="512m",
    cpu_limit=0.5,
    network_enabled=False,
    docker_image="python:3.11-slim",
)

executor = SandboxExecutor(config)

async def run_in_sandbox() -> None:
    result = await executor.execute_python("print('Hello from the sandbox')")
    print(result.output)

asyncio.run(run_in_sandbox())
```

### Sandbox Security Features

- **Docker Isolation**: Code runs in ephemeral, unprivileged containers.
- **Resource Constraints**: Strict limits on CPU, memory, and execution time.
- **Network Gapping**: No outbound network access by default.
- **Read-Only Root**: Prevents modification of the container environment.
- **Drop Capabilities**: Minimal Linux capabilities assigned to the process.

---

## Documentation

📚 **[Full Documentation](docs/index.md)** — Complete guides, references, and tutorials.

### Getting Started
- [Quickstart](docs/getting-started/quickstart.md) — Get your first scan running in 5 minutes
- [Installation](docs/getting-started/installation.md) — All installation methods
- [Your First Analysis](docs/getting-started/first-analysis.md) — Step-by-step tutorial

### User Guides
- [CLI Reference](docs/guides/cli-reference.md) — Complete command-line reference
- [Configuration](docs/guides/configuration.md) — Environment variables and config files
- [Provider Setup](docs/guides/providers/index.md) — Anthropic, OpenAI, Azure, Ollama
- [Output Formats](docs/guides/output-formats.md) — JSON, SARIF, HTML, Markdown
- [Interpreting Results](docs/guides/interpreting-results.md) — Understanding findings

### Integration
- [CI/CD Integration](docs/integration/ci-cd.md) — GitHub Actions, GitLab CI, Jenkins
- [Baseline Tracking](docs/integration/baseline-tracking.md) — Track regressions

### Concepts
- [How It Works](docs/concepts/how-it-works.md) — System overview
- [Security Model](docs/concepts/security-model.md) — Threat model and sandboxing
- [Attack Coverage](docs/concepts/attack-coverage.md) — What vulnerabilities are detected

### Developer Guides
- [Python API](docs/developers/python-api.md) — Programmatic usage
- [Extending Agents](docs/developers/extending-agents.md) — Add custom agents
- [Extending Providers](docs/developers/extending-providers.md) — Add LLM providers
- [Event Sourcing](docs/developers/event-sourcing.md) — The Bead audit system
- [Testing Guide](docs/developers/testing.md) — Testing your extensions

### Reference
- [Agent Reference](docs/reference/agents.md) — Detailed agent documentation
- [Data Structures](docs/reference/data-structures.md) — Types and schemas
- [Architecture](docs/reference/architecture.md) — System internals

### Support
- [Troubleshooting](docs/support/troubleshooting.md) — Common issues and solutions
- [FAQ](docs/support/faq.md) — Frequently asked questions
- [Glossary](docs/support/glossary.md) — Key terms defined

### Other Resources
- [Examples](examples/) — Sample code and vulnerable test applications
- [Contributing Guidelines](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)

---

## Development

### Setup

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests

# Run type checking
uv run mypy src
```

### Convenience Targets

```bash
# Deterministic demo
make demo

# Lint / format / test
make lint
make format
make test
```

### Local Pre-commit (Optional)

To run the adversarial pipeline locally as a pre-commit hook, use `--files` so only staged paths are analysed.
This is best configured as a **manual** hook (so you can opt-in when you want deeper analysis).

Example `.pre-commit-config.yaml` snippet for your repo:

```yaml
- repo: local
  hooks:
    - id: adversarial-debate
      name: adversarial-debate (manual)
      entry: bash -lc 'adversarial-debate run . --files "$@" --time-budget 60 --skip-verdict --fail-on never --format markdown --report-file .adversarial-precommit.md'
      language: system
      types: [python]
      stages: [manual]
```

Then run:

```bash
pre-commit run adversarial-debate --hook-stage manual
```

### Project Structure

- `src/adversarial_debate/`: Core framework code.
    - `agents/`: AI agent implementations (Exploit, Break, Chaos, Arbiter).
    - `providers/`: LLM provider abstractions (Anthropic, etc.).
    - `sandbox/`: Secure execution environment.
    - `store/`: Immutable "Bead" ledger system.
    - `cli.py`: Command-line interface entry point (implementation in `cli_commands.py`).
- `tests/`: Comprehensive test suite.
- `examples/`: Usage demonstrations.
- `scripts/`: Helper scripts (demo, tooling).
- `docs/`: Technical documentation.

---

## Roadmap

- [ ] OpenAI and LiteLLM provider support
- [ ] VS Code Extension for real-time analysis
- [ ] GitHub Action for automated PR security reviews
- [ ] Support for more languages (JS/TS, Go, Rust)
- [ ] Web-based visualization dashboard for findings

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for our code of conduct and the process for submitting pull requests.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

[Report Bug](https://github.com/dr-gareth-roberts/adverserial-debate/issues/new?template=bug_report.yml) •
[Request Feature](https://github.com/dr-gareth-roberts/adverserial-debate/issues/new?template=feature_request.yml) •
[Ask Question](https://github.com/dr-gareth-roberts/adverserial-debate/discussions)

</div>
