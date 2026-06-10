"""Tests for MCP server implementation."""

import pytest
import json
from unittest.mock import AsyncMock, patch

from ollamatui.mcp.types import (
    MCPTool,
    MCPToolResult,
    MCPCapabilities,
    MCPListToolsResult,
    MCPRequest,
    MCPResponse,
)
from ollamatui.mcp.server import MCPServer


def test_mcp_tool_creation():
    """Test MCPTool creation."""
    tool = MCPTool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object", "properties": {"input": {"type": "string"}}},
    )
    
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert "input" in tool.input_schema["properties"]


def test_mcp_tool_to_dict():
    """Test MCPTool serialization."""
    tool = MCPTool(
        name="test",
        description="Test",
        input_schema={"type": "object"},
    )
    
    d = tool.to_dict()
    
    assert d["name"] == "test"
    assert d["description"] == "Test"
    assert d["inputSchema"]["type"] == "object"


def test_mcp_tool_result_text():
    """Test MCPToolResult text creation."""
    result = MCPToolResult.text("Hello, world!")
    
    assert result.is_error is False
    assert len(result.content) == 1
    assert result.content[0]["type"] == "text"
    assert result.content[0]["text"] == "Hello, world!"


def test_mcp_tool_result_error():
    """Test MCPToolResult error creation."""
    result = MCPToolResult.text("Error occurred", is_error=True)
    
    assert result.is_error is True
    assert result.content[0]["text"] == "Error occurred"


def test_mcp_capabilities():
    """Test MCPCapabilities creation."""
    caps = MCPCapabilities(tools=True)
    
    d = caps.to_dict()
    
    assert "capabilities" in d
    assert d["capabilities"]["tools"] is not None
    assert d["protocolVersion"] == "2024-11-05"


def test_mcp_request_from_dict():
    """Test MCPRequest parsing."""
    data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {"name": "test"},
    }
    
    request = MCPRequest.from_dict(data)
    
    assert request.jsonrpc == "2.0"
    assert request.id == 1
    assert request.method == "tools/list"
    assert request.params["name"] == "test"


def test_mcp_response_to_dict():
    """Test MCPResponse serialization."""
    response = MCPResponse(
        id=1,
        result={"tools": []},
    )
    
    d = response.to_dict()
    
    assert d["jsonrpc"] == "2.0"
    assert d["id"] == 1
    assert d["result"] == {"tools": []}


def test_mcp_response_error():
    """Test MCPResponse error serialization."""
    response = MCPResponse(
        id=1,
        error={"code": -32601, "message": "Method not found"},
    )
    
    d = response.to_dict()
    
    assert "error" in d
    assert d["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_mcp_server_initialize():
    """Test MCP server initialize."""
    server = MCPServer(working_dir=".")
    
    request = MCPRequest(id=1, method="initialize", params={})
    response = await server.handle_request(request)
    
    assert response.id == 1
    assert response.result is not None
    assert "capabilities" in response.result


@pytest.mark.asyncio
async def test_mcp_server_list_tools():
    """Test MCP server tools/list."""
    server = MCPServer(working_dir=".")
    
    request = MCPRequest(id=1, method="tools/list", params={})
    response = await server.handle_request(request)
    
    assert response.id == 1
    assert response.result is not None
    assert "tools" in response.result
    
    # Check that our tools are listed
    tool_names = [t["name"] for t in response.result["tools"]]
    assert "bash" in tool_names
    assert "file" in tool_names
    assert "git" in tool_names


@pytest.mark.asyncio
async def test_mcp_server_call_tool():
    """Test MCP server tools/call."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPServer(working_dir=tmpdir, approval_policy="never")
        
        request = MCPRequest(
            id=1,
            method="tools/call",
            params={
                "name": "bash",
                "arguments": {"command": "echo 'hello'"},
            },
        )
        
        response = await server.handle_request(request)
        
        assert response.id == 1
        assert response.result is not None
        assert response.result["isError"] is False
        assert "hello" in response.result["content"][0]["text"]


@pytest.mark.asyncio
async def test_mcp_server_call_unknown_tool():
    """Test MCP server calling unknown tool."""
    server = MCPServer(working_dir=".")
    
    request = MCPRequest(
        id=1,
        method="tools/call",
        params={
            "name": "unknown_tool",
            "arguments": {},
        },
    )
    
    response = await server.handle_request(request)
    
    assert response.id == 1
    assert response.result["isError"] is True
    assert "Unknown tool" in response.result["content"][0]["text"]


@pytest.mark.asyncio
async def test_mcp_server_handle_json():
    """Test MCP server JSON handling."""
    server = MCPServer(working_dir=".")
    
    json_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    })
    
    response = await server.handle_json(json_request)
    
    response_data = json.loads(response)
    assert response_data["jsonrpc"] == "2.0"
    assert response_data["id"] == 1
    assert "result" in response_data


def test_mcp_server_get_tools_for_ollama():
    """Test converting MCP tools to Ollama format."""
    server = MCPServer(working_dir=".")
    
    ollama_tools = server.get_tools_for_ollama()
    
    assert isinstance(ollama_tools, list)
    assert len(ollama_tools) >= 3  # bash, file, git
    
    # Check tool format
    for tool in ollama_tools:
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]