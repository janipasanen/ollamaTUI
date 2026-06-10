"""Git integration tool."""

import asyncio
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from ollamatui.tools.base import BaseTool, ToolResult, ToolParameter


class GitTool(BaseTool):
    """Tool for Git operations."""
    
    name = "git"
    description = "Perform Git operations: status, diff, log, commit, branch, add, reset"
    parameters = [
        ToolParameter(name="operation", type="string", description="Operation: status, diff, log, commit, branch, add, reset, show", required=True),
        ToolParameter(name="path", type="string", description="Repository path (default: working_dir)"),
        ToolParameter(name="message", type="string", description="Commit message (for commit)"),
        ToolParameter(name="files", type="array", description="Files to add/stage (for add)", items={"type": "string"}),
        ToolParameter(name="branch", type="string", description="Branch name (for branch/checkout)"),
        ToolParameter(name="commit_hash", type="string", description="Commit hash (for show/reset)"),
        ToolParameter(name="limit", type="integer", description="Limit for log (default: 10)", default=10),
    ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute git operation."""
        operation = kwargs.get("operation")
        path = kwargs.get("path", self.working_dir)
        
        if not operation:
            return ToolResult(success=False, error="Missing required parameter: operation")
        
        try:
            # Validate path
            validated_path = self.validate_path(path)
            
            if operation == "status":
                return await self._status(validated_path)
            elif operation == "diff":
                return await self._diff(validated_path)
            elif operation == "log":
                limit = kwargs.get("limit", 10)
                return await self._log(validated_path, limit)
            elif operation == "commit":
                message = kwargs.get("message")
                if not message:
                    return ToolResult(success=False, error="Missing commit message")
                return await self._commit(validated_path, message)
            elif operation == "branch":
                branch = kwargs.get("branch")
                return await self._branch(validated_path, branch)
            elif operation == "add":
                files = kwargs.get("files", ["."])
                return await self._add(validated_path, files)
            elif operation == "reset":
                commit_hash = kwargs.get("commit_hash", "HEAD")
                return await self._reset(validated_path, commit_hash)
            elif operation == "show":
                commit_hash = kwargs.get("commit_hash", "HEAD")
                return await self._show(validated_path, commit_hash)
            elif operation == "checkout":
                branch = kwargs.get("branch")
                if not branch:
                    return ToolResult(success=False, error="Missing branch name")
                return await self._checkout(validated_path, branch)
            else:
                return ToolResult(success=False, error=f"Unknown operation: {operation}")
        
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Git operation failed: {str(e)}")
    
    async def _run_git(self, path: str, args: List[str]) -> tuple[int, str, str]:
        """Run git command and return (returncode, stdout, stderr)."""
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            process.returncode,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
    
    async def _status(self, path: str) -> ToolResult:
        """Get git status."""
        code, stdout, stderr = await self._run_git(path, ["status", "--porcelain"])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        # Parse porcelain output
        files = []
        for line in stdout.strip().split("\n"):
            if line:
                status = line[:2]
                filepath = line[3:]
                files.append({
                    "status": status.strip(),
                    "path": filepath,
                    "staged": status[0] != " " and status[0] != "?",
                    "unstaged": status[1] != " " and status[1] != "?",
                })
        
        return ToolResult(
            success=True,
            output=files,
            metadata={"path": path, "clean": len(files) == 0}
        )
    
    async def _diff(self, path: str) -> ToolResult:
        """Get git diff."""
        code, stdout, stderr = await self._run_git(path, ["diff"])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        return ToolResult(
            success=True,
            output=stdout,
            metadata={"path": path}
        )
    
    async def _log(self, path: str, limit: int) -> ToolResult:
        """Get git log."""
        code, stdout, stderr = await self._run_git(path, [
            "log",
            f"-{limit}",
            "--pretty=format:%H|%an|%ad|%s",
            "--date=short",
        ])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        commits = []
        for line in stdout.strip().split("\n"):
            if line:
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0][:8],
                        "full_hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    })
        
        return ToolResult(
            success=True,
            output=commits,
            metadata={"path": path, "count": len(commits)}
        )
    
    async def _commit(self, path: str, message: str) -> ToolResult:
        """Create a commit."""
        code, stdout, stderr = await self._run_git(path, ["commit", "-m", message])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        return ToolResult(
            success=True,
            output=stdout,
            metadata={"path": path}
        )
    
    async def _branch(self, path: str, branch: Optional[str]) -> ToolResult:
        """List or create branches."""
        if branch:
            # Create new branch
            code, stdout, stderr = await self._run_git(path, ["branch", branch])
        else:
            # List branches
            code, stdout, stderr = await self._run_git(path, ["branch", "-a"])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        branches = []
        for line in stdout.strip().split("\n"):
            if line:
                current = line.startswith("*")
                name = line[2:].strip() if current else line.strip()
                branches.append({
                    "name": name,
                    "current": current,
                })
        
        return ToolResult(
            success=True,
            output=branches,
            metadata={"path": path}
        )
    
    async def _add(self, path: str, files: List[str]) -> ToolResult:
        """Stage files."""
        code, stdout, stderr = await self._run_git(path, ["add"] + files)
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        return ToolResult(
            success=True,
            output=f"Staged {len(files)} file(s)",
            metadata={"path": path, "files": files}
        )
    
    async def _reset(self, path: str, commit_hash: str) -> ToolResult:
        """Reset to commit."""
        code, stdout, stderr = await self._run_git(path, ["reset", "--hard", commit_hash])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        return ToolResult(
            success=True,
            output=f"Reset to {commit_hash}",
            metadata={"path": path, "commit": commit_hash}
        )
    
    async def _show(self, path: str, commit_hash: str) -> ToolResult:
        """Show commit details."""
        code, stdout, stderr = await self._run_git(path, [
            "show",
            "--stat",
            commit_hash,
        ])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        return ToolResult(
            success=True,
            output=stdout,
            metadata={"path": path, "commit": commit_hash}
        )
    
    async def _checkout(self, path: str, branch: str) -> ToolResult:
        """Checkout branch."""
        code, stdout, stderr = await self._run_git(path, ["checkout", branch])
        
        if code != 0:
            return ToolResult(success=False, error=stderr)
        
        return ToolResult(
            success=True,
            output=f"Switched to branch {branch}",
            metadata={"path": path, "branch": branch}
        )
    
    async def is_git_repo(self, path: str) -> bool:
        """Check if path is a git repository."""
        code, _, _ = await self._run_git(path, ["rev-parse", "--git-dir"])
        return code == 0
    
    async def get_current_branch(self, path: str) -> Optional[str]:
        """Get current branch name."""
        code, stdout, _ = await self._run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if code == 0:
            return stdout.strip()
        return None
    
    async def get_remote_url(self, path: str) -> Optional[str]:
        """Get remote origin URL."""
        code, stdout, _ = await self._run_git(path, ["config", "--get", "remote.origin.url"])
        if code == 0:
            return stdout.strip()
        return None
