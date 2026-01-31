# Provider Setup

Adversarial Debate supports multiple LLM providers. This guide helps you choose and configure the right one for your needs.

## Available Providers

| Provider | Best For | API Key Required | Local Option |
|----------|----------|------------------|--------------|
| [Anthropic](anthropic.md) | Production use (default) | Yes | No |
| [OpenAI](openai.md) | Alternative cloud provider | Yes | No |
| [Azure OpenAI](azure.md) | Enterprise/compliance | Yes | No |
| [Ollama](ollama.md) | Local/air-gapped environments | No | Yes |
| [Mock](mock.md) | Testing and demos | No | Yes |

## Quick Comparison

### Quality and Capability

| Provider | Security Analysis | Logic Bug Detection | Speed |
|----------|-------------------|---------------------|-------|
| Anthropic | Excellent | Excellent | Fast |
| OpenAI | Very Good | Very Good | Fast |
| Azure OpenAI | Very Good | Very Good | Fast |
| Ollama | Varies by model | Varies by model | Varies |
| Mock | Deterministic | Deterministic | Instant |

### Cost Considerations

| Provider | Pricing Model | Approximate Cost* |
|----------|---------------|-------------------|
| Anthropic | Per token | ~$0.01-0.03 per analysis |
| OpenAI | Per token | ~$0.01-0.03 per analysis |
| Azure OpenAI | Per token | Similar to OpenAI |
| Ollama | Free (local compute) | Electricity only |
| Mock | Free | Free |

*Costs vary significantly based on code size and complexity.

### Compliance and Data Handling

| Provider | Data Retention | Compliance |
|----------|----------------|------------|
| Anthropic | No training on API data | SOC 2, GDPR |
| OpenAI | No training on API data | SOC 2, GDPR |
| Azure OpenAI | Enterprise controls | SOC 2, HIPAA, FedRAMP |
| Ollama | Fully local | Complete control |
| Mock | No data sent | N/A |

## Choosing a Provider

### For Production

**Anthropic (Recommended)**
- Best overall quality for security analysis
- Claude models excel at nuanced code understanding
- Fast response times

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

### For Enterprise/Compliance

**Azure OpenAI**
- Enterprise security controls
- Data residency options
- HIPAA, FedRAMP compliance available

```bash
export LLM_PROVIDER=azure
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

### For Air-Gapped Environments

**Ollama**
- Runs entirely locally
- No data leaves your network
- Requires capable hardware

```bash
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
```

### For Testing and CI

**Mock**
- No API key needed
- Deterministic results
- Instant responses

```bash
export LLM_PROVIDER=mock
```

## Provider-Specific Guides

- [Anthropic Setup](anthropic.md) — Default provider configuration
- [OpenAI Setup](openai.md) — OpenAI API configuration
- [Azure OpenAI Setup](azure.md) — Enterprise Azure configuration
- [Ollama Setup](ollama.md) — Local LLM configuration
- [Mock Provider](mock.md) — Testing and demo configuration

## Switching Providers

You can switch providers at runtime using environment variables:

```bash
# Use Anthropic
LLM_PROVIDER=anthropic adversarial-debate run src/

# Use OpenAI
LLM_PROVIDER=openai adversarial-debate run src/

# Use Ollama
LLM_PROVIDER=ollama adversarial-debate run src/
```

Or in a configuration file:

```json
{
  "provider": {
    "provider": "anthropic"
  }
}
```

## See Also

- [Configuration Guide](../configuration.md) — All configuration options
- [Troubleshooting](../../support/troubleshooting.md) — Common provider issues
