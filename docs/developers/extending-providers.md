# Extending Providers

Create custom LLM providers to integrate with new backends.

## Overview

Providers abstract LLM communication. Creating a custom provider allows you to:
- Use a new LLM service
- Add custom authentication
- Implement caching or routing
- Support specialised deployment

## The Provider Interface

All providers implement the `LLMProvider` abstract base class:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from adversarial_debate.providers.base import (
    LLMProvider,
    Message,
    LLMResponse,
    ModelTier,
    ProviderConfig,
)


class LLMProvider(ABC):
    def __init__(self, config: ProviderConfig | None = None):
        self.config = config or ProviderConfig()

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion from the model."""
        ...

    @abstractmethod
    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Get the appropriate model name for a given tier."""
        ...
```

## Data Classes

### Message

```python
@dataclass
class Message:
    role: str      # "system", "user", or "assistant"
    content: str
```

### LLMResponse

```python
@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int]  # {"input_tokens": N, "output_tokens": M}
    finish_reason: str | None = None
    raw_response: Any = None
```

### ProviderConfig

```python
@dataclass
class ProviderConfig:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 120.0
    extra: dict[str, Any] = field(default_factory=dict)
```

### ModelTier

```python
class ModelTier(str, Enum):
    LOCAL_SMALL = "local_small"
    HOSTED_SMALL = "hosted_small"
    HOSTED_LARGE = "hosted_large"
```

## Creating a Custom Provider

Let's create a provider for a hypothetical "AcmeLLM" service.

### Step 1: Implement the Provider

```python
# src/adversarial_debate/providers/acme.py

import aiohttp
from typing import Any

from adversarial_debate.providers.base import (
    LLMProvider,
    LLMResponse,
    Message,
    ModelTier,
    ProviderConfig,
)


class AcmeProvider(LLMProvider):
    """Provider for AcmeLLM API."""

    DEFAULT_BASE_URL = "https://api.acme-llm.com/v1"

    MODEL_MAP = {
        ModelTier.HOSTED_LARGE: "acme-pro",
        ModelTier.HOSTED_SMALL: "acme-mini",
        ModelTier.LOCAL_SMALL: "acme-mini",
    }

    def __init__(self, config: ProviderConfig | None = None):
        super().__init__(config)
        self.base_url = self.config.base_url or self.DEFAULT_BASE_URL
        self.api_key = self.config.api_key

        if not self.api_key:
            raise ValueError("ACME_API_KEY is required")

    async def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        model = model or self.config.model or "acme-pro"
        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens

        # Build request payload
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Make request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ProviderError(f"Acme API error: {error_text}")

                data = await response.json()

        # Parse response
        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data["model"],
            usage={
                "input_tokens": data["usage"]["prompt_tokens"],
                "output_tokens": data["usage"]["completion_tokens"],
            },
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )

    def get_model_for_tier(self, tier: ModelTier) -> str:
        if self.config.model:
            return self.config.model
        return self.MODEL_MAP.get(tier, "acme-pro")
```

### Step 2: Register the Provider

```python
# src/adversarial_debate/providers/__init__.py

from .acme import AcmeProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "azure": AzureOpenAIProvider,
    "ollama": OllamaProvider,
    "mock": MockProvider,
    "acme": AcmeProvider,  # Add this
}


def get_provider(name: str, config: ProviderConfig | None = None) -> LLMProvider:
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}")
    return PROVIDERS[name](config)
```

### Step 3: Add Environment Variable Support

```python
# src/adversarial_debate/config.py

import os

# In Config.from_env() or similar
if provider_name == "acme":
    api_key = os.getenv("ACME_API_KEY")
```

### Step 4: Add Tests

```python
# tests/unit/test_providers/test_acme_provider.py

import pytest
from aioresponses import aioresponses

from adversarial_debate.providers import AcmeProvider, ProviderConfig, Message


@pytest.fixture
def provider():
    return AcmeProvider(ProviderConfig(api_key="test-key"))


@pytest.mark.asyncio
async def test_complete_success(provider):
    with aioresponses() as m:
        m.post(
            "https://api.acme-llm.com/v1/chat/completions",
            payload={
                "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
                "model": "acme-pro",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

        response = await provider.complete([
            Message(role="user", content="Hi")
        ])

        assert response.content == "Hello!"
        assert response.model == "acme-pro"


@pytest.mark.asyncio
async def test_model_tier_mapping(provider):
    from adversarial_debate.providers.base import ModelTier

    assert provider.get_model_for_tier(ModelTier.HOSTED_LARGE) == "acme-pro"
    assert provider.get_model_for_tier(ModelTier.HOSTED_SMALL) == "acme-mini"
```

## Error Handling

Handle API errors appropriately:

```python
from adversarial_debate.exceptions import ProviderError, RateLimitError

async def complete(self, messages: list[Message], **kwargs) -> LLMResponse:
    async with session.post(...) as response:
        if response.status == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise RateLimitError(f"Rate limited, retry after {retry_after}s")

        if response.status == 401:
            raise ProviderError("Invalid API key")

        if response.status >= 500:
            raise ProviderError(f"Server error: {response.status}")

        if response.status != 200:
            error = await response.text()
            raise ProviderError(f"API error: {error}")
```

## Retry Logic

Implement retry with exponential backoff:

```python
import asyncio
from typing import TypeVar

T = TypeVar("T")


async def with_retry(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> T:
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            await asyncio.sleep(delay)
        except ProviderError:
            raise


async def complete(self, messages: list[Message], **kwargs) -> LLMResponse:
    async def _call():
        # Actual API call
        ...

    return await with_retry(_call, max_retries=self.config.extra.get("max_retries", 3))
```

## Streaming Support (Optional)

For providers that support streaming:

```python
from typing import AsyncIterator


class StreamingProvider(LLMProvider):
    async def complete_stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        async with session.post(..., stream=True) as response:
            async for line in response.content:
                if line.startswith(b"data: "):
                    data = json.loads(line[6:])
                    if content := data.get("choices", [{}])[0].get("delta", {}).get("content"):
                        yield content
```

## Provider-Specific Configuration

Support provider-specific options via the `extra` dict:

```python
class AcmeProvider(LLMProvider):
    async def complete(self, messages: list[Message], **kwargs) -> LLMResponse:
        payload = {
            "model": model,
            "messages": [...],
        }

        # Provider-specific options
        if self.config.extra.get("use_cache"):
            payload["cache"] = True

        if top_p := self.config.extra.get("top_p"):
            payload["top_p"] = top_p
```

Usage:

```python
provider = get_provider(
    "acme",
    ProviderConfig(
        api_key="...",
        extra={"use_cache": True, "top_p": 0.9},
    ),
)
```

## Lazy Loading

For optional dependencies, use lazy loading:

```python
# src/adversarial_debate/providers/__init__.py

def get_provider(name: str, config: ProviderConfig | None = None) -> LLMProvider:
    if name == "acme":
        try:
            from .acme import AcmeProvider
        except ImportError:
            raise ImportError(
                "Acme provider requires acme-sdk. "
                "Install with: pip install adversarial-debate[acme]"
            )
        return AcmeProvider(config)

    # ... other providers
```

## Documentation

Update the provider documentation:

```markdown
# docs/guides/providers/acme.md

# Acme LLM Provider

Configure Adversarial Debate to use Acme LLM.

## Quick Setup

```bash
export LLM_PROVIDER=acme
export ACME_API_KEY=your-key
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ACME_API_KEY` | Yes | Your API key |
| `LLM_MODEL` | No | Model override |

## Available Models

| Model | Tier | Use Case |
|-------|------|----------|
| `acme-pro` | HOSTED_LARGE | Best quality |
| `acme-mini` | HOSTED_SMALL | Faster, cheaper |
```

## See Also

- [Provider Index](../guides/providers/index.md) — All providers
- [Python API Guide](python-api.md) — Using providers
- [Configuration Guide](../guides/configuration.md) — Provider settings
