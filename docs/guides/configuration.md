# Configuration Guide

Adversarial Debate can be configured through environment variables, configuration files, or command-line options.

## Configuration Precedence

Configuration values are applied in this order (later overrides earlier):

1. Built-in defaults
2. Configuration file (`--config`)
3. Environment variables
4. Command-line options

## Environment Variables

### Provider Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | LLM provider to use |
| `LLM_MODEL` | Provider default | Model name override |
| `LLM_TIMEOUT` | `120` | Request timeout (seconds) |

> Sampling temperature, max output tokens, and retry counts are not read from
> the environment — set them in a [configuration file](#configuration-file)
> under the `provider` block.

### Provider API Keys

| Variable | Required For | Description |
|----------|--------------|-------------|
| `ANTHROPIC_API_KEY` | `anthropic` | Your Anthropic API key |
| `OPENAI_API_KEY` | `openai` | Your OpenAI API key |
| `AZURE_OPENAI_API_KEY` | `azure` | Your Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | `azure` | Azure endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | `azure` | Azure deployment name |
| `OLLAMA_BASE_URL` | `ollama` | Ollama server URL (default: `http://localhost:11434`) |

### Framework Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ADVERSARIAL_DEBUG` | `false` | Enable debug mode |
| `ADVERSARIAL_DRY_RUN` | `false` | Enable dry-run mode |
| `ADVERSARIAL_LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `ADVERSARIAL_LOG_FORMAT` | `text` | Log format (`text` or `json`) |
| `ADVERSARIAL_OUTPUT_DIR` | `./output` | Default output directory |
| `ADVERSARIAL_BEAD_LEDGER` | `./beads/ledger.jsonl` | Bead ledger file path |
| `ADVERSARIAL_CACHE_DIR` | `.adversarial-cache` | Incremental-analysis cache directory |

> Sandbox behaviour (Docker image, memory/CPU limits, network access, timeouts)
> is configured through the `sandbox` block of a
> [configuration file](#configuration-file), not via environment variables.

## Configuration File

For complex configurations, use a JSON configuration file:

```json
{
  "provider": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "timeout_seconds": 120,
    "max_retries": 3,
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "sandbox": {
    "use_docker": true,
    "docker_image": "python:3.11-slim",
    "memory_limit": "512m",
    "cpu_limit": 1.0,
    "timeout_seconds": 60,
    "network_enabled": false,
    "use_subprocess": true
  },
  "output_dir": "./output",
  "bead_ledger_path": "./beads/ledger.jsonl",
  "debug": false,
  "dry_run": false
}
```

> The loader recognises the `provider`, `logging`, `sandbox`, `debug`,
> `dry_run`, `output_dir`, `bead_ledger_path`, and `cache_dir` keys (see
> [`schemas/config.schema.json`](../../schemas/config.schema.json)). Unknown
> keys are ignored.

Save this as `config.json` and use it:

```bash
adversarial-debate run src/ --config config.json
```

## Using a .env File

For environment variables, you can use a `.env` file:

```bash
# .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

ADVERSARIAL_LOG_LEVEL=DEBUG
ADVERSARIAL_OUTPUT_DIR=./security-results
```

The framework automatically loads `.env` from the current directory.

## Provider Configuration

### Anthropic (Default)

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: specific model
export LLM_MODEL=claude-sonnet-4-20250514
```

Available models:
- `claude-sonnet-4-20250514` (default for HOSTED_LARGE)
- `claude-3-5-haiku-20241022` (default for HOSTED_SMALL)
- `claude-3-haiku-20240307` (default for LOCAL_SMALL)

### OpenAI

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Optional: specific model
export LLM_MODEL=gpt-4-turbo
```

Available models:
- `gpt-4-turbo` (default for HOSTED_LARGE)
- `gpt-4o-mini` (default for HOSTED_SMALL)

### Azure OpenAI

```bash
export LLM_PROVIDER=azure
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

### Ollama (Local)

```bash
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434

# Optional: specific model
export LLM_MODEL=llama3.1
```

Available models depend on what you've pulled:
```bash
ollama pull llama3.1
ollama pull codellama
```

### Mock (Testing)

```bash
export LLM_PROVIDER=mock
```

No API key required. Produces deterministic results for testing.

## Advanced Configuration

### Model Tiers

The framework uses different model tiers for different tasks:

| Tier | Default (Anthropic) | Purpose |
|------|---------------------|---------|
| `HOSTED_LARGE` | Claude Sonnet | Deep analysis (ExploitAgent, BreakAgent, Arbiter) |
| `HOSTED_SMALL` | Claude Haiku | Faster tasks (ChaosOrchestrator, ChaosAgent) |

The tier-to-model mapping is built into each provider. To use a single
non-default model everywhere, set `provider.model` in your config file (or
`LLM_MODEL` in the environment).

### Rate Limiting

The provider retries failed requests; set the retry count in your config file:

```json
{
  "provider": {
    "max_retries": 5
  }
}
```

### Sandbox Hardening

For maximum security in the sandbox:

```json
{
  "sandbox": {
    "use_docker": true,
    "docker_image": "python:3.11-slim",
    "memory_limit": "128m",
    "cpu_limit": 0.25,
    "timeout_seconds": 10,
    "network_enabled": false,
    "read_only": true
  }
}
```

### Caching

Caching is **opt-in**. Pass `--cache` to `run` to reuse a previous run's agent
results when the target code is unchanged:

```bash
adversarial-debate run src/ --cache
```

The cache key is the analysed code plus the agent name, so it serves an
unchanged re-run of the same target and self-invalidates as soon as any analysed
file changes (it is whole-target, not per-file). A cache hit skips the agent —
and therefore its bead-ledger entries — which is why caching is off by default
for a security tool. Entries live under `ADVERSARIAL_CACHE_DIR`
(`.adversarial-cache` by default) with a 7-day TTL.

Inspect or clear the cache with the `cache` subcommands:

```bash
adversarial-debate cache stats
adversarial-debate cache cleanup   # remove expired entries
adversarial-debate cache clear     # remove everything
```

## Configuration Validation

Validate your configuration:

```bash
adversarial-debate --config config.json --dry-run run src/
```

This checks:
- Configuration file syntax
- Required API keys are present
- Provider connectivity
- Docker availability (if sandbox enabled)

## Environment-Specific Configuration

### Development

```bash
# .env.development
LLM_PROVIDER=mock
ADVERSARIAL_DEBUG=true
ADVERSARIAL_LOG_LEVEL=DEBUG
```

### CI/CD

```bash
# .env.ci
LLM_PROVIDER=anthropic
ADVERSARIAL_LOG_FORMAT=json
```

### Production

```bash
# .env.production
LLM_PROVIDER=anthropic
ADVERSARIAL_LOG_LEVEL=WARNING
ADVERSARIAL_LOG_FORMAT=json
```

## See Also

- [Provider Setup](providers/index.md) — Detailed provider configuration
- [CLI Reference](cli-reference.md) — Command-line options
- [CI/CD Integration](../integration/ci-cd.md) — CI configuration patterns
