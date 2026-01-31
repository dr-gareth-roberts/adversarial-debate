# Quickstart

Get your first security scan running in under 5 minutes—no API key required.

> **Safety Reminder:** Only use this framework to test systems you own or have explicit written authorisation to test. Unauthorised security testing is illegal in most jurisdictions.

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Step 1: Install

```bash
# Using uv (recommended)
uv add adversarial-debate

# Or using pip
pip install adversarial-debate
```

## Step 2: Run Your First Scan

The framework includes a mock provider that produces deterministic results without requiring an API key. This is perfect for getting started.

```bash
# Analyze a single file
LLM_PROVIDER=mock adversarial-debate analyze exploit examples/mini-app/app.py

# Or run the full pipeline on a directory
LLM_PROVIDER=mock adversarial-debate run examples/mini-app/ --output output
```

## Step 3: View the Results

After running the full pipeline, you'll find results in the `output/` directory:

```
output/
└── run-20240115-143022/
    ├── attack_plan.json      # Orchestrator's attack strategy
    ├── exploit_findings.json # Security vulnerabilities found
    ├── break_findings.json   # Logic bugs and edge cases
    ├── chaos_findings.json   # Resilience experiments
    ├── crypto_findings.json  # Cryptographic weaknesses
    ├── findings.json         # All findings combined
    ├── verdict.json          # Final BLOCK/WARN/PASS verdict
    └── bundle.json           # Canonical results bundle
```

## Example Output

```
============================================================
VERDICT: BLOCK
============================================================

Blocking Issues: 2
  [CRITICAL] SQL injection in user lookup
    File: examples/mini-app/app.py:42
    Exploitation: TRIVIAL
    Fix effort: HOURS

  [HIGH] Command injection via report runner
    File: examples/mini-app/app.py:78
    Exploitation: EASY
    Fix effort: HOURS

Warnings: 1
  [MEDIUM] Missing rate limiting on login endpoint

Results saved to: output/run-20240115-143022/
```

## What's Next?

- **[Installation Guide](installation.md)** — Learn all installation methods and set up real providers
- **[Your First Analysis](first-analysis.md)** — Step-by-step tutorial with detailed explanations
- **[CLI Reference](../guides/cli-reference.md)** — Explore all available commands and options

## Using a Real Provider

Once you're ready to analyse your own code with a real LLM:

```bash
# Set your API key
export ANTHROPIC_API_KEY=your-key-here

# Run on your code
adversarial-debate run src/ --output results/
```

See [Provider Setup](../guides/providers/index.md) for configuring Anthropic, OpenAI, Azure, or Ollama.
