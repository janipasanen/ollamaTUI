"""Base tool classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None


class BaseTool(ABC):
    """Base class for all tools."""
    
    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = []
    
    def __init__(self, working_dir: str = ".", allowed_dirs: List[str] = None):
        self.working_dir = working_dir
        self.allowed_dirs = allowed_dirs or []
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool schema for LLM function calling."""
        properties = {}
        required = []
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
    
    def validate_path(self, path: str) -> str:
        """Validate and resolve a path within allowed directories."""
        from pathlib import Path
        import os
        
        # Expand user and resolve
        path = os.path.expanduser(path)
        path = os.path.normpath(path)
        
        # If relative, make it relative to working_dir
        if not os.path.isabs(path):
            path = os.path.join(self.working_dir, path)
        
        # Check if path is within allowed directories
        allowed = [os.path.expanduser(d) for d in self.allowed_dirs]
        allowed.append(os.path.expanduser(self.working_dir))
        
        path_abs = os.path.abspath(path)
        for allowed_dir in allowed:
            allowed_abs = os.path.abspath(allowed_dir)
            if path_abs.startswith(allowed_abs + os.sep) or path_abs == allowed_abs:
                return path
        
        raise PermissionError(f"Path '{path}' is not within allowed directories")


class ApprovalRequired(Exception):
    """Exception raised when tool execution requires approval."""
    def __init__(self, tool_name: str, params: Dict[str, Any], reason: str):
        self.tool_name = tool_name
        self.params = params
        self.reason = reason
        super().__init__(f"Approval required for {tool_name}: {reason}")
