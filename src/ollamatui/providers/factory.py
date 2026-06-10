"""Provider factory for creating Ollama providers."""

from typing import Optional
from ollamatui.config import Config, ProviderType
from ollamatui.providers.base import BaseOllamaProvider
from ollamatui.providers.local import LocalOllamaProvider
from ollamatui.providers.cloud import CloudOllamaProvider


def create_provider(config: Config) -> BaseOllamaProvider:
    """Create a provider based on configuration."""
    if config.provider == ProviderType.CLOUD:
        return CloudOllamaProvider(
            host=config.cloud_host,
            api_key=config.api_key,
        )
    else:
        return LocalOllamaProvider(
            host=config.local_host,
        )


async def test_provider(config: Config) -> bool:
    """Test if a provider is accessible."""
    provider = create_provider(config)
    try:
        return await provider.check_connection()
    finally:
        await provider.close()
