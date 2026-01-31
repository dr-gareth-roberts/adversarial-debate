# Azure OpenAI Provider

Azure OpenAI provides enterprise-grade access to OpenAI models with additional security, compliance, and data residency features.

## Quick Setup

```bash
export LLM_PROVIDER=azure
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

## Prerequisites

1. An Azure subscription
2. Azure OpenAI resource created
3. Model deployment configured
4. API access enabled

## Installation

Azure OpenAI support is included with the OpenAI optional dependency:

```bash
uv add "adversarial-debate[openai]"
```

## Azure Portal Setup

### 1. Create an Azure OpenAI Resource

1. Go to [portal.azure.com](https://portal.azure.com/)
2. Search for "Azure OpenAI"
3. Click "Create"
4. Select subscription and resource group
5. Choose region (affects data residency)
6. Name your resource
7. Select pricing tier
8. Review and create

### 2. Deploy a Model

1. Open your Azure OpenAI resource
2. Go to "Model deployments"
3. Click "Create new deployment"
4. Select model (e.g., `gpt-4-turbo`)
5. Name your deployment
6. Set capacity (tokens per minute)

### 3. Get Your Credentials

1. In your Azure OpenAI resource, go to "Keys and Endpoint"
2. Copy Key 1 or Key 2
3. Copy the Endpoint URL
4. Note your deployment name

## Configuration Options

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | Set to `azure` |
| `AZURE_OPENAI_API_KEY` | Yes | Your Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | Yes | Your endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Your deployment name |
| `AZURE_OPENAI_API_VERSION` | No | API version (default: `2024-02-15-preview`) |
| `LLM_TIMEOUT` | No | Request timeout (seconds) |

### Configuration File

```json
{
  "provider": {
    "provider": "azure",
    "api_key": "${AZURE_OPENAI_API_KEY}",
    "base_url": "${AZURE_OPENAI_ENDPOINT}",
    "timeout_seconds": 120,
    "extra": {
      "deployment": "${AZURE_OPENAI_DEPLOYMENT}",
      "api_version": "2024-02-15-preview"
    }
  }
}
```

## Multiple Deployments

If you have different deployments for different model tiers:

```json
{
  "provider": {
    "provider": "azure",
    "base_url": "${AZURE_OPENAI_ENDPOINT}",
    "api_key": "${AZURE_OPENAI_API_KEY}",
    "extra": {
      "deployment": "gpt4-turbo-deployment",
      "deployment_overrides": {
        "HOSTED_SMALL": "gpt4-mini-deployment"
      }
    }
  }
}
```

## Compliance Features

Azure OpenAI provides enterprise compliance features:

| Feature | Benefit |
|---------|---------|
| Data residency | Choose where your data is processed |
| Private endpoints | VNet integration |
| Managed identity | No API keys needed |
| Content filtering | Configurable safety |
| Audit logging | Track all API calls |

### Using Managed Identity

For production, use Azure Managed Identity instead of API keys:

```python
from azure.identity import DefaultAzureCredential

# Configure in your environment
# The framework will use DefaultAzureCredential
```

```json
{
  "provider": {
    "provider": "azure",
    "base_url": "${AZURE_OPENAI_ENDPOINT}",
    "extra": {
      "deployment": "${AZURE_OPENAI_DEPLOYMENT}",
      "use_managed_identity": true
    }
  }
}
```

## Troubleshooting

### "Resource not found"

Check your endpoint URL:
- Must end with `/` or have no trailing slash consistently
- Format: `https://your-resource.openai.azure.com/`

### "Deployment not found"

Verify:
1. Deployment exists in Azure portal
2. Deployment name matches exactly (case-sensitive)
3. Model is deployed and ready

### "Access denied"

Check:
1. API key is correct
2. Key has access to the deployment
3. Resource is not restricted by IP/VNet

### "Content filtered"

Azure's content filters may block some security-related content. Options:
1. Request content filter modification from Azure
2. Adjust analysis prompts
3. Use a different provider for security testing

## Regional Availability

Azure OpenAI availability varies by region:

| Region | GPT-4 | GPT-4 Turbo |
|--------|-------|-------------|
| East US | Yes | Yes |
| West Europe | Yes | Yes |
| UK South | Yes | Yes |
| Japan East | Yes | Yes |

Check [Azure documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models) for current availability.

## See Also

- [Provider Index](index.md) — Compare all providers
- [OpenAI Provider](openai.md) — Standard OpenAI setup
- [Configuration Guide](../configuration.md) — All options
