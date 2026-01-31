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
| `LLM_TEMPERATURE` | `0.7` | Sampling temperature |
| `LLM_MAX_TOKENS` | `4096` | Maximum output tokens |
| `LLM_MAX_RETRIES` | `3` | Maximum retry attempts |

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
| `ADVERSARIAL_CACHE_DIR` | `./cache` | Cache directory |
| `ADVERSARIAL_CACHE_TTL` | `86400` | Cache time-to-live (seconds) |

### Sandbox Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ADVERSARIAL_SANDBOX_DOCKER` | `true` | Use Docker for sandbox |
| `ADVERSARIAL_SANDBOX_IMAGE` | `python:3.11-slim` | Docker image for sandbox |
| `ADVERSARIAL_SANDBOX_MEMORY` | `256m` | Memory limit |
| `ADVERSARIAL_SANDBOX_CPU` | `0.5` | CPU limit |
| `ADVERSARIAL_SANDBOX_TIMEOUT` | `30` | Execution timeout (seconds) |
| `ADVERSARIAL_SANDBOX_NETWORK` | `false` | Allow network access |

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
  "cache": {
    "enabled": true,
    "directory": "./cache",
    "ttl_seconds": 86400
  },
  "output": {
    "directory": "./output",
    "bundle_file": "bundle.json"
  },
  "bead_ledger_path": "./beads/ledger.jsonl",
  "debug": false,
  "dry_run": false
}
```

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
- `claude-3-haiku-20240307` (default for HOSTED_SMALL)

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

Override the model for specific tiers in your config file:

```json
{
  "provider": {
    "provider": "anthropic",
    "model_overrides": {
      "HOSTED_LARGE": "claude-sonnet-4-20250514",
      "HOSTED_SMALL": "claude-3-haiku-20240307"
    }
  }
}
```

### Rate Limiting

Configure retry behaviour for rate limits:

```json
{
  "provider": {
    "max_retries": 5,
    "retry_delay_seconds": 2,
    "retry_exponential_base": 2
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
    "read_only": true,
    "drop_capabilities": true
  }
}
```

### Caching

Enable caching to avoid redundant LLM calls:

```json
{
  "cache": {
    "enabled": true,
    "directory": "./cache",
    "ttl_seconds": 86400,
    "max_size_mb": 1000
  }
}
```

View cache statistics:
```bash
adversarial-debate cache stats
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
ADVERSARIAL_SANDBOX_DOCKER=false
```

### Production

```bash
# .env.production
LLM_PROVIDER=anthropic
ADVERSARIAL_LOG_LEVEL=WARNING
ADVERSARIAL_LOG_FORMAT=json
ADVERSARIAL_CACHE_TTL=3600
```

## See Also

- [Provider Setup](providers/index.md) — Detailed provider configuration
- [CLI Reference](cli-reference.md) — Command-line options
- [CI/CD Integration](../integration/ci-cd.md) — CI configuration patterns
