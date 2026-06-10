"""Bash command execution tool."""

import asyncio
import shlex
from typing import List, Dict, Any, Optional
import os

from ollamatui.tools.base import BaseTool, ToolResult, ToolParameter, ApprovalRequired
from ollamatui.config import SandboxMode


class BashTool(BaseTool):
    """Tool for executing bash commands with approval system."""
    
    name = "bash"
    description = "Execute bash commands with configurable approval policies"
    parameters = [
        ToolParameter(name="command", type="string", description="Command to execute", required=True),
        ToolParameter(name="description", type="string", description="Description of what the command does"),
        ToolParameter(name="timeout", type="integer", description="Timeout in seconds", default=30),
        ToolParameter(name="working_dir", type="string", description="Working directory for command"),
    ]
    
    # Trusted commands that don't require approval
    TRUSTED_COMMANDS = {
        "ls", "cat", "head", "tail", "grep", "rg", "find", "which", "pwd",
        "echo", "printf", "date", "whoami", "id", "uname", "env", "printenv",
        "git status", "git diff", "git log", "git show", "git branch",
        "python3 -c", "python -c", "node -e", "npm list", "pip list",
        "cargo check", "go build", "make", "cmake", "ninja",
    }
    
    # Commands that are never allowed (dangerous)
    BLOCKED_COMMANDS = {
        "rm -rf /", "rm -rf /*", ":(){ :|:& };:", "mkfs", "dd if=",
        "chmod 777", "chown -R", "sudo ", "su ", "passwd", "userdel",
        "groupdel", "crontab -r", "shutdown", "reboot", "halt", "poweroff",
    }
    
    def __init__(
        self,
        working_dir: str = ".",
        allowed_dirs: List[str] = None,
        sandbox_mode: SandboxMode = SandboxMode.WORKSPACE_WRITE,
        approval_policy: str = "on-request",
    ):
        super().__init__(working_dir, allowed_dirs)
        self.sandbox_mode = sandbox_mode
        self.approval_policy = approval_policy
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute bash command with approval checks."""
        command = kwargs.get("command")
        description = kwargs.get("description", "")
        timeout = kwargs.get("timeout", 30)
        working_dir = kwargs.get("working_dir", self.working_dir)
        
        if not command:
            return ToolResult(success=False, error="Missing required parameter: command")
        
        # Check if command is blocked
        if self._is_blocked(command):
            return ToolResult(success=False, error=f"Command blocked for safety: {command}")
        
        # Check approval
        if self._requires_approval(command):
            if self.approval_policy == "never":
                return ToolResult(success=False, error="Approval required but policy is 'never'")
            elif self.approval_policy == "on-request":
                # In real implementation, this would prompt user
                raise ApprovalRequired(self.name, {"command": command}, "User approval required")
            elif self.approval_policy == "untrusted":
                # Only trusted commands allowed without approval
                raise ApprovalRequired(self.name, {"command": command}, "Command not in trusted list")
        
        # Validate working directory
        try:
            working_dir = self.validate_path(working_dir)
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        
        # Check sandbox restrictions
        if not self._check_sandbox(command, working_dir):
            return ToolResult(success=False, error="Command violates sandbox policy")
        
        # Execute command
        return await self._run_command(command, working_dir, timeout)
    
    def _is_blocked(self, command: str) -> bool:
        """Check if command is in blocked list."""
        cmd_lower = command.lower().strip()
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return True
        return False
    
    def _requires_approval(self, command: str) -> bool:
        """Check if command requires approval."""
        if self.approval_policy == "never":
            return False
        
        # Check if it's a trusted command
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return True
        
        base_cmd = cmd_parts[0]
        
        # Check exact match
        if command in self.TRUSTED_COMMANDS:
            return False
        
        # Check prefix match for common commands
        for trusted in self.TRUSTED_COMMANDS:
            if trusted.endswith(" ") and command.startswith(trusted):
                return False
            if command == trusted.split(" ")[0]:
                return False
        
        return True
    
    def _check_sandbox(self, command: str, working_dir: str) -> bool:
        """Check if command complies with sandbox policy."""
        if self.sandbox_mode == SandboxMode.DANGER_FULL_ACCESS:
            return True
        
        # For read-only, only allow read commands
        if self.sandbox_mode == SandboxMode.READ_ONLY:
            read_commands = {"ls", "cat", "head", "tail", "grep", "rg", "find", "which", "pwd", "git status", "git diff", "git log"}
            cmd_parts = shlex.split(command)
            if cmd_parts and cmd_parts[0] not in read_commands:
                return False
        
        # For workspace-write, ensure command doesn't write outside workspace
        if self.sandbox_mode == SandboxMode.WORKSPACE_WRITE:
            # This is a simplified check - in practice would need more sophisticated analysis
            write_commands = {">", ">>", "tee", "cp", "mv", "rm", "mkdir", "touch", "chmod", "chown"}
            cmd_parts = shlex.split(command)
            if any(part in write_commands for part in cmd_parts):
                # Allow if it's within working directory
                pass  # Simplified for now
        
        return True
    
    async def _run_command(
        self,
        command: str,
        working_dir: str,
        timeout: int,
    ) -> ToolResult:
        """Run the command and capture output."""
        try:
            # Use shell for proper command parsing
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PWD": working_dir},
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds",
                    metadata={"command": command, "timeout": timeout},
                )
            
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            
            return ToolResult(
                success=process.returncode == 0,
                output=stdout_str,
                error=stderr_str if process.returncode != 0 else None,
                metadata={
                    "command": command,
                    "returncode": process.returncode,
                    "working_dir": working_dir,
                },
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute command: {str(e)}",
                metadata={"command": command},
            )
    
    def get_trusted_commands(self) -> List[str]:
        """Get list of trusted commands."""
        return sorted(list(self.TRUSTED_COMMANDS))
    
    def add_trusted_command(self, command: str) -> None:
        """Add a command to trusted list."""
        self.TRUSTED_COMMANDS.add(command)
    
    def remove_trusted_command(self, command: str) -> None:
        """Remove a command from trusted list."""
        self.TRUSTED_COMMANDS.discard(command)
