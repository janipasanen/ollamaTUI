"""Tests for session management."""

import tempfile
from pathlib import Path

from ollamatui.sessions.manager import SessionManager


async def test_session_manager():
    """Test session manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "sessions.db"
        manager = SessionManager(str(db_path))
        
        # Create session
        session = await manager.create_session(
            name="Test Session",
            model="qwen2.5-coder:3b",
            provider="local",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert session.id
        assert session.name == "Test Session"
        print("  Create: OK")
        
        # Get session
        retrieved = await manager.get_session(session.id)
        assert retrieved is not None
        assert retrieved.name == "Test Session"
        print("  Get: OK")
        
        # List sessions
        sessions = await manager.list_sessions()
        assert len(sessions) == 1
        print("  List: OK")
        
        # Update session
        session.messages.append({"role": "assistant", "content": "Hi!"})
        await manager.update_session(session)
        
        retrieved = await manager.get_session(session.id)
        assert len(retrieved.messages) == 2
        print("  Update: OK")
        
        # Archive
        await manager.archive_session(session.id)
        sessions = await manager.list_sessions(include_archived=False)
        assert len(sessions) == 0
        print("  Archive: OK")
        
        # Unarchive
        await manager.unarchive_session(session.id)
        sessions = await manager.list_sessions()
        assert len(sessions) == 1
        print("  Unarchive: OK")
        
        # Fork
        forked = await manager.fork_session(session.id, "Forked Session")
        assert forked is not None
        assert forked.name == "Forked Session"
        assert len(forked.messages) == 2
        print("  Fork: OK")
        
        # Search
        results = await manager.search_sessions("Test")
        assert len(results) >= 1
        print("  Search: OK")
        
        # Export/Import
        exported = await manager.export_session(session.id)
        assert exported is not None
        
        imported = await manager.import_session(exported)
        assert imported.id != session.id
        assert imported.name == session.name
        print("  Export/Import: OK")
        
        # Count
        count = await manager.get_session_count()
        assert count >= 2
        print("  Count: OK")
    
    print("All session tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_session_manager())
