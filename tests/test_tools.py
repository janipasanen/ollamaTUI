"""Tests for agent tools."""

import tempfile
import os
from pathlib import Path

from ollamatui.tools.file import FileTool
from ollamatui.tools.bash import BashTool
from ollamatui.tools.git import GitTool
from ollamatui.config import SandboxMode


def test_file_tool_read_write():
    """Test file read and write operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        # Write a file
        result = tool.execute_sync(operation="write", path="test.txt", content="Hello World")
        assert result.success
        
        # Read the file
        result = tool.execute_sync(operation="read", path="test.txt")
        assert result.success
        assert result.output == "Hello World"


def test_file_tool_edit():
    """Test file edit operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        # Write initial content
        tool.execute_sync(operation="write", path="test.txt", content="Hello World")
        
        # Edit the file
        result = tool.execute_sync(operation="edit", path="test.txt", old_string="World", new_string="Python")
        assert result.success
        
        # Verify
        result = tool.execute_sync(operation="read", path="test.txt")
        assert result.output == "Hello Python"


def test_file_tool_list():
    """Test file list operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        # Create some files
        Path(tmpdir, "file1.txt").write_text("content1")
        Path(tmpdir, "file2.txt").write_text("content2")
        Path(tmpdir, "subdir").mkdir()
        Path(tmpdir, "subdir", "file3.txt").write_text("content3")
        
        # List directory
        result = tool.execute_sync(operation="list", path=".")
        assert result.success
        assert len(result.output) >= 3
        
        names = [item["name"] for item in result.output]
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "subdir" in names


def test_file_tool_search():
    """Test file search operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        # Create files with content
        Path(tmpdir, "file1.txt").write_text("Hello World\nThis is a test")
        Path(tmpdir, "file2.txt").write_text("Another file\nNo match here")
        Path(tmpdir, "subdir").mkdir()
        Path(tmpdir, "subdir", "file3.txt").write_text("World again")
        
        # Search
        result = tool.execute_sync(operation="search", path=".", pattern="World", recursive=True)
        assert result.success
        assert len(result.output) == 2  # Two matches


def test_bash_tool_basic():
    """Test basic bash command execution."""
    tool = BashTool(working_dir=".", allowed_dirs=["."])
    
    # Test simple command
    result = tool.execute_sync(command="echo hello")
    assert result.success
    assert "hello" in result.output


def test_bash_tool_working_dir():
    """Test bash with working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        # Create a file
        Path(tmpdir, "test.txt").write_text("content")
        
        # Run command in that directory
        result = tool.execute_sync(command="cat test.txt", working_dir=tmpdir)
        assert result.success
        assert "content" in result.output


def test_bash_tool_trusted_commands():
    """Test trusted command detection."""
    tool = BashTool()
    
    # These should be trusted
    assert not tool._requires_approval("ls")
    assert not tool._requires_approval("cat file.txt")
    assert not tool._requires_approval("grep pattern file.txt")
    assert not tool._requires_approval("git status")
    
    # These should require approval
    assert tool._requires_approval("rm file.txt")
    assert tool._requires_approval("mkdir newdir")


def test_bash_tool_blocked_commands():
    """Test blocked command detection."""
    tool = BashTool()
    
    assert tool._is_blocked("rm -rf /")
    assert tool._is_blocked("dd if=/dev/zero of=/dev/sda")
    assert not tool._is_blocked("ls -la")


def test_git_tool_status():
    """Test git status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        os.system(f"cd {tmpdir} && git init -q && git config user.email 'test@test.com' && git config user.name 'Test'")
        
        tool = GitTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        # Create a file
        Path(tmpdir, "test.txt").write_text("content")
        
        # Check status
        result = tool.execute_sync(operation="status", path=tmpdir)
        assert result.success
        assert len(result.output) == 1
        assert result.output[0]["path"] == "test.txt"


def test_git_tool_log():
    """Test git log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.system(f"cd {tmpdir} && git init -q && git config user.email 'test@test.com' && git config user.name 'Test'")
        
        Path(tmpdir, "file1.txt").write_text("content1")
        os.system(f"cd {tmpdir} && git add . && git commit -m 'First commit' -q")
        
        Path(tmpdir, "file2.txt").write_text("content2")
        os.system(f"cd {tmpdir} && git add . && git commit -m 'Second commit' -q")
        
        tool = GitTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        result = tool.execute_sync(operation="log", path=tmpdir, limit=5)
        assert result.success
        assert len(result.output) == 2
        assert result.output[0]["message"] == "Second commit"
        assert result.output[1]["message"] == "First commit"


def test_tool_schema():
    """Test tool schema generation."""
    file_tool = FileTool()
    schema = file_tool.get_schema()
    
    assert schema["name"] == "file"
    assert "parameters" in schema
    assert "operation" in schema["parameters"]["properties"]
    assert "path" in schema["parameters"]["properties"]
    
    bash_tool = BashTool()
    schema = bash_tool.get_schema()
    assert schema["name"] == "bash"
    
    git_tool = GitTool()
    schema = git_tool.get_schema()
    assert schema["name"] == "git"


# Add sync execute method for testing
def execute_sync(self, **kwargs):
    """Synchronous wrapper for testing."""
    import asyncio
    return asyncio.run(self.execute(**kwargs))

FileTool.execute_sync = execute_sync
BashTool.execute_sync = execute_sync
GitTool.execute_sync = execute_sync


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
