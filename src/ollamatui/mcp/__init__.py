"""MCP (Model Context Protocol) server support for OllamaTUI."""

from ollamatui.mcp.server import MCPServer
from ollamatui.mcp.types import (
    MCPTool,
    MCPToolResult,
    MCPCapabilities,
    MCPListToolsResult,
    MPCallToolResult,
)

__all__ = [
    "MCPServer",
    "MCPTool",
    "MCPToolResult",
    "MCPCapabilities",
    "MCPListToolsResult",
    "MPCallToolResult",
]