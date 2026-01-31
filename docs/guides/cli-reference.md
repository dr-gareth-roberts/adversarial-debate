# CLI Reference

Complete command-line reference for Adversarial Debate.

## Synopsis

```bash
adversarial-debate [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS] [ARGUMENTS]
```

## Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `-c, --config FILE` | Path to configuration file |
| `--log-level LEVEL` | Log level: DEBUG, INFO, WARNING, ERROR |
| `--json-output` | Output results as JSON |
| `--dry-run` | Show what would be done without executing |

## Commands

### run

Run the complete analysis pipeline: orchestrate → analyse → (cross-examine) → verdict.

```bash
adversarial-debate run TARGET [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `TARGET` | File or directory to analyse |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output DIR` | `./output` | Output directory for results |
| `--bundle-file FILE` | `bundle.json` | Name for the canonical results bundle |
| `--report-file FILE` | — | Generate a formatted report file |
| `--format FORMAT` | `json` | Report format: `json`, `sarif`, `html`, `markdown` |
| `--parallel N` | `3` | Maximum concurrent agent executions |
| `--time-budget SECONDS` | `600` | Total time budget for the analysis |
| `--skip-verdict` | — | Skip the Arbiter verdict stage |
| `--skip-debate` | — | Skip cross-examination stage |
| `--fail-on LEVEL` | `block` | Exit non-zero on: `block`, `warn`, `never` |
| `--baseline FILE` | — | Compare against baseline for regression detection |
| `--files FILE...` | — | Analyse only specific files (for pre-commit hooks) |

**Examples:**

```bash
# Full pipeline with all defaults
adversarial-debate run src/

# Save results to specific directory
adversarial-debate run src/ --output security-results/

# Generate SARIF report for IDE integration
adversarial-debate run src/ --format sarif --report-file findings.sarif

# Run with time limit
adversarial-debate run src/ --time-budget 300

# Skip verdict for faster iteration
adversarial-debate run src/ --skip-verdict

# Compare against baseline
adversarial-debate run src/ --baseline previous-run.json

# Use with pre-commit hooks
adversarial-debate run . --files src/api/auth.py src/api/users.py
```

### analyse

Run a single agent on target code.

```bash
adversarial-debate analyse AGENT TARGET [OPTIONS]
```

**Arguments:**

| Argument | Values | Description |
|----------|--------|-------------|
| `AGENT` | `exploit`, `break`, `chaos`, `crypto` | Agent to run |
| `TARGET` | — | File or directory to analyse |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output FILE` | — | Output file for results |
| `--format FORMAT` | `json` | Output format: `json`, `text` |
| `--timeout SECONDS` | `120` | Timeout for the agent |

**Examples:**

```bash
# Find security vulnerabilities
adversarial-debate analyse exploit src/api/

# Find logic bugs
adversarial-debate analyse break src/core/calculations.py

# Find resilience issues
adversarial-debate analyse chaos src/services/

# Find cryptographic weaknesses
adversarial-debate analyse crypto src/auth/
```

### orchestrate

Generate an attack plan without running analysis.

```bash
adversarial-debate orchestrate TARGET [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `TARGET` | File or directory to plan for |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output FILE` | — | Output file for attack plan |
| `--exposure LEVEL` | `internal` | Exposure level: `public`, `authenticated`, `internal` |
| `--time-budget SECONDS` | `600` | Time budget for planning |

**Examples:**

```bash
# Generate attack plan for public API
adversarial-debate orchestrate src/api/ --exposure public

# Save plan to file
adversarial-debate orchestrate src/ --output attack-plan.json
```

### verdict

Run the Arbiter on existing findings.

```bash
adversarial-debate verdict FINDINGS [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `FINDINGS` | Path to findings JSON file or bundle |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output FILE` | — | Output file for verdict |
| `--format FORMAT` | `json` | Output format: `json`, `text` |

**Examples:**

```bash
# Render verdict on findings
adversarial-debate verdict findings.json

# Render verdict on a bundle
adversarial-debate verdict output/run-123/bundle.json
```

### watch

Watch files for changes and re-analyse automatically.

```bash
adversarial-debate watch TARGET [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `TARGET` | Directory to watch |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--agent AGENT` | `exploit` | Agent to run on changes |
| `--debounce SECONDS` | `2` | Wait time after change before analysing |

**Examples:**

```bash
# Watch for changes and check for vulnerabilities
adversarial-debate watch src/ --agent exploit

# Watch with longer debounce
adversarial-debate watch src/ --debounce 5
```

### cache

Manage the analysis cache.

```bash
adversarial-debate cache SUBCOMMAND [OPTIONS]
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| `stats` | Show cache statistics |
| `clear` | Clear the entire cache |
| `cleanup` | Remove expired entries |

**Examples:**

```bash
# View cache statistics
adversarial-debate cache stats

# Clear the cache
adversarial-debate cache clear

# Remove old entries
adversarial-debate cache cleanup --older-than 7d
```

## Environment Variables

These environment variables configure the framework:

### Provider Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | Provider: `anthropic`, `openai`, `azure`, `ollama`, `mock` |
| `LLM_MODEL` | — | Model override (provider-specific) |
| `LLM_TIMEOUT` | `120` | Request timeout in seconds |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `AZURE_OPENAI_API_KEY` | — | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | — | Azure OpenAI deployment name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

### Framework Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ADVERSARIAL_DEBUG` | `false` | Enable debug mode |
| `ADVERSARIAL_LOG_LEVEL` | `INFO` | Log level |
| `ADVERSARIAL_LOG_FORMAT` | `text` | Log format: `text`, `json` |
| `ADVERSARIAL_OUTPUT_DIR` | `./output` | Default output directory |
| `ADVERSARIAL_BEAD_LEDGER` | `./beads/ledger.jsonl` | Bead ledger path |

See [Configuration Guide](configuration.md) for complete details.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (PASS verdict or successful completion) |
| `1` | Error (invalid input, configuration error, runtime error) |
| `2` | Blocked (BLOCK verdict — security issues found) |
| `3` | Warning (WARN verdict, when `--fail-on warn` is set) |

## Output Files

When running the full pipeline, these files are created in the output directory:

| File | Description |
|------|-------------|
| `attack_plan.json` | ChaosOrchestrator's attack strategy |
| `exploit_findings.json` | ExploitAgent findings |
| `break_findings.json` | BreakAgent findings |
| `chaos_findings.json` | ChaosAgent findings |
| `crypto_findings.json` | CryptoAgent findings |
| `findings.json` | Combined findings (pre-debate) |
| `findings.debated.json` | Combined findings after cross-examination (optional) |
| `verdict.json` | Arbiter verdict and remediation tasks |
| `bundle.json` | Canonical results bundle |

## Configuration File

Instead of environment variables, you can use a JSON configuration file:

```bash
adversarial-debate run src/ --config config.json
```

See [Configuration Guide](configuration.md) for the file format.

## Shell Completion

Generate shell completion scripts:

```bash
# Bash
adversarial-debate --completion bash > /etc/bash_completion.d/adversarial-debate

# Zsh
adversarial-debate --completion zsh > ~/.zsh/completions/_adversarial-debate

# Fish
adversarial-debate --completion fish > ~/.config/fish/completions/adversarial-debate.fish
```

## See Also

- [Configuration Guide](configuration.md) — All configuration options
- [Output Formats](output-formats.md) — Understanding output files
- [CI/CD Integration](../integration/ci-cd.md) — Automation workflows
