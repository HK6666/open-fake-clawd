"""REST API routes for the web dashboard."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import settings
from backend.claude.session import session_manager, SessionState
from backend.claude.runner import runner_manager
from backend.memory.manager import memory_manager


router = APIRouter(prefix="/api", tags=["api"])


# ============ Pydantic Models ============

class SessionInfo(BaseModel):
    """Session information response."""
    session_id: str
    user_id: int
    working_directory: str
    state: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_cost: float
    title: Optional[str] = None


class MessageInfo(BaseModel):
    """Message information."""
    role: str
    content: str
    timestamp: datetime


class SessionDetail(SessionInfo):
    """Session with messages."""
    messages: List[MessageInfo]


class MemoryFile(BaseModel):
    """Memory file information."""
    filename: str
    content: str
    modified: Optional[datetime] = None


class MemoryUpdateRequest(BaseModel):
    """Request to update a memory file."""
    content: str


class RunnerStatus(BaseModel):
    """Runner status information."""
    user_id: int
    state: str
    working_directory: str
    session_id: Optional[str] = None


# ============ Session Endpoints ============

@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(user_id: Optional[int] = None):
    """List all sessions, optionally filtered by user."""
    all_sessions = []

    if user_id:
        sessions = session_manager.get_user_sessions(user_id)
    else:
        # Get all sessions (admin view)
        sessions = []
        for uid in session_manager._user_sessions.keys():
            sessions.extend(session_manager.get_user_sessions(uid))

    for s in sessions:
        all_sessions.append(SessionInfo(
            session_id=s.session_id,
            user_id=s.user_id,
            working_directory=str(s.working_directory),
            state=s.state.value,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=len(s.messages),
            total_cost=s.total_cost,
            title=s.title
        ))

    return sorted(all_sessions, key=lambda x: x.updated_at, reverse=True)


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """Get session details with messages."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = [
        MessageInfo(
            role=m.role,
            content=m.content,
            timestamp=m.timestamp
        )
        for m in session.messages
    ]

    return SessionDetail(
        session_id=session.session_id,
        user_id=session.user_id,
        working_directory=str(session.working_directory),
        state=session.state.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        total_cost=session.total_cost,
        title=session.title,
        messages=messages
    )


@router.get("/sessions/{session_id}/export")
async def export_session(session_id: str):
    """Export session as markdown file."""
    markdown = session_manager.export_session(session_id)
    if not markdown:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save to file
    await session_manager.save_session_to_file(session_id)

    filepath = settings.sessions_path / f"{session_id}.md"
    return FileResponse(
        filepath,
        media_type="text/markdown",
        filename=f"session_{session_id}.md"
    )


# ============ Memory Endpoints ============

@router.get("/memory/files")
async def list_memory_files():
    """List all memory workspace files."""
    files = []

    # Core files
    for filename in ["SOUL.md", "USER.md", "AGENTS.md", "TOOLS.md"]:
        filepath = settings.workspace_path / filename
        if filepath.exists():
            files.append({
                "filename": filename,
                "path": str(filepath),
                "type": "core",
                "modified": datetime.fromtimestamp(filepath.stat().st_mtime)
            })

    # Memory fragments
    for filepath in settings.workspace_path.joinpath("memory").glob("*.md"):
        files.append({
            "filename": filepath.name,
            "path": str(filepath),
            "type": "memory",
            "modified": datetime.fromtimestamp(filepath.stat().st_mtime)
        })

    return files


@router.get("/memory/{filename}", response_model=MemoryFile)
async def get_memory_file(filename: str):
    """Get content of a memory file."""
    # Security: only allow .md files in workspace
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files allowed")

    # Check in workspace root first
    filepath = settings.workspace_path / filename
    if not filepath.exists():
        # Check in memory subdirectory
        filepath = settings.workspace_path / "memory" / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    content = filepath.read_text(encoding="utf-8")
    modified = datetime.fromtimestamp(filepath.stat().st_mtime)

    return MemoryFile(
        filename=filename,
        content=content,
        modified=modified
    )


@router.put("/memory/{filename}")
async def update_memory_file(filename: str, request: MemoryUpdateRequest):
    """Update a memory file."""
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files allowed")

    # Determine file path
    if filename in ["SOUL.md", "USER.md", "AGENTS.md", "TOOLS.md"]:
        filepath = settings.workspace_path / filename
    else:
        filepath = settings.workspace_path / "memory" / filename

    # Ensure directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    filepath.write_text(request.content, encoding="utf-8")

    return {"status": "ok", "filename": filename}


# ============ Runner Endpoints ============

@router.get("/runners", response_model=List[RunnerStatus])
async def list_runners():
    """List all active runners."""
    runners = []
    for user_id, runner in runner_manager._runners.items():
        runners.append(RunnerStatus(
            user_id=user_id,
            state=runner.state.value,
            working_directory=str(runner.working_directory),
            session_id=runner.session_id
        ))
    return runners


@router.post("/runners/{user_id}/stop")
async def stop_runner(user_id: int):
    """Stop a specific user's runner."""
    await runner_manager.stop_runner(user_id)
    return {"status": "ok", "user_id": user_id}


# ============ Config Endpoints ============

@router.get("/config")
async def get_config():
    """Get current configuration (safe subset)."""
    return {
        "approved_directory": str(settings.approved_directory),
        "workspace_path": str(settings.workspace_path),
        "claude_timeout": settings.claude_timeout,
        "claude_max_turns": settings.claude_max_turns,
        "rate_limit_requests": settings.rate_limit_requests,
        "rate_limit_window": settings.rate_limit_window,
        "allowed_users_count": len(settings.allowed_users)
    }


# ============ WebSocket for Real-time Logs ============

class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time logs."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


async def broadcast_log(log_type: str, message: str, **extra):
    """Broadcast a log message to all WebSocket clients."""
    await ws_manager.broadcast({
        "type": log_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        **extra
    })


# ============ Health Check ============

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }
