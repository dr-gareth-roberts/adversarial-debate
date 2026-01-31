"""Provider construction helpers for the CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import Config

if TYPE_CHECKING:
    from .providers import LLMProvider


def _get_provider_from_config(config: Config) -> LLMProvider:
    from .providers import ProviderConfig as RuntimeProviderConfig
    from .providers import get_provider

    runtime_config = RuntimeProviderConfig(
        api_key=config.provider.api_key,
        base_url=config.provider.base_url,
        model=config.provider.model,
        temperature=config.provider.temperature,
        max_tokens=config.provider.max_tokens,
        timeout=float(config.provider.timeout_seconds),
        extra={"max_retries": config.provider.max_retries, **config.provider.extra},
    )
    return get_provider(config.provider.provider, runtime_config)
