# Adversarial Debate

AI Red Team Security Testing Framework using an adversarial agent mesh.

## Overview

Adversarial Debate is a 5-phase red team system that uses multiple specialized AI agents to find security vulnerabilities and logic bugs in code. Each agent attacks from a different angle, and findings are consolidated with confidence scoring.

```
ChaosOrchestrator (strategy)
        │
        ├── ExploitAgent (OWASP Top 10 security)
        ├── BreakAgent (logic bugs, edge cases)
        └── ChaosAgent (resilience, failure modes)
        │
        ▼
    Arbiter (consolidation + deduplication)
```

## Features

- **ExploitAgent**: Security vulnerabilities mapped to OWASP Top 10 and CWE
- **BreakAgent**: Logic bugs, boundary conditions, state corruption
- **ChaosAgent**: Failure handling, resource exhaustion, race conditions
- **ChaosOrchestrator**: Coordinates attack strategy based on code analysis
- **Arbiter**: Consolidates findings, deduplicates, assigns confidence scores
- **Hardened Sandbox**: Secure code execution with Docker isolation

## Installation

```bash
pip install adversarial-debate
```

Or install from source:

```bash
git clone https://github.com/dr-gareth-roberts/adversarial-debate.git
cd adversarial-debate
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from adversarial_debate import (
    ExploitAgent,
    BreakAgent,
    ChaosAgent,
    Arbiter,
    AnthropicProvider,
    BeadStore,
    AgentContext,
)

async def analyze_code(code: str, file_path: str):
    # Setup
    provider = AnthropicProvider()
    store = BeadStore("beads.db")

    # Create agents
    exploit_agent = ExploitAgent(provider, store)
    break_agent = BreakAgent(provider, store)
    chaos_agent = ChaosAgent(provider, store)
    arbiter = Arbiter(provider, store)

    # Build context
    context = AgentContext(
        run_id="run-001",
        timestamp_iso="2024-01-01T00:00:00Z",
        policy={},
        thread_id="thread-001",
        task_id="task-001",
        inputs={
            "code": code,
            "file_path": file_path,
            "language": "python",
            "exposure": "public",
        }
    )

    # Run agents
    exploit_result = await exploit_agent.run(context)
    break_result = await break_agent.run(context)
    chaos_result = await chaos_agent.run(context)

    # Consolidate findings
    arbiter_context = AgentContext(
        run_id="run-001",
        timestamp_iso="2024-01-01T00:00:00Z",
        policy={},
        thread_id="thread-001",
        task_id="task-001",
        inputs={
            "findings": {
                "exploit": exploit_result.result,
                "break": break_result.result,
                "chaos": chaos_result.result,
            }
        }
    )
    final_result = await arbiter.run(arbiter_context)

    return final_result

# Example usage
code = '''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
'''

result = asyncio.run(analyze_code(code, "app.py"))
print(f"Found {len(result.result['findings'])} issues")
```

## Agent Types

### ExploitAgent

Focuses on OWASP Top 10 2021 security vulnerabilities:

- **A01: Broken Access Control** - IDOR, missing auth, path traversal
- **A02: Cryptographic Failures** - Weak hashing, hardcoded secrets
- **A03: Injection** - SQL, command, XSS, template injection
- **A05: Security Misconfiguration** - Debug mode, CORS issues
- **A08: Software Integrity Failures** - Insecure deserialization
- **A10: SSRF** - Server-side request forgery

### BreakAgent

Focuses on logic bugs and edge cases:

- Boundary value errors (off-by-one, overflow)
- State machine violations
- Race conditions and concurrency bugs
- Error handling gaps
- Type confusion
- Business logic flaws

### ChaosAgent

Tests resilience and failure handling:

- Resource exhaustion (memory, disk, connections)
- Network failures and timeouts
- Cascading failures
- Recovery behavior
- Data corruption scenarios
- Circuit breaker testing

### Arbiter

Consolidates findings from all agents:

- Deduplicates similar findings
- Assigns confidence scores
- Prioritizes by severity and exploitability
- Generates remediation roadmap

## Hardened Sandbox

Execute untrusted code safely:

```python
from adversarial_debate import SandboxExecutor, SandboxConfig

config = SandboxConfig(
    timeout_seconds=30,
    max_memory_mb=512,
    use_docker=True,
)

executor = SandboxExecutor(config)
result = executor.execute_python(
    code="print('Hello, World!')",
    inputs={"x": 42}
)
print(result.stdout)
```

Security features:
- Docker isolation with resource limits
- Atomic temp file creation
- Path traversal prevention
- Input validation and sanitization
- Cryptographically secure temp names

## Configuration

Set your API key:

```bash
export ANTHROPIC_API_KEY=your-key-here
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type check
mypy src/

# Lint
ruff check src/
```

## Architecture

The system uses an event-sourced "bead" architecture where each agent emits structured findings as immutable records:

```
┌─────────────────┐
│  AgentContext   │  Input: code, policy, prior beads
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Agent       │  Stateless processor
│  (LLM + Parse)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AgentOutput   │  Structured findings + beads
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   BeadStore     │  SQLite with FTS5 search
└─────────────────┘
```

## License

MIT License - see LICENSE file for details.
