"""MCP (Model Context Protocol) server implementation."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Callable, Awaitable
from pathlib import Path

from ollamatui.mcp.types import (
    MCPTool,
    MCPToolResult,
    MCPCapabilities,
    MCPListToolsResult,
    MPCallToolResult,
    MCPRequest,
    MCPResponse,
)
from ollamatui.tools import BashTool, FileTool, GitTool, WebSearchTool
from ollamatui.tools.base import ApprovalRequired


class MCPServer:
    """MCP server that exposes OllamaTUI tools."""
    
    def __init__(
        self,
        working_dir: str = ".",
        allowed_dirs: List[str] = None,
        approval_policy: str = "never",
    ):
        """Initialize MCP server.
        
        Args:
            working_dir: Working directory for tools
            allowed_dirs: Additional allowed directories
            approval_policy: Tool approval policy (never, on-request, untrusted)
        """
        self.working_dir = working_dir
        self.allowed_dirs = allowed_dirs or []
        self.approval_policy = approval_policy
        
        # Initialize tools
        self.tools = {
            "bash": BashTool(
                working_dir=working_dir,
                allowed_dirs=allowed_dirs,
                approval_policy=approval_policy,
            ),
            "file": FileTool(
                working_dir=working_dir,
                allowed_dirs=allowed_dirs,
            ),
            "git": GitTool(
                working_dir=working_dir,
                allowed_dirs=allowed_dirs,
            ),
            "web_search": WebSearchTool(),
        }
        
        # Build MCP tool definitions
        self._mcp_tools = self._build_tool_definitions()
        
        # Request handlers
        self._handlers: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            "shutdown": self._handle_shutdown,
        }
    
    def _build_tool_definitions(self) -> List[MCPTool]:
        """Build MCP tool definitions from OllamaTUI tools."""
        tools = []
        
        for name, tool in self.tools.items():
            schema = tool.get_schema()
            
            # Convert to MCP input schema format
            input_schema = {
                "type": "object",
                "properties": schema.get("parameters", {}).get("properties", {}),
                "required": schema.get("parameters", {}).get("required", []),
            }
            
            tools.append(MCPTool(
                name=name,
                description=tool.description,
                input_schema=input_schema,
            ))
        
        return tools
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        capabilities = MCPCapabilities()
        return capabilities.to_dict()
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        result = MCPListToolsResult(tools=self._mcp_tools)
        return result.to_dict()
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return MCPToolResult.text(
                f"Unknown tool: {tool_name}",
                is_error=True,
            ).to_dict()
        
        tool = self.tools[tool_name]
        
        try:
            result = await tool.execute(**arguments)
            
            if result.success:
                # Format output
                if isinstance(result.output, str):
                    output = result.output
                elif isinstance(result.output, list):
                    output = json.dumps(result.output, indent=2)
                else:
                    output = str(result.output)
                
                return MCPToolResult.text(output).to_dict()
            else:
                return MCPToolResult.text(
                    result.error or "Tool execution failed",
                    is_error=True,
                ).to_dict()
        
        except ApprovalRequired as e:
            return MCPToolResult.text(
                f"Approval required: {e.reason}",
                is_error=True,
            ).to_dict()
        
        except Exception as e:
            return MCPToolResult.text(
                f"Tool execution error: {str(e)}",
                is_error=True,
            ).to_dict()
    
    async def _handle_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shutdown request."""
        return {}
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request.
        
        Args:
            request: The MCP request
            
        Returns:
            MCP response
        """
        method = request.method
        params = request.params
        
        handler = self._handlers.get(method)
        
        if handler is None:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            )
        
        try:
            result = await handler(params)
            return MCPResponse(
                id=request.id,
                result=result,
            )
        
        except Exception as e:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
            )
    
    async def handle_json(self, json_str: str) -> str:
        """Handle a JSON request.
        
        Args:
            json_str: JSON string containing the request
            
        Returns:
            JSON string containing the response
        """
        try:
            data = json.loads(json_str)
            request = MCPRequest.from_dict(data)
            response = await self.handle_request(request)
            return response.to_json()
        
        except json.JSONDecodeError as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}",
                },
            })
    
    async def run_stdio(self):
        """Run MCP server using stdio transport.
        
        This reads JSON-RPC messages from stdin and writes responses to stdout.
        """
        import sys
        
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                
                json_str = line.decode("utf-8").strip()
                if not json_str:
                    continue
                
                response = await self.handle_json(json_str)
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
            
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                sys.stderr.flush()
    
    def get_tools_for_ollama(self) -> List[Dict[str, Any]]:
        """Get tools in Ollama format.
        
        This converts MCP tools to Ollama's tool format for use in chat.
        
        Returns:
            List of tools in Ollama format
        """
        ollama_tools = []
        
        for name, tool in self.tools.items():
            schema = tool.get_schema()
            
            # Convert to Ollama format
            ollama_tool = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": schema.get("parameters", {}),
                },
            }
            
            ollama_tools.append(ollama_tool)
        
        return ollama_tools


async def main():
    """Run MCP server."""
    import os
    
    working_dir = os.environ.get("OLLAMATUI_WORKING_DIR", ".")
    approval_policy = os.environ.get("OLLAMATUI_APPROVAL_POLICY", "never")
    
    server = MCPServer(
        working_dir=working_dir,
        approval_policy=approval_policy,
    )
    
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())