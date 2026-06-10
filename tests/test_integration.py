"""Integration tests for OllamaTUI."""

import asyncio
import tempfile
from pathlib import Path

from ollamatui.config import Config, load_config, ProviderType, SandboxMode, ApprovalPolicy
from ollamatui.providers.factory import create_provider
from ollamatui.providers.base import ChatMessage
from ollamatui.tools.file import FileTool
from ollamatui.tools.bash import BashTool
from ollamatui.tools.git import GitTool
from ollamatui.tools.web_search import WebSearchTool
from ollamatui.sessions.manager import SessionManager


async def test_config_integration():
    """Test config with providers."""
    print("Testing config integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test local provider config
        config = Config(
            provider=ProviderType.LOCAL,
            local_host="http://localhost:11434",
            model="qwen2.5-coder:3b",
        )
        
        provider = create_provider(config)
        assert provider.provider_name == "local"
        
        # Test connection
        connected = await provider.check_connection()
        print(f"  Local provider connection: {connected}")
        
        await provider.close()
    
    print("  Config integration: OK")


async def test_tools_integration():
    """Test tools working together."""
    print("Testing tools integration...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        import os
        os.system(f"cd {tmpdir} && git init -q && git config user.email 'test@test.com' && git config user.name 'Test'")
        
        # Create tools
        file_tool = FileTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        bash_tool = BashTool(working_dir=tmpdir, allowed_dirs=[tmpdir], approval_policy="never")
        git_tool = GitTool(working_dir=tmpdir, allowed_dirs=[tmpdir])
        
        # Create a file using file tool
        result = await file_tool.execute(operation="write", path="hello.py", content='print("Hello World")')
        assert result.success
        print("  File write: OK")
        
        # Run it with bash tool
        result = await bash_tool.execute(command="python3 hello.py", working_dir=tmpdir)
        assert result.success
        assert "Hello World" in result.output
        print("  Bash execute: OK")
        
        # Check git status
        result = await git_tool.execute(operation="status", path=tmpdir)
        assert result.success
        assert len(result.output) == 1
        print("  Git status: OK")
        
        # Add and commit
        result = await git_tool.execute(operation="add", path=tmpdir, files=["."])
        assert result.success
        print("  Git add: OK")
        
        result = await git_tool.execute(operation="commit", path=tmpdir, message="Add hello.py")
        assert result.success
        print("  Git commit: OK")
        
        # Search web
        web_search = WebSearchTool()
        result = await web_search.execute(query="Python asyncio", max_results=2)
        assert result.success
        print(f"  Web search: OK ({len(result.output)} results)")
        await web_search.close()
    
    print("  Tools integration: OK")


async def test_session_with_tools():
    """Test sessions with tools."""
    print("Testing session with tools...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "sessions.db"
        manager = SessionManager(str(db_path))
        
        # Create session
        session = await manager.create_session(
            name="Test with Tools",
            model="qwen2.5-coder:3b",
            provider="local",
            messages=[
                {"role": "user", "content": "Create a hello world file"},
                {"role": "assistant", "content": "I'll create a hello world file for you."},
            ],
        )
        
        # Simulate tool use in session
        session.messages.append({
            "role": "tool",
            "content": "Created hello.py",
            "tool": "file",
            "operation": "write",
        })
        
        await manager.update_session(session)
        
        # Retrieve and verify
        retrieved = await manager.get_session(session.id)
        assert len(retrieved.messages) == 3
        assert retrieved.messages[2]["tool"] == "file"
        print("  Session with tool use: OK")
    
    print("  Session with tools: OK")


async def test_provider_streaming():
    """Test provider streaming chat."""
    print("Testing provider streaming...")
    
    config = Config(
        provider=ProviderType.LOCAL,
        local_host="http://localhost:11434",
        model="qwen2.5-coder:3b",
    )
    
    provider = create_provider(config)
    
    messages = [ChatMessage(role="user", content="Say hello in one word")]
    
    full_response = ""
    async for chunk in provider.chat(config.model, messages, stream=True):
        if chunk.message.content:
            full_response += chunk.message.content
        if chunk.done:
            break
    
    assert len(full_response) > 0
    print(f"  Streaming response: '{full_response[:50]}...'")
    
    await provider.close()
    print("  Provider streaming: OK")


async def main():
    """Run all integration tests."""
    await test_config_integration()
    await test_tools_integration()
    await test_session_with_tools()
    await test_provider_streaming()
    print("\nAll integration tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
