"""Tests for provider implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from ollamatui.providers.base import ModelInfo, ChatMessage, ChatResponse
from ollamatui.providers.cloud import CloudOllamaProvider


def test_model_info_creation():
    """Test ModelInfo dataclass."""
    model = ModelInfo(
        name="test-model",
        size="7B",
        digest="abc123",
        modified_at="2024-01-01",
    )
    
    assert model.name == "test-model"
    assert model.size == "7B"
    assert model.digest == "abc123"
    assert model.modified_at == "2024-01-01"


def test_chat_message_creation():
    """Test ChatMessage dataclass."""
    msg = ChatMessage(role="user", content="Hello")
    
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.images is None


def test_chat_message_with_images():
    """Test ChatMessage with images."""
    msg = ChatMessage(
        role="user",
        content="What's in this image?",
        images=["base64imagedata"]
    )
    
    assert msg.role == "user"
    assert msg.content == "What's in this image?"
    assert msg.images == ["base64imagedata"]


def test_chat_response_creation():
    """Test ChatResponse dataclass."""
    response = ChatResponse(
        model="test-model",
        message=ChatMessage(role="assistant", content="Hello!"),
        done=False,
    )
    
    assert response.model == "test-model"
    assert response.message.content == "Hello!"
    assert response.done is False
    assert response.thinking is None
    assert response.tool_calls is None


def test_chat_response_with_thinking():
    """Test ChatResponse with thinking."""
    response = ChatResponse(
        model="test-model",
        message=ChatMessage(role="assistant", content=""),
        done=False,
        thinking="Let me think...",
    )
    
    assert response.thinking == "Let me think..."


def test_chat_response_with_tool_calls():
    """Test ChatResponse with tool calls."""
    tool_calls = [
        {
            "function": {
                "name": "bash",
                "arguments": {"command": "ls -la"}
            }
        }
    ]
    response = ChatResponse(
        model="test-model",
        message=ChatMessage(role="assistant", content=""),
        done=False,
        tool_calls=tool_calls,
    )
    
    assert response.tool_calls == tool_calls


@pytest.mark.asyncio
async def test_cloud_provider_parse_response():
    """Test CloudOllamaProvider response parsing."""
    provider = CloudOllamaProvider(api_key="test-key")
    
    # Test basic response
    data = {
        "model": "test-model",
        "message": {"role": "assistant", "content": "Hello!"},
        "done": False,
    }
    
    response = provider._parse_response(data)
    
    assert response.model == "test-model"
    assert response.message.content == "Hello!"
    assert response.done is False


@pytest.mark.asyncio
async def test_cloud_provider_parse_response_with_thinking():
    """Test CloudOllamaProvider response parsing with thinking."""
    provider = CloudOllamaProvider(api_key="test-key")
    
    data = {
        "model": "test-model",
        "message": {"role": "assistant", "content": ""},
        "thinking": "I am thinking...",
        "done": False,
    }
    
    response = provider._parse_response(data)
    
    assert response.thinking == "I am thinking..."


@pytest.mark.asyncio
async def test_cloud_provider_parse_response_with_tool_calls():
    """Test CloudOllamaProvider response parsing with tool calls."""
    provider = CloudOllamaProvider(api_key="test-key")
    
    data = {
        "model": "test-model",
        "message": {"role": "assistant", "content": ""},
        "tool_calls": [
            {"function": {"name": "bash", "arguments": {"command": "ls"}}}
        ],
        "done": False,
    }
    
    response = provider._parse_response(data)
    
    assert response.tool_calls is not None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["function"]["name"] == "bash"


def test_cloud_provider_get_schema():
    """Test CloudOllamaProvider tool schema generation."""
    provider = CloudOllamaProvider(api_key="test-key")
    
    # No tools by default for cloud provider
    # The schema would be generated from tool definitions
    assert True  # Placeholder for actual schema test


@pytest.mark.asyncio
async def test_cloud_provider_handles_null_content():
    """Test CloudOllamaProvider handles null content gracefully."""
    provider = CloudOllamaProvider(api_key="test-key")
    
    data = {
        "model": "test-model",
        "message": {"role": "assistant", "content": None},
        "done": False,
    }
    
    response = provider._parse_response(data)
    
    # Should convert None to empty string
    assert response.message.content == ""


@pytest.mark.asyncio
async def test_cloud_provider_handles_missing_message():
    """Test CloudOllamaProvider handles missing message."""
    provider = CloudOllamaProvider(api_key="test-key")
    
    data = {
        "model": "test-model",
        "done": False,
    }
    
    response = provider._parse_response(data)
    
    # Should create empty message
    assert response.message.role == "assistant"
    assert response.message.content == ""