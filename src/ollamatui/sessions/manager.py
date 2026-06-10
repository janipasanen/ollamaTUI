"""Session management with SQLite backend."""

import sqlite3
import json
import asyncio
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import uuid


@dataclass
class Session:
    """A chat session."""
    id: str
    name: str
    model: str
    provider: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    archived: bool = False
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class SessionManager:
    """Manages chat sessions with SQLite persistence."""
    
    def __init__(self, db_path: str = "~/.ollamatui/sessions.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the database."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]'
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated 
                ON sessions(updated_at DESC)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_archived 
                ON sessions(archived)
            """)
            
            await db.commit()
        
        self._initialized = True
    
    async def create_session(
        self,
        name: str,
        model: str,
        provider: str,
        messages: List[Dict[str, Any]] = None,
        tags: List[str] = None,
    ) -> Session:
        """Create a new session."""
        await self.initialize()
        
        session = Session(
            id=str(uuid.uuid4()),
            name=name,
            model=model,
            provider=provider,
            messages=messages or [],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tags=tags or [],
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO sessions (id, name, model, provider, messages, created_at, updated_at, archived, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.name,
                session.model,
                session.provider,
                json.dumps(session.messages),
                session.created_at,
                session.updated_at,
                0,
                json.dumps(session.tags),
            ))
            await db.commit()
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_session(row)
                return None
    
    async def list_sessions(
        self,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Session]:
        """List sessions."""
        await self.initialize()
        
        query = "SELECT * FROM sessions"
        params = []
        
        if not include_archived:
            query += " WHERE archived = 0"
        
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_session(row) for row in rows]
    
    async def update_session(self, session: Session) -> None:
        """Update a session."""
        await self.initialize()
        
        session.updated_at = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions
                SET name = ?, model = ?, provider = ?, messages = ?,
                    updated_at = ?, archived = ?, tags = ?
                WHERE id = ?
            """, (
                session.name,
                session.model,
                session.provider,
                json.dumps(session.messages),
                session.updated_at,
                1 if session.archived else 0,
                json.dumps(session.tags),
                session.id,
            ))
            await db.commit()
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM sessions WHERE id = ?",
                (session_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def archive_session(self, session_id: str) -> bool:
        """Archive a session."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session.archived = True
        await self.update_session(session)
        return True
    
    async def unarchive_session(self, session_id: str) -> bool:
        """Unarchive a session."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session.archived = False
        await self.update_session(session)
        return True
    
    async def fork_session(self, session_id: str, new_name: str = None) -> Optional[Session]:
        """Fork a session from a specific point."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        fork_name = new_name or f"{session.name} (fork)"
        return await self.create_session(
            name=fork_name,
            model=session.model,
            provider=session.provider,
            messages=session.messages.copy(),
            tags=session.tags + ["forked"],
        )
    
    async def search_sessions(self, query: str, limit: int = 20) -> List[Session]:
        """Search sessions by name or message content."""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM sessions
                WHERE (name LIKE ? OR messages LIKE ?) AND archived = 0
                ORDER BY updated_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_session(row) for row in rows]
    
    async def get_session_count(self, include_archived: bool = False) -> int:
        """Get total session count."""
        await self.initialize()
        
        query = "SELECT COUNT(*) FROM sessions"
        params = []
        
        if not include_archived:
            query += " WHERE archived = 0"
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    def _row_to_session(self, row) -> Session:
        """Convert database row to Session object."""
        return Session(
            id=row["id"],
            name=row["name"],
            model=row["model"],
            provider=row["provider"],
            messages=json.loads(row["messages"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            archived=bool(row["archived"]),
            tags=json.loads(row["tags"]),
        )
    
    async def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export a session as JSON."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        return asdict(session)
    
    async def import_session(self, data: Dict[str, Any]) -> Session:
        """Import a session from JSON."""
        session = Session(**data)
        session.id = str(uuid.uuid4())  # Generate new ID
        session.created_at = datetime.now().isoformat()
        session.updated_at = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO sessions (id, name, model, provider, messages, created_at, updated_at, archived, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.name,
                session.model,
                session.provider,
                json.dumps(session.messages),
                session.created_at,
                session.updated_at,
                0,
                json.dumps(session.tags),
            ))
            await db.commit()
        
        return session
