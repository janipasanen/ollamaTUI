"""File operations tool."""

import os
import aiofiles
from pathlib import Path
from typing import Optional, List, Dict, Any
import difflib

from ollamatui.tools.base import BaseTool, ToolResult, ToolParameter


class FileTool(BaseTool):
    """Tool for file operations: read, write, edit, list, search."""
    
    name = "file"
    description = "Perform file operations: read, write, edit, list, search"
    parameters = [
        ToolParameter(name="operation", type="string", description="Operation to perform: read, write, edit, list, search", required=True),
        ToolParameter(name="path", type="string", description="File or directory path", required=True),
        ToolParameter(name="content", type="string", description="Content to write (for write/edit)"),
        ToolParameter(name="old_string", type="string", description="String to replace (for edit)"),
        ToolParameter(name="new_string", type="string", description="Replacement string (for edit)"),
        ToolParameter(name="pattern", type="string", description="Search pattern (for search)"),
        ToolParameter(name="recursive", type="boolean", description="Recursive search (for search)", default=False),
    ]
    
    # Trusted operations that don't require approval
    TRUSTED_OPERATIONS = {"read", "list", "search"}
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute file operation."""
        operation = kwargs.get("operation")
        path = kwargs.get("path")
        
        if not operation or not path:
            return ToolResult(success=False, error="Missing required parameters: operation and path")
        
        try:
            # Validate path
            validated_path = self.validate_path(path)
            
            if operation == "read":
                return await self._read(validated_path)
            elif operation == "write":
                content = kwargs.get("content", "")
                return await self._write(validated_path, content)
            elif operation == "edit":
                old_string = kwargs.get("old_string", "")
                new_string = kwargs.get("new_string", "")
                return await self._edit(validated_path, old_string, new_string)
            elif operation == "list":
                return await self._list(validated_path)
            elif operation == "search":
                pattern = kwargs.get("pattern", "")
                recursive = kwargs.get("recursive", False)
                return await self._search(validated_path, pattern, recursive)
            else:
                return ToolResult(success=False, error=f"Unknown operation: {operation}")
        
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"File operation failed: {str(e)}")
    
    async def _read(self, path: str) -> ToolResult:
        """Read a file."""
        try:
            async with aiofiles.open(path, "r") as f:
                content = await f.read()
            return ToolResult(
                success=True,
                output=content,
                metadata={"path": path, "size": len(content)}
            )
        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: {path}")
        except IsADirectoryError:
            return ToolResult(success=False, error=f"Path is a directory: {path}")
    
    async def _write(self, path: str, content: str) -> ToolResult:
        """Write a file."""
        # Create directory if needed
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        async with aiofiles.open(path, "w") as f:
            await f.write(content)
        
        return ToolResult(
            success=True,
            output=f"Written {len(content)} bytes to {path}",
            metadata={"path": path, "size": len(content)}
        )
    
    async def _edit(self, path: str, old_string: str, new_string: str) -> ToolResult:
        """Edit a file by replacing old_string with new_string."""
        try:
            async with aiofiles.open(path, "r") as f:
                content = await f.read()
        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: {path}")
        
        if old_string not in content:
            return ToolResult(success=False, error=f"String not found in file: {old_string[:50]}...")
        
        # Count occurrences
        count = content.count(old_string)
        if count > 1:
            return ToolResult(success=False, error=f"String occurs {count} times, please be more specific")
        
        new_content = content.replace(old_string, new_string)
        
        async with aiofiles.open(path, "w") as f:
            await f.write(new_content)
        
        # Generate diff
        diff = self._generate_diff(content, new_content, path)
        
        return ToolResult(
            success=True,
            output=f"Edited {path}",
            metadata={"path": path, "diff": diff, "replacements": 1}
        )
    
    async def _list(self, path: str) -> ToolResult:
        """List directory contents."""
        try:
            path_obj = Path(path)
            if not path_obj.is_dir():
                return ToolResult(success=False, error=f"Path is not a directory: {path}")
            
            items = []
            for item in sorted(path_obj.iterdir()):
                if item.name.startswith("."):
                    continue
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            
            return ToolResult(
                success=True,
                output=items,
                metadata={"path": path, "count": len(items)}
            )
        except PermissionError:
            return ToolResult(success=False, error=f"Permission denied: {path}")
    
    async def _search(self, path: str, pattern: str, recursive: bool) -> ToolResult:
        """Search for pattern in files."""
        import fnmatch
        
        path_obj = Path(path)
        if not path_obj.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")
        
        results = []
        
        if path_obj.is_file():
            files = [path_obj]
        else:
            if recursive:
                files = list(path_obj.rglob("*"))
            else:
                files = list(path_obj.glob("*"))
            files = [f for f in files if f.is_file() and not f.name.startswith(".")]
        
        for file_path in files:
            try:
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if pattern.lower() in line.lower():
                        results.append({
                            "file": str(file_path),
                            "line": i + 1,
                            "content": line.strip(),
                        })
            except Exception:
                continue  # Skip binary files or unreadable files
        
        return ToolResult(
            success=True,
            output=results,
            metadata={"path": path, "pattern": pattern, "matches": len(results)}
        )
    
    def _generate_diff(self, old: str, new: str, path: str) -> str:
        """Generate a unified diff."""
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        diff = difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
        return "".join(diff)
    
    def requires_approval(self, operation: str) -> bool:
        """Check if operation requires approval."""
        return operation not in self.TRUSTED_OPERATIONS
