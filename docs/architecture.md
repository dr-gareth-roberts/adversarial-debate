# Architecture

This document describes the architecture of Adversarial Debate, a multi-agent AI security testing framework.

## Overview

Adversarial Debate uses specialized agents to analyze code from multiple angles, then consolidates findings with an arbiter. The pipeline is designed for auditability: each agent emits immutable "beads" into an append-only JSONL ledger.

```text
CLI / Python API
  -> AgentContext
  -> ChaosOrchestrator (attack planning)
       -> ExploitAgent | BreakAgent | ChaosAgent
  -> Arbiter (consolidation + verdict)
  -> BeadStore (JSONL ledger)
```

## Core Components

- **CLI** (`src/adversarial_debate/cli.py`): command parsing, IO, and orchestration for local runs.
- **Agents** (`src/adversarial_debate/agents/`): stateless analyzers with strict input/output contracts.
  - `ExploitAgent`: OWASP security findings
  - `BreakAgent`: logic bugs and edge cases
  - `ChaosAgent`: resilience experiments
  - `ChaosOrchestrator`: attack planning
  - `Arbiter`: validation, deduplication, and verdict
- **Providers** (`src/adversarial_debate/providers/`): LLM backends.
  - `AnthropicProvider`: real API calls
  - `MockProvider`: deterministic, no API key demo/test
- **Store** (`src/adversarial_debate/store/`): JSONL bead ledger with idempotency and auditability.
- **Sandbox** (`src/adversarial_debate/sandbox/`): isolated execution helpers (Docker or subprocess).
- **Config** (`src/adversarial_debate/config.py`): dataclass-based config from env or JSON.

## Data Flow (CLI `run`)

1. **Collect inputs**: target files + patches are gathered from a file or directory.
2. **Plan**: ChaosOrchestrator returns an `AttackPlan` and emits an ATTACK_PLAN bead.
3. **Analyze**: Exploit, Break, and Chaos agents run in parallel and emit beads.
4. **Consolidate**: Arbiter merges findings into an `ArbiterVerdict`.
5. **Persist**: artifacts are written to `./output/run-<timestamp>/` and beads to `./beads/ledger.jsonl`.

## Bead Ledger

Beads are immutable event records. Each bead includes:
- `thread_id` and `task_id` for traceability
- `bead_type` for classification
- `payload` for structured summaries
- `confidence`, `assumptions`, and `unknowns`

The ledger is JSONL, append-only, and guarded with file locking for safe concurrent writes.

## Extension Points

- **New agents**: extend `Agent` and implement `name`, `bead_type`, `_build_prompt`, and `_parse_response`.
- **New providers**: implement `LLMProvider` and add to `get_provider`.
- **New workflows**: add new CLI commands or pipeline steps in `cli.py`.

## Demo Architecture

For a deterministic walkthrough, use the mock provider with the mini app in `examples/mini-app/`. The demo exercises the full pipeline without external API calls.
