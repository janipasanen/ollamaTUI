"""MCP (Model Context Protocol) type definitions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json


@dataclass
class MCPTool:
    """Represents an MCP tool definition."""
    
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPToolResult:
    """Result of an MCP tool execution."""
    
    content: List[Dict[str, Any]]
    is_error: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        return {
            "content": self.content,
            "isError": self.is_error,
        }
    
    @classmethod
    def text(cls, text: str, is_error: bool = False) -> "MCPToolResult":
        """Create a text result."""
        return cls(
            content=[{"type": "text", "text": text}],
            is_error=is_error,
        )


@dataclass
class MCPCapabilities:
    """MCP server capabilities."""
    
    tools: bool = True
    resources: bool = False
    prompts: bool = False
    logging: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        return {
            "capabilities": {
                "tools": {"listChanged": False} if self.tools else None,
                "resources": {"subscribe": False, "listChanged": False} if self.resources else None,
                "prompts": {"listChanged": False} if self.prompts else None,
                "logging": {} if self.logging else None,
            },
            "protocolVersion": "2024-11-05",
        }


@dataclass
class MCPListToolsResult:
    """Result of listing tools."""
    
    tools: List[MCPTool]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        return {
            "tools": [tool.to_dict() for tool in self.tools],
        }


@dataclass
class MPCallToolResult:
    """Result of calling a tool."""
    
    content: List[Dict[str, Any]]
    is_error: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        return {
            "content": self.content,
            "isError": self.is_error,
        }


@dataclass
class MCPRequest:
    """An MCP JSON-RPC request."""
    
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method", ""),
            params=data.get("params", {}),
        )


@dataclass
class MCPResponse:
    """An MCP JSON-RPC response."""
    
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP protocol format."""
        data = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            data["id"] = self.id
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())