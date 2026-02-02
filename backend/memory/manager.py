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
        self.workspace = workspace_path or settings.workspace_path_resolved
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
It will be automatically updated as we work together.

## Preferences

- **Preferred Language**: Auto-detected from conversations
- **UI/Design Style**: To be learned from project work
- **Communication Style**: To be learned
- **Coding Approach**: To be learned

## Current Projects

*Project information will be recorded automatically*

## Tech Stack Experience

### Languages
*Detected from code interactions*

### Frameworks & Libraries
*Detected from project work*

### Tools & Platforms
*Detected from usage patterns*

## Working Habits

*Learning from interaction patterns*

## Notes

*Additional context and preferences*

---

*Last updated: Never*
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

    def _extract_project_info(self, working_directory: str) -> Dict[str, Any]:
        """Extract project name and path from working directory."""
        from pathlib import Path

        path = Path(working_directory)
        project_name = path.name

        # Try to find project root by looking for markers
        current = path
        for _ in range(5):  # Check up to 5 levels up
            if any((current / marker).exists() for marker in ['.git', 'package.json', 'pyproject.toml', 'Cargo.toml']):
                project_name = current.name
                path = current
                break
            if current.parent == current:
                break
            current = current.parent

        return {
            "name": project_name,
            "path": str(path),
            "short_path": str(path).replace(str(Path.home()), "~")
        }

    def _detect_language(self, messages: List[Dict[str, str]]) -> str:
        """Detect user's preferred language from messages."""
        user_messages = [m.get("content", "") for m in messages if m.get("role") == "user"]
        all_text = " ".join(user_messages)

        # Simple heuristic: check for Chinese characters
        chinese_chars = sum(1 for c in all_text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(all_text.replace(" ", ""))

        if total_chars > 0 and chinese_chars / total_chars > 0.1:
            return "Chinese (中文)"
        return "English"

    def _detect_tech_stack(self, all_text: str) -> Dict[str, List[str]]:
        """Detect detailed tech stack from conversation."""
        all_lower = all_text.lower()

        detected = {
            "languages": set(),
            "frameworks": set(),
            "tools": set(),
            "databases": set()
        }

        # Languages with better detection
        lang_patterns = {
            "Python": ["python", ".py", "pip install", "import "],
            "JavaScript": ["javascript", ".js", "node ", "npm "],
            "TypeScript": ["typescript", ".ts", ".tsx", "interface ", "type "],
            "Go": ["golang", ".go", "go mod", "package main"],
            "Rust": ["rust", "cargo", ".rs", "fn main"],
            "Java": ["java", "maven", "gradle", ".java"],
            "C++": ["c++", "cpp", ".cpp", ".hpp"],
            "C#": ["c#", "csharp", ".cs", "dotnet"],
        }

        for lang, patterns in lang_patterns.items():
            if any(p in all_lower for p in patterns):
                detected["languages"].add(lang)

        # Frontend Frameworks
        frontend_patterns = {
            "Vue 3": ["vue 3", "vue3", "createapp", "composition api", "<script setup"],
            "Vue 2": ["vue 2", "vue@2", "new vue("],
            "React": ["react", "jsx", "usestate", "useeffect"],
            "Angular": ["angular", "@angular"],
            "Svelte": ["svelte", ".svelte"],
            "Vite": ["vite", "vite.config"],
            "Webpack": ["webpack", "webpack.config"],
        }

        for framework, patterns in frontend_patterns.items():
            if any(p in all_lower for p in patterns):
                detected["frameworks"].add(framework)

        # Backend Frameworks
        backend_patterns = {
            "FastAPI": ["fastapi", "from fastapi", "@app.get", "@app.post"],
            "Flask": ["flask", "from flask import"],
            "Django": ["django", "django."],
            "Express": ["express", "app.listen"],
            "Next.js": ["next.js", "nextjs"],
            "NestJS": ["nestjs", "@nestjs"],
        }

        for framework, patterns in backend_patterns.items():
            if any(p in all_lower for p in patterns):
                detected["frameworks"].add(framework)

        # Tools & Platforms
        tool_patterns = {
            "Git": ["git add", "git commit", "git push", "git clone"],
            "Docker": ["docker", "dockerfile", "docker-compose"],
            "Telegram Bot": ["telegram", "python-telegram-bot", "telebot"],
            "Claude CLI": ["claude", "claude code", "claude-cli"],
            "Uvicorn": ["uvicorn", "uvicorn.run"],
            "npm": ["npm install", "npm run", "package.json"],
            "pnpm": ["pnpm install", "pnpm run"],
            "Nginx": ["nginx", "nginx.conf"],
        }

        for tool, patterns in tool_patterns.items():
            if any(p in all_lower for p in patterns):
                detected["tools"].add(tool)

        # Databases
        db_patterns = {
            "SQLite": ["sqlite", "aiosqlite", ".db"],
            "PostgreSQL": ["postgres", "postgresql", "psql"],
            "MySQL": ["mysql", "mariadb"],
            "MongoDB": ["mongodb", "mongo", "mongoose"],
            "Redis": ["redis", "redis-cli"],
        }

        for db, patterns in db_patterns.items():
            if any(p in all_lower for p in patterns):
                detected["databases"].add(db)

        # Convert sets to sorted lists
        return {k: sorted(list(v)) for k, v in detected.items()}

    def _extract_user_preferences(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract user preferences from conversation."""
        all_text = " ".join([m.get("content", "") for m in messages]).lower()

        preferences = {}

        # UI/Design preferences
        ui_keywords = {
            "minimalist": ["minimalist", "minimal", "简洁", "性冷淡"],
            "modern": ["modern", "现代"],
            "clean": ["clean", "干净"],
            "professional": ["professional", "专业"],
        }

        ui_style = []
        for style, keywords in ui_keywords.items():
            if any(kw in all_text for kw in keywords):
                ui_style.append(style)

        if ui_style:
            preferences["ui_style"] = ui_style

        # Coding style preferences
        if any(word in all_text for word in ["简洁", "concise", "minimal", "简单"]):
            preferences["coding_style"] = "Prefers concise, minimal code"

        if any(word in all_text for word in ["去掉", "remove", "删除", "不要"]):
            preferences["preferences_notes"] = "Prefers removing unnecessary elements"

        return preferences

    def _extract_important_changes(self, messages: List[Dict[str, str]]) -> List[str]:
        """Extract important changes and decisions from conversation."""
        changes = []
        assistant_messages = [m.get("content", "") for m in messages if m.get("role") == "assistant"]

        # Look for implementation keywords
        for msg in assistant_messages:
            msg_lower = msg.lower()

            # UI changes
            if "ui" in msg_lower and ("refactor" in msg_lower or "重构" in msg_lower):
                changes.append("UI refactoring")

            # Configuration changes
            if "port" in msg_lower and any(str(p) in msg for p in range(1000, 65536)):
                changes.append("Configuration update")

            # Feature additions/removals
            if "removed" in msg_lower or "移除" in msg_lower:
                changes.append("Feature removal")
            if "added" in msg_lower or "添加" in msg_lower:
                changes.append("Feature addition")

        return list(set(changes))

    async def extract_and_update_user_profile(self, session_messages: List[Dict[str, str]], working_directory: str):
        """
        Intelligently extract information from session and update USER.md.

        Args:
            session_messages: List of {"role": str, "content": str}
            working_directory: The working directory used in this session
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        user_content = await self.read_file("USER.md") or ""

        # Extract all information
        project_info = self._extract_project_info(working_directory)
        preferred_language = self._detect_language(session_messages)

        all_text = " ".join([m.get("content", "") for m in session_messages])
        tech_stack = self._detect_tech_stack(all_text)
        preferences = self._extract_user_preferences(session_messages)

        # Build updated USER.md
        new_content = []
        new_content.append("# User Profile\n")
        new_content.append("This file stores information about the user that helps personalize interactions.")
        new_content.append("It will be automatically updated as we work together.\n")

        # Preferences section
        new_content.append("## Preferences\n")
        new_content.append(f"- **Preferred Language**: {preferred_language}")

        if preferences.get("ui_style"):
            ui_styles = ", ".join(preferences["ui_style"]).title()
            new_content.append(f"- **UI/Design Style**: {ui_styles}")
        else:
            new_content.append("- **UI/Design Style**: To be learned from project work")

        new_content.append("- **Communication Style**: Clear, direct, focused on implementation")

        if preferences.get("coding_style"):
            new_content.append(f"- **Coding Approach**: {preferences['coding_style']}")
        else:
            new_content.append("- **Coding Approach**: To be learned\n")

        # Current Projects section
        new_content.append("## Current Projects\n")

        # Extract existing projects to avoid duplicates
        project_section_match = re.search(r"## Current Projects\n(.*?)(?=\n##|\Z)", user_content, re.DOTALL)
        existing_projects = []
        if project_section_match:
            existing_projects_text = project_section_match.group(1)
            existing_projects = re.findall(r"### (.*?)\n", existing_projects_text)

        # Add new project if not exists
        if project_info["name"] not in existing_projects:
            new_content.append(f"### {project_info['name']}\n")
            new_content.append(f"- **Path**: `{project_info['short_path']}`")
            new_content.append(f"- **Last Used**: {timestamp}\n")
        else:
            # Keep existing project info but update timestamp
            if project_section_match:
                existing_text = project_section_match.group(1)
                # Update timestamp for this project
                existing_text = re.sub(
                    rf"(### {project_info['name']}\n.*?Last Used:).*?\n",
                    rf"\1 {timestamp}\n",
                    existing_text,
                    flags=re.DOTALL
                )
                new_content.append(existing_text.strip() + "\n")

        # Tech Stack section
        new_content.append("## Tech Stack Experience\n")

        if tech_stack["languages"]:
            new_content.append("### Languages")
            for lang in tech_stack["languages"]:
                if lang not in user_content or "Languages" not in user_content:
                    new_content.append(f"- {lang}")

            # Keep existing languages
            lang_match = re.search(r"### Languages\n(.*?)(?=\n###|\n##|\Z)", user_content, re.DOTALL)
            if lang_match:
                existing_langs = set(re.findall(r"- (.*?)\n", lang_match.group(1)))
                for lang in existing_langs:
                    if lang not in tech_stack["languages"]:
                        new_content.append(f"- {lang}")
            new_content.append("")

        if tech_stack["frameworks"]:
            new_content.append("### Frameworks & Libraries")

            # Merge new and existing
            framework_match = re.search(r"### Frameworks & Libraries\n(.*?)(?=\n###|\n##|\Z)", user_content, re.DOTALL)
            existing_frameworks = set()
            if framework_match:
                existing_frameworks = set(re.findall(r"- (.*?)\n", framework_match.group(1)))

            all_frameworks = set(tech_stack["frameworks"]) | existing_frameworks
            for fw in sorted(all_frameworks):
                new_content.append(f"- {fw}")
            new_content.append("")

        if tech_stack["tools"] or tech_stack["databases"]:
            new_content.append("### Tools & Platforms")

            # Merge tools and databases
            tool_match = re.search(r"### Tools & Platforms\n(.*?)(?=\n###|\n##|\Z)", user_content, re.DOTALL)
            existing_tools = set()
            if tool_match:
                existing_tools = set(re.findall(r"- (.*?)\n", tool_match.group(1)))

            all_tools = set(tech_stack["tools"]) | set(tech_stack["databases"]) | existing_tools
            for tool in sorted(all_tools):
                new_content.append(f"- {tool}")
            new_content.append("")

        # Working Habits section
        new_content.append("## Working Habits\n")
        if preferences.get("preferences_notes"):
            new_content.append(f"- {preferences['preferences_notes']}")
        else:
            new_content.append("*Learning from interaction patterns*\n")

        # Notes section
        new_content.append("## Notes\n")

        # Preserve existing notes
        notes_match = re.search(r"## Notes\n(.*?)(?=\n---|\Z)", user_content, re.DOTALL)
        if notes_match and notes_match.group(1).strip() and "*Additional context" not in notes_match.group(1):
            new_content.append(notes_match.group(1).strip() + "\n")
        else:
            new_content.append("*Additional context and preferences*\n")

        # Footer
        new_content.append("---\n")
        new_content.append(f"*Last updated: {timestamp}*\n")

        # Write updated content
        final_content = "\n".join(new_content)
        await self.write_file("USER.md", final_content)

        # Generate PROJECT.md for this project
        await self._update_project_context(project_info, tech_stack, session_messages)

        return {
            "updated": True,
            "project": project_info["name"],
            "new_languages": tech_stack["languages"],
            "new_frameworks": tech_stack["frameworks"],
            "new_tools": tech_stack["tools"]
        }

    async def _update_project_context(
        self,
        project_info: Dict[str, Any],
        tech_stack: Dict[str, List[str]],
        messages: List[Dict[str, str]]
    ):
        """Create or update PROJECT.md with project-specific context."""
        project_name = project_info["name"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Try to read existing PROJECT.md
        project_content = await self.read_file("PROJECT.md") or ""

        # Extract important changes
        changes = self._extract_important_changes(messages)

        # Build PROJECT.md content
        content = []
        content.append(f"# Project: {project_name}\n")
        content.append(f"**Path**: `{project_info['short_path']}`\n")

        content.append("## Tech Stack\n")

        if tech_stack["languages"]:
            content.append("### Languages")
            for lang in tech_stack["languages"]:
                content.append(f"- {lang}")
            content.append("")

        if tech_stack["frameworks"]:
            content.append("### Frameworks")
            for fw in tech_stack["frameworks"]:
                content.append(f"- {fw}")
            content.append("")

        if tech_stack["tools"]:
            content.append("### Tools")
            for tool in tech_stack["tools"]:
                content.append(f"- {tool}")
            content.append("")

        if tech_stack["databases"]:
            content.append("### Databases")
            for db in tech_stack["databases"]:
                content.append(f"- {db}")
            content.append("")

        # Recent Changes section
        content.append("## Recent Changes\n")

        # Extract existing changes
        changes_match = re.search(r"## Recent Changes\n(.*?)(?=\n##|\Z)", project_content, re.DOTALL)
        existing_changes = []
        if changes_match:
            existing_changes = changes_match.group(1).strip().split("\n")
            existing_changes = [c for c in existing_changes[:5] if c.strip()]  # Keep last 5

        # Add new changes
        for change in changes:
            change_line = f"- **{timestamp}**: {change}"
            if change_line not in "\n".join(existing_changes):
                content.append(change_line)

        # Add existing changes
        for change in existing_changes[:5]:
            if change.strip() and change not in "\n".join(content):
                content.append(change)

        content.append("")
        content.append("---\n")
        content.append(f"*Last updated: {timestamp}*\n")

        await self.write_file("PROJECT.md", "\n".join(content))


# Global memory manager
memory_manager = MemoryManager()
