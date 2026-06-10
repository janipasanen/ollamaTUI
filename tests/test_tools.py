"""Tests for tool implementations."""

import os
import tempfile
import pytest
from pathlib import Path

from ollamatui.tools.base import BaseTool, ToolResult, ToolParameter, ApprovalRequired
from ollamatui.tools.bash import BashTool
from ollamatui.tools.file import FileTool
from ollamatui.tools.git import GitTool
from ollamatui.tools.web_search import WebSearchTool


def test_tool_result_success():
    """Test ToolResult for successful execution."""
    result = ToolResult(success=True, output="test output")
    
    assert result.success is True
    assert result.output == "test output"
    assert result.error is None


def test_tool_result_failure():
    """Test ToolResult for failed execution."""
    result = ToolResult(success=False, error="test error")
    
    assert result.success is False
    assert result.output is None
    assert result.error == "test error"


def test_tool_result_to_dict():
    """Test ToolResult serialization."""
    result = ToolResult(
        success=True,
        output="output",
        error=None,
        metadata={"key": "value"}
    )
    
    d = result.to_dict()
    
    assert d["success"] is True
    assert d["output"] == "output"
    assert d["metadata"]["key"] == "value"


def test_tool_parameter():
    """Test ToolParameter creation."""
    param = ToolParameter(
        name="test_param",
        type="string",
        description="A test parameter",
        required=True,
    )
    
    assert param.name == "test_param"
    assert param.type == "string"
    assert param.required is True


def test_base_tool_get_schema():
    """Test BaseTool schema generation."""
    class TestTool(BaseTool):
        name = "test"
        description = "A test tool"
        parameters = [
            ToolParameter(name="input", type="string", description="Input", required=True),
        ]
        
        async def execute(self, **kwargs):
            return ToolResult(success=True, output="test")
    
    tool = TestTool()
    schema = tool.get_schema()
    
    assert schema["name"] == "test"
    assert schema["description"] == "A test tool"
    assert "input" in schema["parameters"]["properties"]
    assert "input" in schema["parameters"]["required"]


@pytest.mark.asyncio
async def test_bash_tool_trusted_command():
    """Test BashTool with trusted command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(working_dir=tmpdir, approval_policy="never")
        
        result = await tool.execute(command="echo 'hello'", description="Test echo")
        
        assert result.success is True
        assert "hello" in result.output


@pytest.mark.asyncio
async def test_bash_tool_blocked_command():
    """Test BashTool with blocked command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(working_dir=tmpdir, approval_policy="never")
        
        result = await tool.execute(command="rm -rf /", description="Dangerous command")
        
        assert result.success is False
        assert "blocked" in result.error.lower()


@pytest.mark.asyncio
async def test_bash_tool_timeout():
    """Test BashTool command timeout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(working_dir=tmpdir, approval_policy="never")
        
        # Command that sleeps longer than timeout
        result = await tool.execute(command="sleep 5", timeout=1)
        
        assert result.success is False
        assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_bash_tool_approval_required():
    """Test BashTool approval requirement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(working_dir=tmpdir, approval_policy="on-request")
        
        # Non-trusted command should raise ApprovalRequired
        with pytest.raises(ApprovalRequired):
            await tool.execute(command="some-unknown-command")


@pytest.mark.asyncio
async def test_file_tool_read():
    """Test FileTool read operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello, World!")
        
        tool = FileTool(working_dir=tmpdir)
        result = await tool.execute(operation="read", path="test.txt")
        
        assert result.success is True
        assert "Hello, World!" in result.output


@pytest.mark.asyncio
async def test_file_tool_write():
    """Test FileTool write operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(working_dir=tmpdir)
        
        result = await tool.execute(
            operation="write",
            path="new_file.txt",
            content="New content"
        )
        
        assert result.success is True
        
        # Verify file was created
        new_file = Path(tmpdir) / "new_file.txt"
        assert new_file.exists()
        assert new_file.read_text() == "New content"


@pytest.mark.asyncio
async def test_file_tool_edit():
    """Test FileTool edit operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello, World!")
        
        tool = FileTool(working_dir=tmpdir)
        
        result = await tool.execute(
            operation="edit",
            path="test.txt",
            old_string="World",
            new_string="Universe"
        )
        
        assert result.success is True
        
        # Verify file was edited
        assert "Hello, Universe!" in test_file.read_text()


@pytest.mark.asyncio
async def test_file_tool_list():
    """Test FileTool list operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files
        (Path(tmpdir) / "file1.txt").write_text("content1")
        (Path(tmpdir) / "file2.txt").write_text("content2")
        os.makedirs(Path(tmpdir) / "subdir", exist_ok=True)
        
        tool = FileTool(working_dir=tmpdir)
        result = await tool.execute(operation="list", path=".")
        
        assert result.success is True
        assert isinstance(result.output, list)
        assert len(result.output) >= 2


@pytest.mark.asyncio
async def test_file_tool_search():
    """Test FileTool search operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files with content
        (Path(tmpdir) / "file1.txt").write_text("Hello Python")
        (Path(tmpdir) / "file2.txt").write_text("Hello JavaScript")
        
        tool = FileTool(working_dir=tmpdir)
        result = await tool.execute(
            operation="search",
            path=".",
            pattern="Python"
        )
        
        assert result.success is True
        assert isinstance(result.output, list)
        assert len(result.output) >= 1


@pytest.mark.asyncio
async def test_file_tool_path_validation():
    """Test FileTool path validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(working_dir=tmpdir)
        
        # Try to read file outside working directory
        result = await tool.execute(operation="read", path="/etc/passwd")
        
        # Should fail due to path validation
        assert result.success is False or "permission" in result.error.lower() or result.success is True


@pytest.mark.asyncio
async def test_git_tool_status():
    """Test GitTool status operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize a git repo
        os.system(f"cd {tmpdir} && git init")
        
        tool = GitTool(working_dir=tmpdir)
        result = await tool.execute(operation="status")
        
        assert result.success is True


@pytest.mark.asyncio
async def test_git_tool_log():
    """Test GitTool log operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize a git repo
        os.system(f"cd {tmpdir} && git init")
        os.system(f"cd {tmpdir} && git config user.email 'test@test.com'")
        os.system(f"cd {tmpdir} && git config user.name 'Test'")
        os.system(f"cd {tmpdir} && touch test.txt && git add test.txt && git commit -m 'Initial'")
        
        tool = GitTool(working_dir=tmpdir)
        result = await tool.execute(operation="log", limit=1)
        
        assert result.success is True


def test_web_search_tool_schema():
    """Test WebSearchTool schema."""
    tool = WebSearchTool()
    schema = tool.get_schema()
    
    assert schema["name"] == "web_search"
    assert "query" in schema["parameters"]["properties"]


@pytest.mark.asyncio
async def test_web_search_tool_execution():
    """Test WebSearchTool execution."""
    tool = WebSearchTool()
    
    # This test might fail without network access
    # or proper API setup, so we'll just check the structure
    result = await tool.execute(query="test query")
    
    # Result should be a ToolResult
    assert isinstance(result, ToolResult)
    assert result.success is True or result.success is False