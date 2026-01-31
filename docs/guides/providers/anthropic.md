# Anthropic Provider

Anthropic is the default and recommended provider for Adversarial Debate. Claude models excel at security analysis and code understanding.

## Quick Setup

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Getting an API Key

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (it starts with `sk-ant-`)

**Important:** Store your API key securely. Never commit it to version control.

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | — | Set to `anthropic` |
| `ANTHROPIC_API_KEY` | Yes | — | Your API key |
| `LLM_MODEL` | No | See below | Model override |
| `LLM_TIMEOUT` | No | `120` | Request timeout (seconds) |
| `LLM_TEMPERATURE` | No | `0.7` | Sampling temperature |
| `LLM_MAX_TOKENS` | No | `4096` | Maximum output tokens |

### Configuration File

```json
{
  "provider": {
    "provider": "anthropic",
    "api_key": "${ANTHROPIC_API_KEY}",
    "model": "claude-sonnet-4-20250514",
    "timeout_seconds": 120,
    "temperature": 0.7,
    "max_tokens": 4096,
    "max_retries": 3
  }
}
```

## Available Models

The framework automatically selects models based on task complexity:

| Tier | Default Model | Use Case |
|------|---------------|----------|
| `HOSTED_LARGE` | `claude-sonnet-4-20250514` | ExploitAgent, BreakAgent, CryptoAgent, Arbiter |
| `HOSTED_SMALL` | `claude-3-haiku-20240307` | ChaosOrchestrator, ChaosAgent |

### Overriding the Model

```bash
# Use a specific model for all tasks
export LLM_MODEL=claude-sonnet-4-20250514
```

Or per-tier in config:

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

## Cost Estimation

Approximate costs per analysis (varies by code size):

| Code Size | Approximate Cost |
|-----------|------------------|
| Small file (~100 lines) | ~$0.01-0.02 |
| Medium file (~500 lines) | ~$0.02-0.05 |
| Large file (~1000 lines) | ~$0.05-0.10 |
| Full pipeline (directory) | ~$0.10-0.50 |

**Tips for cost management:**
- Use `--skip-verdict` during development
- Use the mock provider for testing
- Set time budgets to limit analysis depth
- Use caching to avoid redundant calls

## Rate Limits

Anthropic applies rate limits based on your tier:

| Tier | Requests/minute | Tokens/minute |
|------|-----------------|---------------|
| Free | 5 | 25,000 |
| Build | 50 | 100,000 |
| Scale | 1,000+ | 1,000,000+ |

The framework automatically handles rate limiting with exponential backoff:

```json
{
  "provider": {
    "max_retries": 5,
    "retry_delay_seconds": 2
  }
}
```

## Troubleshooting

### "Invalid API Key"

Verify your key:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2024-01-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-3-haiku-20240307", "max_tokens": 10, "messages": [{"role": "user", "content": "Hi"}]}'
```

Common issues:
- Key starts with `sk-ant-` — correct format
- Key is copied completely (no truncation)
- Key is active (not revoked)

### "Rate Limit Exceeded"

Options:
1. Wait and retry (framework handles this automatically)
2. Increase `retry_delay_seconds`
3. Upgrade your Anthropic tier
4. Reduce `--parallel` to lower concurrent requests

### "Request Timeout"

Increase the timeout:

```bash
export LLM_TIMEOUT=300
```

Or in config:

```json
{
  "provider": {
    "timeout_seconds": 300
  }
}
```

### "Context Length Exceeded"

The code being analysed is too large. Options:
1. Analyse smaller files individually
2. Use `--files` to target specific files
3. Split large files before analysis

## Security Best Practices

1. **Use environment variables** — Never hardcode API keys
2. **Rotate keys regularly** — Create new keys periodically
3. **Use separate keys** — Different keys for dev/prod
4. **Monitor usage** — Check the Anthropic console for anomalies
5. **Set spending limits** — Configure budget alerts in the console

## Example Usage

```bash
# Basic usage
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
adversarial-debate run src/

# With specific model
LLM_MODEL=claude-sonnet-4-20250514 adversarial-debate run src/

# With increased timeout
LLM_TIMEOUT=300 adversarial-debate run large-codebase/
```

## See Also

- [Provider Index](index.md) — Compare all providers
- [Configuration Guide](../configuration.md) — All configuration options
- [Troubleshooting](../../support/troubleshooting.md) — Common issues
