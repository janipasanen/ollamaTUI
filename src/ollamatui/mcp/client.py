"""MCP (Model Context Protocol) client implementation."""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ollamatui.tools.base import BaseTool, ToolResult, ToolParameter


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # stdio or sse
    url: Optional[str] = None  # for SSE transport


@dataclass
class MCPTool:
    """An MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class MCPClient:
    """Client for connecting to MCP servers."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.tools: Dict[str, MCPTool] = {}  # tool_name -> MCPTool
        self._initialized = False
    
    async def add_server(self, config: MCPServerConfig) -> bool:
        """Add and connect to an MCP server."""
        if config.transport == "stdio":
            return await self._connect_stdio(config)
        elif config.transport == "sse":
            return await self._connect_sse(config)
        else:
            raise ValueError(f"Unknown transport: {config.transport}")
    
    async def _connect_stdio(self, config: MCPServerConfig) -> bool:
        """Connect to MCP server via stdio."""
        try:
            # Prepare environment
            env = {**os.environ, **config.env}
            
            # Start process
            process = await asyncio.create_subprocess_exec(
                config.command,
                *config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            self.processes[config.name] = process
            
            # Initialize connection
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "OllamaTUI",
                        "version": "0.1.0",
                    },
                },
            }
            
            await self._send_request(process, init_request)
            response = await self._read_response(process)
            
            if "error" in response:
                raise Exception(f"MCP init failed: {response['error']}")
            
            # List tools
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
            
            await self._send_request(process, tools_request)
            response = await self._read_response(process)
            
            if "result" in response and "tools" in response["result"]:
                for tool_data in response["result"]["tools"]:
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_name=config.name,
                    )
                    self.tools[f"{config.name}.{tool.name}"] = tool
            
            self.servers[config.name] = config
            return True
            
        except Exception as e:
            print(f"Failed to connect to MCP server {config.name}: {e}")
            return False
    
    async def _connect_sse(self, config: MCPServerConfig) -> bool:
        """Connect to MCP server via SSE."""
        # Placeholder for SSE transport
        # Would require httpx with SSE support
        return False
    
    async def _send_request(self, process: asyncio.subprocess.Process, request: Dict[str, Any]) -> None:
        """Send JSON-RPC request to process."""
        data = json.dumps(request) + "\n"
        process.stdin.write(data.encode())
        await process.stdin.drain()
    
    async def _read_response(self, process: asyncio.subprocess.Process) -> Dict[str, Any]:
        """Read JSON-RPC response from process."""
        line = await process.stdout.readline()
        if not line:
            return {}
        return json.loads(line.decode().strip())
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call an MCP tool."""
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")
        
        tool = self.tools[tool_name]
        process = self.processes.get(tool.server_name)
        
        if not process:
            return ToolResult(success=False, error=f"Server not connected: {tool.server_name}")
        
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool.name,
                "arguments": arguments,
            },
        }
        
        try:
            await self._send_request(process, request)
            response = await self._read_response(process)
            
            if "error" in response:
                return ToolResult(success=False, error=response["error"].get("message", "Unknown error"))
            
            result = response.get("result", {})
            return ToolResult(
                success=True,
                output=result.get("content", []),
                metadata={"tool": tool_name, "server": tool.server_name},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Tool call failed: {str(e)}")
    
    def get_available_tools(self) -> List[MCPTool]:
        """Get list of available MCP tools."""
        return list(self.tools.values())
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for an MCP tool."""
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            return {
                "name": tool_name,
                "description": tool.description,
                "parameters": tool.input_schema,
            }
        return None
    
    async def close(self) -> None:
        """Close all connections."""
        for name, process in self.processes.items():
            try:
                process.terminate()
                await process.wait()
            except Exception:
                pass
        self.processes.clear()
        self.tools.clear()
        self.servers.clear()
