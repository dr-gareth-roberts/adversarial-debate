# AGENTS.md

AI Red Team Security Testing Framework using adversarial agent mesh.

## Commands

```bash
make test                           # Run all tests
uv run --extra dev python -m pytest tests/test_file.py::test_name -v  # Single test
make lint                           # Lint with ruff
make format                         # Format with ruff
make typecheck                      # Type check with mypy (strict mode)
```

## Architecture

- **src/adversarial_debate/** — Main package
  - `agents/` — ExploitAgent, BreakAgent, ChaosAgent, CryptoAgent, Arbiter
  - `providers/` — LLM provider abstraction (Anthropic, OpenAI)
  - `store/` — Bead ledger (event-sourced append-only log)
  - `sandbox/` — Docker-based code execution sandbox
- Multi-agent pipeline: ChaosOrchestrator → Red Team Agents (parallel) → Arbiter

## Code Style

- Python 3.11+, strict mypy, ruff (line-length 100)
- Use `@dataclass` or Pydantic models for structured data
- Agents inherit from `Agent` ABC; implement `_build_prompt()` and `_parse_response()`
- All agent output is JSON; use `json_mode=True` in LLM calls
- Async-first: use `async def` for agent `run()` methods
- Naming: `snake_case` functions, `PascalCase` classes, `SCREAMING_SNAKE` constants
