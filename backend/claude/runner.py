"""Claude Code CLI subprocess manager."""

import asyncio
import json
import os
import signal
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Callable, Optional, Dict, Any

from backend.config import settings


class RunnerState(Enum):
    """State of a Claude runner."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Represents a streaming event from Claude Code."""

    type: str  # 'text', 'tool_use', 'tool_result', 'error', 'done'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClaudeRunner:
    """Manages Claude Code CLI subprocess."""

    def __init__(
        self,
        working_directory: Optional[Path] = None,
        session_id: Optional[str] = None,
    ):
        self.working_directory = working_directory or settings.approved_directory
        self.session_id = session_id
        self.state = RunnerState.IDLE
        self._process: Optional[asyncio.subprocess.Process] = None
        self._output_buffer: list[str] = []
        self._error_buffer: list[str] = []

    @property
    def is_running(self) -> bool:
        """Check if the runner is currently processing."""
        return self.state == RunnerState.RUNNING

    def _build_command(self, prompt: str, continue_session: bool = False) -> list[str]:
        """Build the Claude CLI command."""
        cmd = [settings.claude_cli_path]

        # Add prompt
        cmd.extend(["--print", prompt])

        # Continue existing session
        if continue_session and self.session_id:
            cmd.extend(["--continue", self.session_id])

        # Output format
        cmd.extend(["--output-format", "stream-json"])

        # Max turns
        cmd.extend(["--max-turns", str(settings.claude_max_turns)])

        return cmd

    async def run(
        self,
        prompt: str,
        continue_session: bool = False,
        on_event: Optional[Callable[[StreamEvent], None]] = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Run Claude Code with the given prompt.

        Yields StreamEvent objects as they occur.
        """
        if self.is_running:
            raise RuntimeError("Runner is already processing a request")

        self.state = RunnerState.RUNNING
        self._output_buffer.clear()
        self._error_buffer.clear()

        cmd = self._build_command(prompt, continue_session)

        try:
            # Start subprocess
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_directory),
                env={**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
            )

            # Process stdout stream
            async for event in self._process_stream():
                if on_event:
                    on_event(event)
                yield event

            # Wait for process to complete
            await self._process.wait()

            # Check for errors
            if self._process.returncode != 0:
                stderr = await self._process.stderr.read()
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                error_event = StreamEvent(
                    type="error",
                    content=error_msg,
                    metadata={"returncode": self._process.returncode}
                )
                if on_event:
                    on_event(error_event)
                yield error_event
                self.state = RunnerState.ERROR
            else:
                self.state = RunnerState.IDLE

            # Final done event
            done_event = StreamEvent(type="done", content="")
            if on_event:
                on_event(done_event)
            yield done_event

        except asyncio.CancelledError:
            await self.stop()
            self.state = RunnerState.STOPPED
            raise
        except Exception as e:
            self.state = RunnerState.ERROR
            error_event = StreamEvent(type="error", content=str(e))
            if on_event:
                on_event(error_event)
            yield error_event

    async def _process_stream(self) -> AsyncIterator[StreamEvent]:
        """Process the stdout stream from Claude Code."""
        buffer = ""

        while True:
            chunk = await self._process.stdout.read(1024)
            if not chunk:
                break

            buffer += chunk.decode("utf-8", errors="replace")

            # Process complete JSON lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                event = self._parse_stream_line(line)
                if event:
                    self._output_buffer.append(line)
                    yield event

    def _parse_stream_line(self, line: str) -> Optional[StreamEvent]:
        """Parse a single line of stream output."""
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            # Not JSON, treat as plain text
            return StreamEvent(type="text", content=line)

        event_type = data.get("type", "unknown")

        # Handle different event types from Claude Code stream
        if event_type == "assistant":
            # Assistant message with content
            message = data.get("message", {})
            content_blocks = message.get("content", [])
            text_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
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
            if session_id:
                self.session_id = session_id
            return StreamEvent(
                type="result",
                content=result,
                metadata={"session_id": session_id, "cost": data.get("cost_usd")}
            )

        elif event_type == "error":
            return StreamEvent(
                type="error",
                content=data.get("error", {}).get("message", "Unknown error")
            )

        elif event_type == "system":
            # System message (tool output, etc.)
            return StreamEvent(
                type="system",
                content=data.get("message", ""),
                metadata=data
            )

        return None

    async def stop(self):
        """Stop the running process."""
        if self._process and self._process.returncode is None:
            try:
                # Try graceful termination first
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if doesn't respond
                    self._process.kill()
                    await self._process.wait()
            except ProcessLookupError:
                pass  # Process already exited

        self.state = RunnerState.STOPPED

    def get_output(self) -> str:
        """Get accumulated output."""
        return "\n".join(self._output_buffer)

    def change_directory(self, path: Path) -> bool:
        """
        Change working directory.

        Returns True if successful, False if path is not allowed.
        """
        # Resolve and validate path
        resolved = path.expanduser().resolve()

        # Check if path is within approved directory
        try:
            resolved.relative_to(settings.approved_directory)
        except ValueError:
            # Path is not within approved directory
            # Allow if it's the approved directory itself
            if resolved != settings.approved_directory:
                return False

        if not resolved.is_dir():
            return False

        self.working_directory = resolved
        return True


class RunnerManager:
    """Manages multiple Claude runners for different users/sessions."""

    def __init__(self):
        self._runners: Dict[int, ClaudeRunner] = {}  # user_id -> runner

    def get_runner(self, user_id: int) -> ClaudeRunner:
        """Get or create a runner for a user."""
        if user_id not in self._runners:
            self._runners[user_id] = ClaudeRunner()
        return self._runners[user_id]

    def get_active_runner(self, user_id: int) -> Optional[ClaudeRunner]:
        """Get runner only if it exists."""
        return self._runners.get(user_id)

    async def stop_runner(self, user_id: int):
        """Stop a user's runner."""
        runner = self._runners.get(user_id)
        if runner:
            await runner.stop()

    async def stop_all(self):
        """Stop all runners."""
        for runner in self._runners.values():
            await runner.stop()


# Global runner manager
runner_manager = RunnerManager()
