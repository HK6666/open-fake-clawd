"""Database models using aiosqlite."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from backend.config import settings


@dataclass
class Session:
    """Represents a Claude Code session."""

    id: str
    user_id: int
    title: Optional[str]
    working_directory: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_active: bool


@dataclass
class Message:
    """Represents a message in a session."""

    id: int
    session_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime


@dataclass
class DailyRequestCount:
    """Represents daily request count statistics."""

    id: int
    date: str  # YYYY-MM-DD format
    user_id: int
    request_count: int
    created_at: datetime
    updated_at: datetime


class Database:
    """Database manager for session persistence."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to the database and create tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT,
                working_directory TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS daily_request_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                request_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_daily_counts_date ON daily_request_counts(date);
            CREATE INDEX IF NOT EXISTS idx_daily_counts_user_id ON daily_request_counts(user_id);
        """)
        await self._conn.commit()

    async def create_session(self, session_id: str, user_id: int, working_directory: str, title: Optional[str] = None) -> Session:
        """Create a new session."""
        now = datetime.now()
        await self._conn.execute(
            """
            INSERT INTO sessions (id, user_id, title, working_directory, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, title, working_directory, now, now)
        )
        await self._conn.commit()
        return Session(
            id=session_id,
            user_id=user_id,
            title=title,
            working_directory=working_directory,
            created_at=now,
            updated_at=now,
            message_count=0,
            is_active=True
        )

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Session(**dict(row))
        return None

    async def get_user_sessions(self, user_id: int, limit: int = 20) -> List[Session]:
        """Get sessions for a user, ordered by most recent."""
        cursor = await self._conn.execute(
            """
            SELECT * FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [Session(**dict(row)) for row in rows]

    async def get_active_session(self, user_id: int) -> Optional[Session]:
        """Get the most recent active session for a user."""
        cursor = await self._conn.execute(
            """
            SELECT * FROM sessions
            WHERE user_id = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Session(**dict(row))
        return None

    async def update_session(self, session_id: str, **kwargs):
        """Update session fields."""
        if not kwargs:
            return

        kwargs["updated_at"] = datetime.now()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [session_id]

        await self._conn.execute(
            f"UPDATE sessions SET {set_clause} WHERE id = ?",
            values
        )
        await self._conn.commit()

    async def add_message(self, session_id: str, role: str, content: str) -> Message:
        """Add a message to a session."""
        now = datetime.now()
        cursor = await self._conn.execute(
            """
            INSERT INTO messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, now)
        )
        await self._conn.execute(
            """
            UPDATE sessions
            SET message_count = message_count + 1, updated_at = ?
            WHERE id = ?
            """,
            (now, session_id)
        )
        await self._conn.commit()

        return Message(
            id=cursor.lastrowid,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=now
        )

    async def get_session_messages(self, session_id: str, limit: int = 100) -> List[Message]:
        """Get messages for a session."""
        cursor = await self._conn.execute(
            """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (session_id, limit)
        )
        rows = await cursor.fetchall()
        return [Message(**dict(row)) for row in rows]

    async def increment_daily_request_count(self, user_id: int) -> DailyRequestCount:
        """Increment daily request count for a user."""
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now()
        
        # Try to update existing record
        cursor = await self._conn.execute(
            """
            UPDATE daily_request_counts 
            SET request_count = request_count + 1, updated_at = ?
            WHERE date = ? AND user_id = ?
            """,
            (now, today, user_id)
        )
        await self._conn.commit()
        
        # If no rows updated, insert new record
        if cursor.rowcount == 0:
            await self._conn.execute(
                """
                INSERT INTO daily_request_counts (date, user_id, request_count, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?)
                """,
                (today, user_id, now, now)
            )
            await self._conn.commit()
        
        # Return the record
        cursor = await self._conn.execute(
            """
            SELECT * FROM daily_request_counts
            WHERE date = ? AND user_id = ?
            """,
            (today, user_id)
        )
        row = await cursor.fetchone()
        if row:
            return DailyRequestCount(**dict(row))
        return None

    async def get_daily_request_counts(self, start_date: str, end_date: str, user_id: int = None) -> List[DailyRequestCount]:
        """Get daily request counts for a date range."""
        if user_id:
            cursor = await self._conn.execute(
                """
                SELECT * FROM daily_request_counts
                WHERE date >= ? AND date <= ? AND user_id = ?
                ORDER BY date ASC
                """,
                (start_date, end_date, user_id)
            )
        else:
            cursor = await self._conn.execute(
                """
                SELECT date, SUM(request_count) as request_count
                FROM daily_request_counts
                WHERE date >= ? AND date <= ?
                GROUP BY date
                ORDER BY date ASC
                """,
                (start_date, end_date)
            )
        rows = await cursor.fetchall()
        return [DailyRequestCount(**dict(row)) for row in rows]


# Global database instance
db = Database()
