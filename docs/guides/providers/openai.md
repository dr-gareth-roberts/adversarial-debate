# OpenAI Provider

OpenAI provides GPT-4 and other models as an alternative to the default Anthropic provider.

## Quick Setup

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
```

## Installation

OpenAI support is an optional dependency:

```bash
# Install with OpenAI support
uv add "adversarial-debate[openai]"

# Or install all providers
uv add "adversarial-debate[all-providers]"
```

## Getting an API Key

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new secret key
5. Copy the key (it starts with `sk-`)

**Important:** Store your API key securely. Never commit it to version control.

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | — | Set to `openai` |
| `OPENAI_API_KEY` | Yes | — | Your API key |
| `OPENAI_ORG_ID` | No | — | Organisation ID (if applicable) |
| `OPENAI_BASE_URL` | No | — | Custom API base URL |
| `LLM_MODEL` | No | See below | Model override |
| `LLM_TIMEOUT` | No | `120` | Request timeout (seconds) |

### Configuration File

```json
{
  "provider": {
    "provider": "openai",
    "api_key": "${OPENAI_API_KEY}",
    "model": "gpt-4-turbo",
    "timeout_seconds": 120,
    "temperature": 0.7,
    "max_tokens": 4096,
    "extra": {
      "organization": "org-..."
    }
  }
}
```

## Available Models

| Tier | Default Model | Use Case |
|------|---------------|----------|
| `HOSTED_LARGE` | `gpt-4-turbo` | ExploitAgent, BreakAgent, CryptoAgent, Arbiter |
| `HOSTED_SMALL` | `gpt-4o-mini` | ChaosOrchestrator, ChaosAgent |

### Recommended Models

| Model | Best For |
|-------|----------|
| `gpt-4-turbo` | Best overall quality |
| `gpt-4o` | Balanced speed and quality |
| `gpt-4o-mini` | Faster, lower cost |

### Overriding the Model

```bash
export LLM_MODEL=gpt-4-turbo
```

Or per-tier:

```json
{
  "provider": {
    "provider": "openai",
    "model_overrides": {
      "HOSTED_LARGE": "gpt-4-turbo",
      "HOSTED_SMALL": "gpt-4o-mini"
    }
  }
}
```

## Cost Estimation

Approximate costs per analysis (varies by code size):

| Code Size | GPT-4 Turbo | GPT-4o-mini |
|-----------|-------------|-------------|
| Small file | ~$0.02-0.03 | ~$0.001-0.005 |
| Medium file | ~$0.05-0.10 | ~$0.005-0.02 |
| Large file | ~$0.10-0.20 | ~$0.02-0.05 |

## OpenAI-Compatible APIs

The OpenAI provider works with OpenAI-compatible APIs:

### Together AI

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-together-key
export OPENAI_BASE_URL=https://api.together.xyz/v1
export LLM_MODEL=meta-llama/Llama-3-70b-chat-hf
```

### Groq

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-groq-key
export OPENAI_BASE_URL=https://api.groq.com/openai/v1
export LLM_MODEL=llama-3.1-70b-versatile
```

### Local vLLM Server

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=not-needed
export OPENAI_BASE_URL=http://localhost:8000/v1
export LLM_MODEL=your-model-name
```

## Troubleshooting

### "Invalid API Key"

Verify your key:

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### "Module 'openai' not found"

Install the optional dependency:

```bash
uv add "adversarial-debate[openai]"
```

### "Rate Limit Exceeded"

Options:
1. Wait and retry (automatic)
2. Reduce `--parallel`
3. Upgrade your OpenAI tier

### JSON Mode Issues

OpenAI's JSON mode can sometimes fail. The framework handles this, but if you see parsing errors:

```json
{
  "provider": {
    "extra": {
      "response_format": {"type": "json_object"}
    }
  }
}
```

## See Also

- [Provider Index](index.md) — Compare all providers
- [Azure OpenAI](azure.md) — Enterprise OpenAI option
- [Configuration Guide](../configuration.md) — All options
