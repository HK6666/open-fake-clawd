"""Claude Code CLI subprocess manager with interactive mode support."""

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Callable, Optional, Dict, Any, List

from backend.config import settings

logger = logging.getLogger(__name__)


class RunnerState(Enum):
    """State of a Claude runner."""

    IDLE = "idle"
    RUNNING = "running"
    STARTING = "starting"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Represents a streaming event from Claude Code."""

    type: str  # 'text', 'tool_use', 'tool_result', 'error', 'done', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClaudeRunner:
    """
    Manages Claude Code CLI subprocess in interactive mode.

    The process stays alive and accepts multiple messages through stdin,
    allowing use of slash commands like /usage, /help, etc.
    """

    def __init__(
        self,
        working_directory: Optional[Path] = None,
        session_id: Optional[str] = None,
    ):
        self.working_directory = working_directory or settings.approved_directory_path
        self.session_id = session_id
        self.state = RunnerState.IDLE
        self._process: Optional[asyncio.subprocess.Process] = None
        self._output_buffer: list[str] = []
        self._error_buffer: list[str] = []
        self._read_task: Optional[asyncio.Task] = None
        self._response_queue: asyncio.Queue = asyncio.Queue()
        self._current_response: list[StreamEvent] = []
        self._lock = asyncio.Lock()
        self._last_activity_time: float = 0
        self._health_check_failures: int = 0

    @property
    def is_running(self) -> bool:
        """Check if the runner is currently processing a request."""
        return self.state == RunnerState.RUNNING

    @property
    def is_alive(self) -> bool:
        """Check if the process is alive and ready."""
        return (
            self._process is not None
            and self._process.returncode is None
            and self.state in (RunnerState.IDLE, RunnerState.RUNNING)
        )

    def _build_command(self) -> list[str]:
        """Build the Claude CLI command for interactive mode."""
        cmd = [settings.claude_cli_path]

        # Use stream-json for both input and output
        cmd.extend(["--input-format", "stream-json"])
        cmd.extend(["--output-format", "stream-json"])

        # Print mode is required for stream-json input
        cmd.extend(["-p", ""])

        # Verbose for more detailed output
        cmd.append("--verbose")

        # Max turns
        cmd.extend(["--max-turns", str(settings.claude_max_turns)])

        # Skip permission prompts for automated operation
        cmd.append("--dangerously-skip-permissions")

        # Continue session if we have one
        if self.session_id:
            cmd.extend(["--continue", self.session_id])

        return cmd

    async def start(self) -> bool:
        """
        Start the interactive Claude process.

        Returns True if started successfully, False otherwise.
        """
        if self.is_alive:
            logger.info("Process already running")
            return True

        self.state = RunnerState.STARTING
        cmd = self._build_command()
        logger.info(f"Starting Claude CLI: {' '.join(cmd)}")
        logger.info(f"Working directory: {self.working_directory}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_directory),
                env={**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
            )
            logger.info(f"Process started with PID: {self._process.pid}")

            # Start background reader task
            self._read_task = asyncio.create_task(self._background_reader())

            self.state = RunnerState.IDLE
            return True

        except Exception as e:
            logger.exception(f"Failed to start Claude process: {e}")
            self.state = RunnerState.ERROR
            return False

    async def _background_reader(self):
        """Background task to read stdout and populate response queue."""
        buffer = ""

        try:
            while self._process and self._process.returncode is None:
                try:
                    chunk = await asyncio.wait_for(
                        self._process.stdout.read(4096),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                if not chunk:
                    break

                decoded = chunk.decode("utf-8", errors="replace")
                buffer += decoded

                # Process complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    event = self._parse_stream_line(line)
                    if event:
                        await self._response_queue.put(event)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Background reader error: {e}")
            await self._response_queue.put(StreamEvent(
                type="error",
                content=f"Reader error: {str(e)}"
            ))

    async def send_message(
        self,
        message: str,
        on_event: Optional[Callable[[StreamEvent], None]] = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Send a message to the interactive Claude process.

        Yields StreamEvent objects as they arrive.
        """
        import time

        async with self._lock:
            # Health check before processing
            if not await self.ensure_healthy():
                yield StreamEvent(type="error", content="Runner health check failed, please try again")
                return

            # Ensure process is running
            if not self.is_alive:
                if not await self.start():
                    yield StreamEvent(type="error", content="Failed to start Claude process")
                    return

            if self.state == RunnerState.RUNNING:
                yield StreamEvent(type="error", content="Already processing a request")
                return

            self.state = RunnerState.RUNNING
            self._last_activity_time = time.time()

            try:
                # Clear any stale events from queue
                while not self._response_queue.empty():
                    try:
                        self._response_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                # Send message as JSON
                # Format for stream-json input: {"type":"user","message":{"role":"user","content":"..."}}
                input_msg = {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": message
                    }
                }

                json_line = json.dumps(input_msg) + "\n"
                logger.debug(f"Sending to stdin: {json_line.strip()}")

                self._process.stdin.write(json_line.encode())
                await self._process.stdin.drain()

                # Read responses until we get a result or timeout
                response_complete = False
                timeout_count = 0
                max_timeout_count = settings.claude_timeout // 1  # Use config timeout

                while not response_complete:
                    try:
                        event = await asyncio.wait_for(
                            self._response_queue.get(),
                            timeout=1.0
                        )
                        timeout_count = 0  # Reset on activity
                        self._last_activity_time = time.time()

                        if on_event:
                            on_event(event)
                        yield event

                        # Check for response completion
                        if event.type == "result":
                            if event.metadata.get("session_id"):
                                self.session_id = event.metadata["session_id"]
                            response_complete = True
                        elif event.type == "error":
                            response_complete = True

                    except asyncio.TimeoutError:
                        timeout_count += 1
                        if timeout_count >= max_timeout_count:
                            yield StreamEvent(
                                type="error",
                                content="Response timeout"
                            )
                            response_complete = True

                # Send done event
                done_event = StreamEvent(type="done", content="")
                if on_event:
                    on_event(done_event)
                yield done_event

            except Exception as e:
                logger.exception(f"Error sending message: {e}")
                yield StreamEvent(type="error", content=str(e))
                self.state = RunnerState.ERROR
            finally:
                if self.state == RunnerState.RUNNING:
                    self.state = RunnerState.IDLE

    async def run(
        self,
        prompt: str,
        continue_session: bool = False,
        on_event: Optional[Callable[[StreamEvent], None]] = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Run Claude Code with the given prompt (compatibility method).

        This method maintains backward compatibility with the old API
        while using the new interactive mode internally.
        """
        # Update session continuation setting
        if continue_session and not self.session_id:
            continue_session = False

        async for event in self.send_message(prompt, on_event):
            yield event

    def _parse_stream_line(self, line: str) -> Optional[StreamEvent]:
        """Parse a single line of stream output."""
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            # Not JSON, treat as plain text
            if line.strip():
                return StreamEvent(type="text", content=line)
            return None

        event_type = data.get("type", "unknown")

        # Handle different event types from Claude Code stream
        if event_type == "assistant":
            # Assistant message with content
            message = data.get("message", {})
            content_blocks = message.get("content", [])

            # Ensure content_blocks is a list
            if isinstance(content_blocks, str):
                content_blocks = [{"type": "text", "text": content_blocks}]
            elif not isinstance(content_blocks, list):
                content_blocks = []

            text_parts = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)

            if text_parts:
                return StreamEvent(
                    type="text",
                    content="".join(text_parts),
                    metadata={"message_id": message.get("id")}
                )

        elif event_type == "content_block_delta":
            # Streaming text delta
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                return StreamEvent(
                    type="text",
                    content=delta.get("text", "")
                )

        elif event_type == "content_block_start":
            # Start of a content block (tool use, etc.)
            content_block = data.get("content_block", {})
            if content_block.get("type") == "tool_use":
                return StreamEvent(
                    type="tool_use",
                    content=content_block.get("name", "unknown_tool"),
                    metadata={"tool_id": content_block.get("id")}
                )

        elif event_type == "result":
            # Final result
            result = data.get("result", "")
            session_id = data.get("session_id")
            subtype = data.get("subtype", "")

            return StreamEvent(
                type="result",
                content=result,
                metadata={
                    "session_id": session_id,
                    "cost": data.get("cost_usd"),
                    "subtype": subtype
                }
            )

        elif event_type == "error":
            return StreamEvent(
                type="error",
                content=data.get("error", {}).get("message", "Unknown error")
            )

        elif event_type == "system":
            # System message (tool output, etc.)
            message = data.get("message", "")
            if isinstance(message, dict):
                message = json.dumps(message)
            return StreamEvent(
                type="system",
                content=str(message),
                metadata=data
            )

        elif event_type == "user":
            # User message echoed back (includes slash command output)
            # Format: {"type":"user","message":{"role":"user","content":"<local-command-stdout>...</local-command-stdout>"}}
            message = data.get("message", {})
            content = message.get("content", "")

            # Handle content as list (content blocks) or string
            if isinstance(content, list):
                # Extract text from content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "".join(text_parts)
            elif not isinstance(content, str):
                content = str(content)

            if content:
                # Extract content from <local-command-stdout> tags if present
                match = re.search(r'<local-command-stdout>(.*?)</local-command-stdout>', content, re.DOTALL)
                if match:
                    return StreamEvent(
                        type="text",
                        content=match.group(1).strip(),
                        metadata={"source": "slash_command"}
                    )

        return None

    async def stop(self):
        """Stop the running process."""
        # Cancel reader task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        # Stop process
        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
            except ProcessLookupError:
                pass

        self._process = None
        self.state = RunnerState.STOPPED

    def get_output(self) -> str:
        """Get accumulated output."""
        return "\n".join(self._output_buffer)

    def change_directory(self, path: Path) -> bool:
        """
        Change working directory.

        Note: This will require restarting the process to take effect.
        Returns True if path is valid, False otherwise.
        """
        resolved = path.expanduser().resolve()

        # Check if path is within approved directory
        try:
            resolved.relative_to(settings.approved_directory_path)
        except ValueError:
            if resolved != settings.approved_directory_path:
                return False

        if not resolved.is_dir():
            return False

        self.working_directory = resolved
        return True

    async def restart(self):
        """Restart the process (e.g., after changing directory)."""
        await self.stop()
        self.state = RunnerState.IDLE
        self._health_check_failures = 0
        # Process will be started on next message

    async def health_check(self) -> bool:
        """
        Check if the runner is healthy.

        Returns:
            True if healthy, False if needs restart
        """
        import time

        # Check if process exists and is alive
        if self._process is None:
            return True  # Not started yet, that's ok

        if self._process.returncode is not None:
            logger.warning(f"Process has exited with code {self._process.returncode}")
            self._health_check_failures += 1
            return False

        # Check if stuck in RUNNING state for too long
        if self.state == RunnerState.RUNNING:
            idle_time = time.time() - self._last_activity_time
            if idle_time > settings.claude_timeout:
                logger.warning(f"Process appears stuck (idle for {idle_time:.0f}s)")
                self._health_check_failures += 1
                return False

        # Check queue health
        if self._response_queue.qsize() > 1000:
            logger.warning(f"Response queue is too large ({self._response_queue.qsize()})")
            self._health_check_failures += 1
            return False

        self._health_check_failures = 0
        return True

    async def ensure_healthy(self) -> bool:
        """
        Ensure the runner is healthy, restart if necessary.

        Returns:
            True if healthy or successfully restarted, False otherwise
        """
        if await self.health_check():
            return True

        logger.info(f"Health check failed {self._health_check_failures} times, attempting restart...")

        # Try to restart
        try:
            await self.restart()
            return True
        except Exception as e:
            logger.exception(f"Failed to restart runner: {e}")
            return False


class RunnerManager:
    """
    Manages multiple Claude runners - one per session for better isolation.

    Architecture:
    - Each session gets its own Claude CLI process
    - Prevents one stuck session from blocking others
    - Automatic cleanup of idle/dead processes
    - Per-user resource limits
    """

    def __init__(self, max_sessions_per_user: int = 5):
        self._runners: Dict[str, ClaudeRunner] = {}  # session_id -> runner
        self._user_sessions: Dict[int, List[str]] = {}  # user_id -> session_ids
        self._max_sessions_per_user = max_sessions_per_user
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # Cleanup every 5 minutes

    def get_runner(
        self,
        session_id: str,
        user_id: int,
        working_directory: Optional[Path] = None
    ) -> Optional[ClaudeRunner]:
        """
        Get or create a runner for a session.

        Returns None if user has exceeded max sessions limit.
        """
        # Check if runner already exists
        if session_id in self._runners:
            runner = self._runners[session_id]
            # Health check - restart if dead
            if not runner.is_alive and runner.state != RunnerState.IDLE:
                logger.warning(f"Runner for session {session_id} is dead, will restart on next use")
                runner.state = RunnerState.IDLE
            return runner

        # Check user session limit
        user_sessions = self._user_sessions.get(user_id, [])
        if len(user_sessions) >= self._max_sessions_per_user:
            logger.warning(f"User {user_id} has reached max sessions limit ({self._max_sessions_per_user})")
            return None

        # Create new runner
        runner = ClaudeRunner(
            working_directory=working_directory,
            session_id=session_id
        )
        self._runners[session_id] = runner

        # Track user sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)

        logger.info(f"Created new runner for session {session_id} (user {user_id})")
        return runner

    def get_active_runner(self, session_id: str) -> Optional[ClaudeRunner]:
        """Get runner only if it exists."""
        return self._runners.get(session_id)

    async def stop_runner(self, session_id: str, user_id: Optional[int] = None):
        """Stop a specific runner."""
        runner = self._runners.get(session_id)
        if runner:
            await runner.stop()
            del self._runners[session_id]

            # Remove from user sessions tracking
            if user_id and user_id in self._user_sessions:
                try:
                    self._user_sessions[user_id].remove(session_id)
                    if not self._user_sessions[user_id]:
                        del self._user_sessions[user_id]
                except ValueError:
                    pass

            logger.info(f"Stopped and removed runner for session {session_id}")

    async def stop_user_runners(self, user_id: int):
        """Stop all runners for a specific user."""
        session_ids = self._user_sessions.get(user_id, []).copy()
        for session_id in session_ids:
            await self.stop_runner(session_id, user_id)

    async def stop_all(self):
        """Stop all runners."""
        for runner in list(self._runners.values()):
            await runner.stop()
        self._runners.clear()
        self._user_sessions.clear()

    async def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started background cleanup task")

    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background cleanup task")

    async def _cleanup_loop(self):
        """Background loop for periodic cleanup."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_idle_runners()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in cleanup loop: {e}")

    async def cleanup_idle_runners(self, max_idle_seconds: int = 1800):
        """
        Clean up runners that have been idle for too long.

        Args:
            max_idle_seconds: Maximum idle time before cleanup (default 30 min)
        """
        import time
        current_time = time.time()
        to_remove = []

        for session_id, runner in self._runners.items():
            # Check if process is dead
            if runner._process and runner._process.returncode is not None:
                logger.info(f"Cleaning up dead runner for session {session_id}")
                to_remove.append(session_id)
                continue

            # Check idle time (if state is IDLE and no recent activity)
            if runner.state == RunnerState.IDLE:
                # We could add last_activity_time tracking if needed
                # For now, just check if process is stopped
                if not runner.is_alive:
                    to_remove.append(session_id)

        # Remove identified runners
        for session_id in to_remove:
            runner = self._runners.get(session_id)
            if runner:
                await runner.stop()
                del self._runners[session_id]

                # Remove from user tracking
                for user_id, sessions in list(self._user_sessions.items()):
                    if session_id in sessions:
                        sessions.remove(session_id)
                        if not sessions:
                            del self._user_sessions[user_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} idle/dead runners")

    def get_user_session_count(self, user_id: int) -> int:
        """Get number of active sessions for a user."""
        return len(self._user_sessions.get(user_id, []))

    def get_stats(self) -> Dict[str, Any]:
        """Get runner manager statistics."""
        total_runners = len(self._runners)
        alive_runners = sum(1 for r in self._runners.values() if r.is_alive)
        running_runners = sum(1 for r in self._runners.values() if r.is_running)

        return {
            "total_runners": total_runners,
            "alive_runners": alive_runners,
            "running_runners": running_runners,
            "total_users": len(self._user_sessions),
            "user_sessions": {uid: len(sids) for uid, sids in self._user_sessions.items()}
        }


# Global runner manager
runner_manager = RunnerManager(max_sessions_per_user=settings.max_concurrent_sessions)
