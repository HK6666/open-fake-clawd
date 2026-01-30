"""Session state management for Claude Code interactions."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.config import settings


class SessionState(Enum):
    """State of a chat session."""

    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_INPUT = "waiting_input"
    ERROR = "error"


@dataclass
class ChatMessage:
    """A single message in the chat history."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """Context for a Claude Code session."""

    session_id: str
    user_id: int
    working_directory: Path
    state: SessionState = SessionState.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[ChatMessage] = field(default_factory=list)
    claude_session_id: Optional[str] = None  # Claude Code's internal session ID
    title: Optional[str] = None
    total_cost: float = 0.0

    def add_message(self, role: str, content: str, **metadata) -> ChatMessage:
        """Add a message to the session."""
        msg = ChatMessage(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg

    def get_recent_messages(self, limit: int = 10) -> List[ChatMessage]:
        """Get the most recent messages."""
        return self.messages[-limit:]

    def to_markdown(self) -> str:
        """Export session to markdown format."""
        lines = [
            f"# Session: {self.title or self.session_id}",
            "",
            f"- **Session ID**: {self.session_id}",
            f"- **User ID**: {self.user_id}",
            f"- **Working Directory**: {self.working_directory}",
            f"- **Created**: {self.created_at.isoformat()}",
            f"- **Updated**: {self.updated_at.isoformat()}",
            f"- **Total Cost**: ${self.total_cost:.4f}",
            "",
            "---",
            "",
            "## Conversation",
            "",
        ]

        for msg in self.messages:
            role_label = "**User**" if msg.role == "user" else "**Assistant**"
            lines.append(f"### {role_label} ({msg.timestamp.strftime('%H:%M:%S')})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")

        return "\n".join(lines)


class SessionManager:
    """Manages active sessions for users."""

    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}  # session_id -> context
        self._user_sessions: Dict[int, List[str]] = {}  # user_id -> session_ids
        self._active_session: Dict[int, str] = {}  # user_id -> active session_id

    def create_session(
        self,
        user_id: int,
        working_directory: Optional[Path] = None,
        title: Optional[str] = None
    ) -> SessionContext:
        """Create a new session for a user."""
        session_id = str(uuid.uuid4())[:8]
        context = SessionContext(
            session_id=session_id,
            user_id=user_id,
            working_directory=working_directory or settings.approved_directory,
            title=title
        )

        self._sessions[session_id] = context

        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)

        # Set as active session
        self._active_session[user_id] = session_id

        return context

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_active_session(self, user_id: int) -> Optional[SessionContext]:
        """Get the active session for a user."""
        session_id = self._active_session.get(user_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def set_active_session(self, user_id: int, session_id: str) -> bool:
        """Set the active session for a user."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            if session.user_id == user_id:
                self._active_session[user_id] = session_id
                return True
        return False

    def get_user_sessions(self, user_id: int) -> List[SessionContext]:
        """Get all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def update_session_state(self, session_id: str, state: SessionState):
        """Update the state of a session."""
        session = self._sessions.get(session_id)
        if session:
            session.state = state
            session.updated_at = datetime.now()

    def add_cost(self, session_id: str, cost: float):
        """Add cost to a session."""
        session = self._sessions.get(session_id)
        if session:
            session.total_cost += cost

    def export_session(self, session_id: str) -> Optional[str]:
        """Export a session to markdown."""
        session = self._sessions.get(session_id)
        if session:
            return session.to_markdown()
        return None

    async def save_session_to_file(self, session_id: str):
        """Save a session to a markdown file."""
        session = self._sessions.get(session_id)
        if not session:
            return

        settings.ensure_directories()
        file_path = settings.sessions_path / f"{session_id}.md"

        markdown = session.to_markdown()
        file_path.write_text(markdown, encoding="utf-8")


# Global session manager
session_manager = SessionManager()
