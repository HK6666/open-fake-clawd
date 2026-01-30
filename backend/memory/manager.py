"""Memory management system using markdown files (inspired by clawdbot)."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiofiles

from backend.config import settings


class MemoryManager:
    """
    Manages AI agent memory using markdown files.

    File structure:
    - SOUL.md: AI personality, tone, and boundaries
    - USER.md: User preferences and information
    - AGENTS.md: Available agent configurations
    - TOOLS.md: Available tools documentation
    - memory/*.md: Long-term memory fragments
    - sessions/*.md: Session conversation records
    """

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace = workspace_path or settings.workspace_path
        self.memory_path = self.workspace / "memory"
        self.sessions_path = self.workspace / "sessions"

    async def initialize(self):
        """Initialize workspace with default files."""
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.sessions_path.mkdir(parents=True, exist_ok=True)

        # Create default files if they don't exist
        defaults = {
            "SOUL.md": self._default_soul(),
            "USER.md": self._default_user(),
            "AGENTS.md": self._default_agents(),
            "TOOLS.md": self._default_tools(),
        }

        for filename, content in defaults.items():
            filepath = self.workspace / filename
            if not filepath.exists():
                async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                    await f.write(content)

    def _default_soul(self) -> str:
        """Default SOUL.md content."""
        return """# Soul

This file defines the AI assistant's personality, communication style, and behavioral boundaries.

## Personality

- Helpful and professional
- Concise but thorough
- Patient when explaining complex topics
- Proactive in suggesting improvements

## Communication Style

- Use clear, direct language
- Provide code examples when helpful
- Explain reasoning behind suggestions
- Ask clarifying questions when needed

## Boundaries

- Stay focused on the task at hand
- Don't make assumptions without verification
- Always confirm before destructive operations
- Respect user's coding style and preferences

## Working Principles

1. **Safety First**: Always verify before destructive operations
2. **Understand First**: Read and understand code before modifying
3. **Minimal Changes**: Make only necessary changes
4. **Test Impact**: Consider the impact of changes
"""

    def _default_user(self) -> str:
        """Default USER.md content."""
        return """# User Profile

This file stores information about the user that helps personalize interactions.

## Preferences

- Preferred language: [To be learned]
- Coding style: [To be learned]
- Common projects: [To be learned]

## Project Directories

- Default: [Not set]

## Notes

*This file will be updated automatically as we interact.*
"""

    def _default_agents(self) -> str:
        """Default AGENTS.md content."""
        return """# Available Agents

This file defines specialized agents and their capabilities.

## Default Agent

The default agent handles general coding tasks including:
- Code review and suggestions
- Bug fixing
- Feature implementation
- Documentation

## Code Review Agent

Specialized in reviewing code for:
- Best practices
- Security issues
- Performance optimizations
- Code style

## Debug Agent

Specialized in:
- Analyzing error messages
- Tracing issues
- Suggesting fixes
- Writing tests
"""

    def _default_tools(self) -> str:
        """Default TOOLS.md content."""
        return """# Available Tools

This file documents the tools available to the AI assistant.

## File Operations

- **Read**: Read file contents
- **Write**: Create or overwrite files
- **Edit**: Make precise edits to files
- **Glob**: Find files by pattern

## Search

- **Grep**: Search file contents
- **WebSearch**: Search the web

## Execution

- **Bash**: Execute shell commands
- **Task**: Launch specialized agents

## Notes

These tools are provided by Claude Code. Use them responsibly and always verify before destructive operations.
"""

    async def read_file(self, filename: str) -> Optional[str]:
        """Read a workspace file."""
        filepath = self.workspace / filename
        if filepath.exists():
            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                return await f.read()
        return None

    async def write_file(self, filename: str, content: str):
        """Write to a workspace file."""
        filepath = self.workspace / filename
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(content)

    async def append_to_file(self, filename: str, content: str):
        """Append content to a workspace file."""
        filepath = self.workspace / filename
        async with aiofiles.open(filepath, "a", encoding="utf-8") as f:
            await f.write(content)

    async def get_soul(self) -> str:
        """Get the SOUL.md content."""
        return await self.read_file("SOUL.md") or ""

    async def get_user_profile(self) -> str:
        """Get the USER.md content."""
        return await self.read_file("USER.md") or ""

    async def update_user_profile(self, section: str, content: str):
        """Update a specific section in USER.md."""
        current = await self.read_file("USER.md") or ""

        # Find and update the section
        pattern = rf"(## {section}\n)(.*?)(\n## |\Z)"
        match = re.search(pattern, current, re.DOTALL)

        if match:
            # Update existing section
            new_content = re.sub(
                pattern,
                rf"\1{content}\n\3",
                current,
                flags=re.DOTALL
            )
        else:
            # Add new section
            new_content = current.rstrip() + f"\n\n## {section}\n\n{content}\n"

        await self.write_file("USER.md", new_content)

    async def get_context_for_session(self) -> str:
        """
        Get the combined context for starting a new session.

        Returns SOUL + USER content formatted for injection.
        """
        soul = await self.get_soul()
        user = await self.get_user_profile()

        return f"""# System Context

{soul}

---

# User Context

{user}
"""

    async def save_memory(self, topic: str, content: str):
        """
        Save a memory fragment to the memory directory.

        Args:
            topic: The topic/category for this memory
            content: The memory content
        """
        # Sanitize topic for filename
        safe_topic = re.sub(r'[^\w\-]', '_', topic.lower())
        filename = f"{safe_topic}.md"
        filepath = self.memory_path / filename

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        if filepath.exists():
            # Append to existing memory file
            async with aiofiles.open(filepath, "a", encoding="utf-8") as f:
                await f.write(f"\n\n---\n\n### {timestamp}\n\n{content}")
        else:
            # Create new memory file
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(f"# Memory: {topic}\n\n### {timestamp}\n\n{content}")

    async def get_memories(self, topic: Optional[str] = None) -> Dict[str, str]:
        """
        Get memory fragments.

        Args:
            topic: Optional specific topic to retrieve

        Returns:
            Dict mapping topic names to their content
        """
        memories = {}

        if topic:
            safe_topic = re.sub(r'[^\w\-]', '_', topic.lower())
            filepath = self.memory_path / f"{safe_topic}.md"
            if filepath.exists():
                async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                    memories[topic] = await f.read()
        else:
            # Get all memories
            for filepath in self.memory_path.glob("*.md"):
                async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                    topic_name = filepath.stem.replace("_", " ").title()
                    memories[topic_name] = await f.read()

        return memories

    async def search_memories(self, query: str) -> List[Dict[str, Any]]:
        """
        Search through memories for relevant content.

        Args:
            query: Search query

        Returns:
            List of matching memory fragments with metadata
        """
        results = []
        query_lower = query.lower()

        for filepath in self.memory_path.glob("*.md"):
            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                content = await f.read()

            if query_lower in content.lower():
                # Find relevant sections
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Get surrounding context
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = "\n".join(lines[start:end])

                        results.append({
                            "file": filepath.name,
                            "topic": filepath.stem.replace("_", " ").title(),
                            "context": context,
                            "line": i + 1
                        })

        return results

    async def save_session(self, session_id: str, content: str):
        """Save a session to the sessions directory."""
        filepath = self.sessions_path / f"{session_id}.md"
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(content)

    async def get_session_history(self, session_id: str) -> Optional[str]:
        """Get a session's history."""
        filepath = self.sessions_path / f"{session_id}.md"
        if filepath.exists():
            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                return await f.read()
        return None

    async def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent sessions."""
        sessions = []

        for filepath in sorted(
            self.sessions_path.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]:
            sessions.append({
                "id": filepath.stem,
                "modified": datetime.fromtimestamp(filepath.stat().st_mtime),
                "size": filepath.stat().st_size
            })

        return sessions


# Global memory manager
memory_manager = MemoryManager()
