# Demo Walkthrough (No API Key)

This demo uses the deterministic mock provider and the intentionally vulnerable mini app in `examples/mini-app/`.

## Prerequisites

- Python 3.11+
- No API key required

## Run the Demo

```bash
# Single-agent run
LLM_PROVIDER=mock adversarial-debate analyze exploit examples/mini-app/app.py

# Full pipeline (orchestrate -> analyze -> verdict)
LLM_PROVIDER=mock adversarial-debate run examples/mini-app/ --output output
```

Or use the helper script:

```bash
./scripts/demo.sh
make demo
```

## What You Get

A run directory is created under `./output/`:

```text
output/
  run-<timestamp>/
    attack_plan.json
    exploit_findings.json
    break_findings.json
    chaos_findings.json
    findings.json
    verdict.json
```

The mock provider returns deterministic findings, so results are repeatable. This makes it ideal for demos, recruiter reviews, and CI smoke tests.

## Inspecting the Results

- `attack_plan.json` shows how ChaosOrchestrator prioritized targets.
- `exploit_findings.json`, `break_findings.json`, `chaos_findings.json` show each agent's raw output.
- `findings.json` is the combined set passed to the Arbiter.
- `verdict.json` contains the consolidated decision and remediation tasks.
