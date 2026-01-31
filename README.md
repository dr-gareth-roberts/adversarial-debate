<div align="center">

# Adversarial Debate

### AI Red Team Security Testing Framework

**Find security vulnerabilities before attackers do.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/dr-gareth-roberts/adversarial-debate/actions/workflows/ci.yml/badge.svg)](https://github.com/dr-gareth-roberts/adversarial-debate/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/dr-gareth-roberts/adversarial-debate/branch/main/graph/badge.svg)](https://codecov.io/gh/dr-gareth-roberts/adversarial-debate)
[![PyPI](https://img.shields.io/pypi/v/adversarial-debate.svg)](https://pypi.org/project/adversarial-debate/)
[![Licence: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://bandit.readthedocs.io/)

[Quickstart](#quickstart) •
[Documentation](#documentation) •
[Examples](examples/) •
[Contributing](CONTRIBUTING.md)

</div>

---

> [!CAUTION]
> ## Safety warning — read before use
> **This framework is for authorised security testing only.**
>
> - **Potential for serious damage**: This tool simulates real attacks. Misuse can cause serious damage to systems and data.
> - **Explicit permission required**: You must have explicit, written permission from the system owner before testing.
> - **Sandbox executes potentially malicious code**: Use proper isolation and never run untrusted code outside the hardened sandbox.
> - **Not for harm**: This tool is not intended for disruption or malicious use.
>
> **Legal disclaimer**: By using this software, you accept full responsibility for your actions. The authors and contributors are not liable for any damages, legal consequences, or harm resulting from use or misuse. Ensure compliance with applicable laws and regulations in your jurisdiction.

---

## Overview

Adversarial Debate is a **multi-agent AI security testing framework**. Specialised agents analyse your code from different angles and the Arbiter consolidates findings with confidence scoring and prioritised remediation.

```
ChaosOrchestrator
  ├─ ExploitAgent (security vulnerabilities)
  ├─ BreakAgent   (logic bugs and edge cases)
  ├─ ChaosAgent   (resilience and failure modes)
  └─ CryptoAgent  (crypto and auth-adjacent issues)
        ↓
      Arbiter (deduplication + prioritisation + verdict)
```

## Key capabilities

- **Multi-agent architecture** covering OWASP Top 10, logic bugs, resilience failures, and crypto weaknesses
- **Confidence scoring** with severity and exploitability assessment
- **Hardened sandbox** for safe execution of untrusted code
- **Event-sourced audit trail** via the bead ledger
- **Deterministic demo mode** via the mock provider

## Quickstart

### Requirements

- Python 3.11+
- Docker (required for hardened sandboxing)
- An LLM provider API key (not required for `mock`)

### Install

```bash
# Using uv (recommended)
uv add adversarial-debate

# Using pip
pip install adversarial-debate

# From source
git clone https://github.com/dr-gareth-roberts/adversarial-debate.git
cd adversarial-debate
uv sync --extra dev
```

### Run

```bash
# Analyse a single file for exploits
adversarial-debate analyze exploit src/api/users.py

# Create a coordinated attack plan for a directory
adversarial-debate orchestrate src/

# Run the full pipeline (orchestrate + analyze + verdict)
adversarial-debate run src/api/ --output results/
```

### Deterministic demo (no API key)

```bash
LLM_PROVIDER=mock adversarial-debate analyze exploit examples/mini-app/app.py
LLM_PROVIDER=mock adversarial-debate run examples/mini-app/ --output output
```

## Outputs

A pipeline run writes:

- `attack_plan.json`
- `exploit_findings.json`
- `break_findings.json`
- `chaos_findings.json`
- `crypto_findings.json`
- `findings.json`
- `verdict.json` (unless `--skip-verdict`)
- `bundle.json` (canonical bundle; override with `--bundle-file`)

If cross-examination produces debated findings, it writes `findings.debated.json`.

## Python API

```python
import asyncio
from datetime import UTC, datetime

from adversarial_debate import (
    AgentContext,
    BeadStore,
    ExploitAgent,
    get_provider,
)

async def analyse_code(code: str, file_path: str):
    provider = get_provider("anthropic")  # or "mock" for a deterministic demo
    store = BeadStore()
    exploit = ExploitAgent(provider, store)

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

    return await exploit.run(context)

result = asyncio.run(
    analyse_code(
        "def get_user(id): return db.execute(f'SELECT * FROM users WHERE id={id}')",
        "app.py",
    )
)
```

## Hardened sandbox

The `SandboxExecutor` runs untrusted code with strict limits.

```python
import asyncio
from adversarial_debate import SandboxConfig, SandboxExecutor

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

## Documentation

Start here: `docs/index.md`.

Highlights:

- Getting started: `docs/getting-started/quickstart.md`
- CLI reference: `docs/guides/cli-reference.md`
- Configuration: `docs/guides/configuration.md`
- Output formats: `docs/guides/output-formats.md`
- CI/CD integration: `docs/integration/ci-cd.md`
- Developer guides: `docs/developers/`

## Development

```bash
# Install dependencies
uv sync --extra dev

# Tests
make test

# Lint / format / type-check
make lint
make format
make typecheck
```

## Security

Please read `SECURITY.md` and report vulnerabilities via the security policy.

## Licence

This project is licensed under the MIT Licence. See `LICENSE` for details.

## Links

- Repository: https://github.com/dr-gareth-roberts/adversarial-debate
- Issues: https://github.com/dr-gareth-roberts/adversarial-debate/issues
- Discussions: https://github.com/dr-gareth-roberts/adversarial-debate/discussions
