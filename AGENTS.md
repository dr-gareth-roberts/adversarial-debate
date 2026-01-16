# Repository Guidelines

## Project Structure & Module Organization
- `src/adversarial_debate/cli.py`: CLI entry point and command routing.
- `src/adversarial_debate/agents/`: agent implementations (Exploit, Break, Chaos, Arbiter, ChaosOrchestrator).
- `src/adversarial_debate/attack_plan.py`: attack plan schema produced by ChaosOrchestrator.
- `src/adversarial_debate/verdict.py`: Arbiter verdict and finding types.
- `src/adversarial_debate/providers/`: LLM provider abstraction and implementations.
- `src/adversarial_debate/store/`: bead types and the append-only ledger.
- `src/adversarial_debate/sandbox/`: sandbox execution helpers.
- `src/adversarial_debate/config.py`: environment and config loading.
- `tests/unit/` and `tests/integration/`: test suites.
- `docs/`: architecture and API documentation; `examples/`: runnable samples; `scripts/`: helper scripts.

## Architecture Overview
Adversarial Debate is a multi-agent pipeline for red-team analysis. The orchestrator plans work for specialized agents, agents emit structured findings, and the arbiter consolidates results into a final verdict. Every step emits beads for auditability.

```text
CLI (cli.py)
  -> Config + inputs
  -> AgentContext
  -> ChaosOrchestrator (agents/chaos_orchestrator.py)
       -> ExploitAgent / BreakAgent / ChaosAgent
       -> Arbiter (agents/arbiter.py)
  -> ArbiterVerdict (verdict.py)
  -> BeadStore (store/beads.py)
```

- ChaosOrchestrator outputs an `AttackPlan` (see `attack_plan.py`) and an ATTACK_PLAN bead.
- Each agent calls an `LLMProvider` and returns an `AgentOutput` with findings and beads.
- Arbiter validates, de-duplicates, and ranks findings, producing an `ArbiterVerdict`.
- The sandbox layer (`sandbox/`) can run risky probes under Docker or subprocess limits.

## Key Concepts
- `AgentContext`: the full input to agents, including repo files, policy, and recent beads.
- `AgentOutput`: structured result plus confidence, assumptions, unknowns, and beads.
- `Bead`: immutable event record written to the ledger for traceability.
- `AttackPlan`: orchestrator output describing attack assignments and priorities.
- `ArbiterVerdict`: final decision with validated findings and remediation tasks.
- `ModelTier`: provider-level routing for model selection.

## Learning Path
1. Read `README.md` for CLI usage and background.
2. Run `uv sync --dev`, then `LLM_PROVIDER=mock adversarial-debate analyze exploit examples/mini-app/app.py`.
3. Inspect `./output/` and the bead ledger at `./beads/ledger.jsonl`.
4. Read `docs/architecture.md` and `docs/api.md`.
5. Trace the code path: `cli.py` -> `config.py` -> `agents/base.py` -> `agents/chaos_orchestrator.py` -> `agents/arbiter.py` -> `store/beads.py`.
6. Study `tests/unit/test_agents/` and `tests/integration/` for expected behavior.
7. Try a small change: add a new attack vector in `attack_plan.py` or a targeted agent test.

## Common Workflows
- Single agent run: `adversarial-debate analyze exploit src/api/users.py`
- Orchestrator only: `adversarial-debate orchestrate src/`
- Arbiter only: `adversarial-debate verdict findings.json`
- Full pipeline: `adversarial-debate run src/ --output results/`

## Build, Test, and Development Commands
Use `uv` for dependency management:
- `uv sync --dev` installs dev dependencies.
- `uv run adversarial-debate --help` checks the CLI.
- `LLM_PROVIDER=mock adversarial-debate run examples/mini-app/ --output output` runs the deterministic demo.
- `uv run pytest tests/ -v` runs the full test suite.
- `uv run pytest tests/unit/test_verdict.py -v` runs a single file.
- `uv run pytest tests/ --cov=adversarial_debate --cov-report=html` generates coverage.
- `uv run ruff check src/` lints; `uv run ruff check src/ --fix` auto-fixes.
- `uv run ruff format src/` formats; `uv run ruff format --check src/` verifies.
- `uv run mypy src/adversarial_debate --ignore-missing-imports` runs type checks.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and Python 3.11+. Use type hints and Google-style docstrings for public APIs. Imports should be ordered as standard library, third-party, then local (ruff enforces this). Naming should be `snake_case` for functions/variables and `PascalCase` for classes. Keep functions small and single-purpose, and prefer explicit data structures over implicit behavior.

## Testing Guidelines
Tests use pytest with pytest-asyncio (`asyncio_mode = "auto"`). Mark async tests with `@pytest.mark.anyio`. Keep tests focused and mock external dependencies (LLM providers, filesystem). Shared fixtures live in `tests/conftest.py` (for example, `mock_provider` and `bead_store`). Put unit tests in `tests/unit/` and CLI/workflow tests in `tests/integration/`.

## Commit & Pull Request Guidelines
Current history uses Conventional Commit-style prefixes (for example, `feat: ...`); follow that pattern when possible. Use focused branches (example: `feature/my-change`). Before opening a PR, run tests and quality checks (`pytest`, `ruff`, `mypy`). PRs should include a clear description, tests for new behavior, and doc updates when needed, with linked issues when applicable.

## Security & Configuration Tips
- Secrets: do not commit API keys; use environment variables or a local config file.
- Required: `ANTHROPIC_API_KEY` (or provider-specific key).
- Useful env vars: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TIMEOUT`, `ADVERSARIAL_OUTPUT_DIR`, `ADVERSARIAL_BEAD_LEDGER`, `ADVERSARIAL_LOG_LEVEL`, `ADVERSARIAL_LOG_FORMAT`, `ADVERSARIAL_DRY_RUN`, `ADVERSARIAL_DEBUG`.
- CLI flags: `--config`, `--log-level`, `--json-output`, `--dry-run`, `--output`.
- See `.env.example` for a starting template.

## Output & Artifacts
- Results default to `./output/` (override via `--output` or `ADVERSARIAL_OUTPUT_DIR`).
- Beads are appended to `./beads/ledger.jsonl` (override via `ADVERSARIAL_BEAD_LEDGER`).
- Coverage reports from `pytest --cov-report=html` are generated in `htmlcov/`.

## Adding or Updating Agents
1. Create a new file in `src/adversarial_debate/agents/`.
2. Extend `Agent` and implement `name`, `bead_type`, `_build_prompt`, and `_parse_response`.
3. Return an `AgentOutput` that includes findings and beads; use `_create_bead` for consistency.
4. Export the new class in `src/adversarial_debate/agents/__init__.py`.
5. Add tests in `tests/unit/test_agents/` and consider a CLI integration test if behavior is user-facing.
6. Update docs or examples if the new agent adds a workflow or output shape.

## Claude Code Guidance
This section mirrors the guidance formerly in `CLAUDE.md` so everything lives in one file.

### Project Overview
Adversarial Debate is a multi-agent AI security testing framework. Specialized agents (ExploitAgent, BreakAgent, ChaosAgent) attack code from different angles, then an Arbiter consolidates findings with confidence scoring. All activity is recorded as immutable "Beads" in an event-sourced ledger.

### Development Commands

```bash
# Install dependencies
uv sync --dev

# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_verdict.py -v

# Run with coverage
uv run pytest tests/ --cov=adversarial_debate --cov-report=html

# Linting
uv run ruff check src/
uv run ruff check src/ --fix  # auto-fix

# Formatting
uv run ruff format src/

# Type checking
uv run mypy src/adversarial_debate --ignore-missing-imports

# CLI usage
adversarial-debate --help
adversarial-debate analyze exploit src/api/users.py
adversarial-debate run src/ --output results/
```

### Architecture

#### Data Flow
```
Source Code -> AgentContext -> ChaosOrchestrator
                                   |
                +------------------+------------------+
                |                  |                  |
                v                  v                  v
          ExploitAgent        BreakAgent         ChaosAgent
          (OWASP Top 10)      (Logic bugs)       (Resilience)
                \------------------|------------------/
                                   |
                                   v
                                 Arbiter
                     (Consolidation & Deduplication)
                                   |
                                   v
                     ArbiterVerdict -> BeadStore (audit ledger)
```

#### Core Components

**Agents** (`src/adversarial_debate/agents/`):
- All agents inherit from `Agent` base class in `base.py`
- Agents are stateless: context flows through `AgentContext`, output is `AgentOutput`
- Must implement: `name`, `bead_type`, `_build_prompt()`, `_parse_response()`
- Use `_create_bead()` to record findings to the audit trail
- All execution is async (`async def run()`)

**Bead Store** (`src/adversarial_debate/store/beads.py`):
- Beads are immutable records of agent findings
- Deterministic IDs via SHA-256 hash ensure idempotency
- Append-only JSONL ledger with file locking for auditability

**LLM Providers** (`src/adversarial_debate/providers/`):
- Abstract `LLMProvider` with `complete()` method
- `ModelTier` enum routes to appropriate model
- JSON mode enabled for structured output

**Sandbox** (`src/adversarial_debate/sandbox/`):
- Docker isolation (preferred) or subprocess fallback
- Resource limits: memory, CPU, timeout
- Methods for testing: SQL injection, command injection, SSRF, etc.

#### Adding a New Agent

1. Create file in `src/adversarial_debate/agents/`
2. Extend `Agent` base class
3. Implement required properties and methods:
```python
from adversarial_debate.agents.base import Agent, AgentContext, AgentOutput
from adversarial_debate.store import BeadType

class MyAgent(Agent):
    @property
    def name(self) -> str:
        return "MyAgent"

    @property
    def bead_type(self) -> BeadType:
        return BeadType.ANALYSIS

    def _build_prompt(self, context: AgentContext) -> list[Message]:
        ...

    def _parse_response(self, response: str, context: AgentContext) -> AgentOutput:
        ...
```
4. Export in `agents/__init__.py`
5. Add tests in `tests/unit/test_agents/`

### Code Style

- Python 3.11+, mypy strict mode
- Google-style docstrings
- Use type hints for all function signatures
- Imports: stdlib -> third-party -> local (ruff sorts automatically)

### Configuration

Key environment variables:
- `LLM_PROVIDER` - Default: `anthropic` (use `mock` for deterministic runs)
- `ANTHROPIC_API_KEY` - Required for `anthropic`
- `LLM_MODEL` - Default: `claude-sonnet-4-20250514`
- `ADVERSARIAL_DEBUG` - Enable verbose logging
- `ADVERSARIAL_OUTPUT_DIR` - Results directory (default: `./output`)

### Testing

- pytest with pytest-asyncio (`asyncio_mode = "auto"`)
- Use `@pytest.mark.anyio` for async tests
- Common fixtures in `tests/conftest.py`: `test_config`, `mock_provider`, `bead_store`, `sample_context`
- Mock external dependencies (LLM providers, filesystem)
