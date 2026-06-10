"""Tests for Ollama providers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ollamatui.providers.base import ModelInfo, ChatMessage, ChatResponse
from ollamatui.providers.local import LocalOllamaProvider
from ollamatui.providers.cloud import CloudOllamaProvider
from ollamatui.providers.factory import create_provider
from ollamatui.config import Config, ProviderType


def test_model_info():
    """Test ModelInfo dataclass."""
    model = ModelInfo(
        name="test-model",
        size=1000,
        digest="abc123",
        modified_at="2024-01-01T00:00:00Z",
    )
    assert model.name == "test-model"
    assert model.is_cloud == False


def test_chat_message():
    """Test ChatMessage dataclass."""
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.images is None


def test_chat_response():
    """Test ChatResponse dataclass."""
    response = ChatResponse(
        model="test",
        message=ChatMessage(role="assistant", content="Hi"),
        done=True,
    )
    assert response.done == True


def test_create_local_provider():
    """Test creating local provider."""
    config = Config(provider=ProviderType.LOCAL, local_host="http://localhost:11434")
    provider = create_provider(config)
    assert isinstance(provider, LocalOllamaProvider)
    assert provider.provider_name == "local"


def test_create_cloud_provider():
    """Test creating cloud provider."""
    config = Config(provider=ProviderType.CLOUD, cloud_host="https://ollama.com", api_key="test-key")
    provider = create_provider(config)
    assert isinstance(provider, CloudOllamaProvider)
    assert provider.provider_name == "cloud"


def test_create_cloud_provider_without_key():
    """Test creating cloud provider without API key raises error."""
    config = Config(provider=ProviderType.CLOUD, api_key=None)
    try:
        provider = create_provider(config)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "API key is required" in str(e)


async def test_local_provider_list_models():
    """Test local provider list_models with mocked response."""
    provider = LocalOllamaProvider(host="http://localhost:11434")
    
    # Mock the HTTP client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {
                "name": "test-model",
                "size": 1000,
                "digest": "abc123",
                "modified_at": "2024-01-01T00:00:00Z",
                "details": {}
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response
    provider._client = mock_client
    
    models = await provider.list_models()
    assert len(models) == 1
    assert models[0].name == "test-model"
    
    await provider.close()


async def test_cloud_provider_requires_api_key():
    """Test cloud provider requires API key."""
    try:
        CloudOllamaProvider(api_key=None)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


async def test_parse_response():
    """Test response parsing."""
    provider = LocalOllamaProvider(host="http://localhost:11434")
    
    data = {
        "model": "test-model",
        "message": {"role": "assistant", "content": "Hello"},
        "done": True,
        "total_duration": 1000,
        "eval_count": 10,
    }
    
    response = provider._parse_response(data)
    assert response.model == "test-model"
    assert response.message.content == "Hello"
    assert response.done == True
    assert response.eval_count == 10
