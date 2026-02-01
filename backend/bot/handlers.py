"""Telegram bot command handlers."""

import asyncio
import html
import logging
import os
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.claude.runner import ClaudeRunner
    from backend.claude.session import SessionContext

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

from backend.config import settings
from backend.bot.middleware import require_auth, admin_only
from backend.claude.runner import runner_manager, StreamEvent, RunnerState
from backend.claude.session import session_manager, SessionState
from backend.claude.providers import get_llm_provider
from backend.memory.manager import memory_manager
from backend.db.models import db

logger = logging.getLogger(__name__)


# Minimum interval between message updates (seconds) to avoid Telegram rate limits
MIN_UPDATE_INTERVAL = 1.0


class StreamingMessageUpdater:
    """
    Manages streaming message updates to Telegram with rate limiting and batching.

    Features:
    - Rate limiting to avoid Telegram API limits
    - Smart batching of updates
    - Automatic message splitting for long content
    - Error recovery
    """

    def __init__(self, message, min_update_interval: float = MIN_UPDATE_INTERVAL):
        self.message = message
        self.min_update_interval = min_update_interval
        self.last_update_time = 0
        self.buffer = ""
        self.sent_message = None
        self.update_count = 0
        self.error_count = 0

    async def append(self, text: str, force: bool = False):
        """
        Append text to buffer and potentially update the message.

        Args:
            text: Text to append
            force: Force immediate update regardless of interval
        """
        self.buffer += text
        current_time = time.time()

        # Determine if we should update
        should_update = (
            force
            or len(self.buffer) >= STREAM_BUFFER_SIZE
            or (current_time - self.last_update_time) >= self.min_update_interval
        )

        if should_update:
            await self.flush()

    async def flush(self):
        """Send/update the current buffer content."""
        if not self.buffer:
            return

        current_time = time.time()

        # Avoid too frequent updates
        time_since_last = current_time - self.last_update_time
        if time_since_last < 0.5 and self.update_count > 0:
            return

        try:
            truncated = smart_truncate(self.buffer)

            if self.sent_message is None:
                # First message - send it
                self.sent_message = await self.message.reply_text(truncated)
            else:
                # Update existing message
                try:
                    await self.sent_message.edit_text(truncated)
                except Exception as edit_error:
                    # If edit fails (message unchanged, etc.), log but continue
                    if "Message is not modified" not in str(edit_error):
                        logger.debug(f"Edit failed: {edit_error}")

            self.last_update_time = current_time
            self.update_count += 1
            self.error_count = 0  # Reset error count on success

        except Exception as e:
            self.error_count += 1
            logger.error(f"Failed to update message (attempt {self.error_count}): {e}")

            # If too many errors, give up and send as new message
            if self.error_count >= 3:
                try:
                    await self.message.reply_text(
                        f"⚠️ Update error. Continuing...\n\n{smart_truncate(self.buffer)}"
                    )
                    self.error_count = 0
                except Exception:
                    pass

    async def finalize(self):
        """Send final update with all remaining content."""
        await self.flush()


# Maximum message length for Telegram
MAX_MESSAGE_LENGTH = 4096
# Minimum update interval to avoid rate limits (seconds)
MIN_UPDATE_INTERVAL = 1.5
# Buffer size for streaming updates (characters)
STREAM_BUFFER_SIZE = 200


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def smart_truncate(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """
    Intelligently truncate message, preserving code blocks and structure.

    Tries to:
    1. Keep complete code blocks
    2. Break at paragraph boundaries
    3. Preserve important information at start and end
    """
    if len(text) <= max_length:
        return text

    # Calculate how much we can show
    available = max_length - 200  # Reserve for truncation notice

    # Try to find a good breaking point
    # Prefer breaking at double newline (paragraph)
    half = available // 2

    # Get start portion
    start_text = text[:half]
    last_para = start_text.rfind('\n\n')
    if last_para > half * 0.7:  # If we found a paragraph break in last 30%
        start_text = text[:last_para]

    # Get end portion
    end_text = text[-half:]
    first_para = end_text.find('\n\n')
    if first_para > 0 and first_para < half * 0.3:  # If found in first 30%
        end_text = end_text[first_para + 2:]
    else:
        end_text = text[-half:]

    truncated_chars = len(text) - len(start_text) - len(end_text)
    notice = f"\n\n... [{truncated_chars} chars truncated] ...\n\n"

    return start_text + notice + end_text


async def send_long_message(update: Update, text: str, parse_mode: Optional[str] = None):
    """Send a message, intelligently splitting if necessary."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        await update.message.reply_text(text, parse_mode=parse_mode)
        return

    # Smart chunking that respects code blocks and paragraphs
    chunks = []
    current = ""
    in_code_block = False

    for line in text.split("\n"):
        # Track code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block

        potential_length = len(current) + len(line) + 1

        # If adding this line exceeds limit
        if potential_length > MAX_MESSAGE_LENGTH - 100:
            # If we're in a code block, try to close it
            if in_code_block:
                current += "\n```"
                in_code_block = False
            chunks.append(current)
            # If we just closed a code block, open it again in next chunk
            current = "```\n" + line if in_code_block else line
        else:
            current = current + "\n" + line if current else line

    if current:
        chunks.append(current)

    # Send all chunks
    for i, chunk in enumerate(chunks):
        prefix = f"📄 Part {i+1}/{len(chunks)}\n\n" if len(chunks) > 1 else ""
        await update.message.reply_text(prefix + chunk, parse_mode=parse_mode)
        # Add small delay to avoid rate limits
        if i < len(chunks) - 1:
            await asyncio.sleep(0.3)


# ============ Helper Functions ============

def get_or_create_runner(user_id: int, session = None):
    """
    Get or create a runner for a session.

    If session is provided, uses session-based runner.
    If no session, gets/creates active session first.

    Returns None if max sessions exceeded.
    """
    if session is None:
        session = session_manager.get_active_session(user_id)
        if not session:
            # Create a temporary session for commands
            session = session_manager.create_session(
                user_id=user_id,
                working_directory=settings.approved_directory_path
            )

    runner = runner_manager.get_runner(
        session_id=session.session_id,
        user_id=user_id,
        working_directory=session.working_directory
    )

    if runner and session.claude_session_id:
        runner.session_id = session.claude_session_id

    return runner


# ============ Command Handlers ============

def get_main_menu_keyboard():
    """Get main menu inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🆕 New Session", callback_data="menu:new"),
            InlineKeyboardButton("▶️ Continue", callback_data="menu:continue"),
        ],
        [
            InlineKeyboardButton("📂 Folders", callback_data="menu:show_dirs"),
            InlineKeyboardButton("📍 PWD", callback_data="menu:pwd"),
            InlineKeyboardButton("📊 Status", callback_data="menu:status"),
        ],
        [
            InlineKeyboardButton("📋 Sessions", callback_data="menu:sessions"),
            InlineKeyboardButton("💾 Export", callback_data="menu:export"),
            InlineKeyboardButton("🛑 End", callback_data="menu:end"),
        ],
    ])


def get_quick_actions_keyboard():
    """Get quick actions keyboard for common coding tasks."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Review Code", callback_data="quick:review"),
            InlineKeyboardButton("🐛 Debug", callback_data="quick:debug"),
        ],
        [
            InlineKeyboardButton("📝 Explain", callback_data="quick:explain"),
            InlineKeyboardButton("✨ Improve", callback_data="quick:improve"),
        ],
        [
            InlineKeyboardButton("🧪 Write Tests", callback_data="quick:tests"),
            InlineKeyboardButton("📖 Add Docs", callback_data="quick:docs"),
        ],
        [
            InlineKeyboardButton("📂 Menu", callback_data="menu:show"),
        ],
    ])


@require_auth
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user

    # Get provider info
    provider = get_llm_provider()
    provider_name = provider.get_name() if provider else "Claude CLI (Pro)"

    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}!\n\n"
        f"🤖 **ccBot** - Claude Code in Telegram\n"
        f"🔌 Provider: {provider_name}\n\n"
        "💡 Tap the **Menu** button (bottom left) for commands.\n"
        "Or select an action below:",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )


@require_auth
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command - show quick menu."""
    await update.message.reply_text(
        "📋 **Quick Menu**\n\nSelect an action:",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )


@require_auth
async def actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /actions command - show quick coding actions."""
    await update.message.reply_text(
        "⚡ **Quick Actions**\n\nSelect a coding task:",
        parse_mode="Markdown",
        reply_markup=get_quick_actions_keyboard()
    )


@require_auth
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start_command(update, context)


@require_auth
async def new_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - start a new session."""
    user_id = update.effective_user.id

    # Create new session (runner will be created on first use)
    session = session_manager.create_session(
        user_id=user_id,
        working_directory=settings.approved_directory_path
    )

    await update.message.reply_text(
        f"✨ New session started!\n\n"
        f"**Session ID:** `{session.session_id}`\n"
        f"**Working directory:** `{session.working_directory}`\n\n"
        "Send me a message to start working.",
        parse_mode="Markdown"
    )


@require_auth
async def continue_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /continue command - continue last session."""
    user_id = update.effective_user.id

    session = session_manager.get_active_session(user_id)
    if not session:
        await update.message.reply_text(
            "No active session found. Use /new to start a new session."
        )
        return

    # Runner will be auto-created when needed
    await update.message.reply_text(
        f"📂 Continuing session `{session.session_id}`\n\n"
        f"**Messages:** {len(session.messages)}\n"
        f"**Working directory:** `{session.working_directory}`\n"
        f"**Cost so far:** ${session.total_cost:.4f}",
        parse_mode="Markdown"
    )


@require_auth
async def sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sessions command - list user's sessions."""
    user_id = update.effective_user.id
    sessions = session_manager.get_user_sessions(user_id)

    if not sessions:
        await update.message.reply_text("No sessions found. Use /new to start one.")
        return

    lines = ["**Your Sessions:**\n"]
    for s in sessions[:10]:
        status = "🟢" if s.state == SessionState.IDLE else "🔄"
        title = s.title or "Untitled"
        lines.append(
            f"{status} `{s.session_id}` - {title}\n"
            f"   📁 {s.working_directory.name} | 💬 {len(s.messages)} msgs"
        )

    # Add buttons for session selection
    keyboard = [
        [InlineKeyboardButton(f"{s.session_id[:8]}", callback_data=f"session:{s.session_id}")]
        for s in sessions[:5]
    ]

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


@require_auth
async def dirs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dirs command - list and quick switch directories."""
    user_id = update.effective_user.id

    # Get approved directory subdirectories
    approved_dir = settings.approved_directory_path

    try:
        # Get all subdirectories in approved directory
        subdirs = []
        if approved_dir.exists():
            subdirs = [d for d in approved_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            subdirs = sorted(subdirs, key=lambda x: x.stat().st_mtime, reverse=True)[:10]

        # Get recent directories from sessions
        sessions = session_manager.get_user_sessions(user_id)
        recent_dirs = []
        seen = set()
        for s in sessions:
            dir_path = str(s.working_directory)
            if dir_path not in seen:
                recent_dirs.append(s.working_directory)
                seen.add(dir_path)

        # Build message
        lines = ["📂 **Available Directories**\n"]

        # Current directory
        session = session_manager.get_active_session(user_id)
        runner = runner_manager.get_active_runner(session.session_id) if session else None
        current_dir = runner.working_directory if runner else settings.approved_directory_path
        lines.append(f"**Current:** `{current_dir}`\n")

        # Recent directories
        if recent_dirs:
            lines.append("**Recently Used:**")
            for i, d in enumerate(recent_dirs[:5], 1):
                is_current = "👉 " if str(d) == str(current_dir) else "   "
                lines.append(f"{is_current}{i}. `{d.name}/`")
            lines.append("")

        # Available subdirectories
        if subdirs:
            lines.append("**Available in Workspace:**")
            for d in subdirs[:8]:
                is_current = "👉 " if str(d) == str(current_dir) else "   "
                lines.append(f"{is_current}📁 `{d.name}/`")

        lines.append(f"\n💡 **Usage:**")
        lines.append(f"• `/cd <folder>` - Switch to folder")
        lines.append(f"• `/cd ..` - Go up one level")
        lines.append(f"• `/pwd` - Show current path")

        # Create quick switch buttons for recent dirs
        keyboard = []
        for d in recent_dirs[:3]:
            keyboard.append([InlineKeyboardButton(
                f"📂 {d.name}",
                callback_data=f"chdir:{d.name}"
            )])

        # Add subdirs buttons
        for d in subdirs[:3]:
            if d not in recent_dirs[:3]:
                keyboard.append([InlineKeyboardButton(
                    f"📁 {d.name}",
                    callback_data=f"chdir:{d.name}"
                )])

        if keyboard:
            keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="menu:show")])
            await update.message.reply_text(
                "\n".join(lines),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.exception(f"Error in dirs command: {e}")
        await update.message.reply_text(f"❌ Error listing directories: {e}")


@require_auth
async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cd command - change working directory."""
    user_id = update.effective_user.id

    if not context.args:
        # Show help with quick access
        await dirs_command(update, context)
        return

    path_str = " ".join(context.args)
    path = Path(path_str).expanduser()

    session = session_manager.get_active_session(user_id)
    runner = get_or_create_runner(user_id, session)

    if not runner:
        await update.message.reply_text("❌ Cannot create session. Max sessions limit reached.")
        return

    # Handle relative paths
    if not path.is_absolute():
        # Try relative to current directory
        path = runner.working_directory / path

        # If not found, try relative to approved directory
        if not path.exists():
            path = settings.approved_directory_path / path_str

    if runner.change_directory(path):
        if session:
            session.working_directory = runner.working_directory

        await update.message.reply_text(
            f"✅ Changed to: `{runner.working_directory}`\n\n"
            f"📂 Full path: `{runner.working_directory}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ Cannot change to: `{path}`\n\n"
            f"**Possible reasons:**\n"
            f"• Directory doesn't exist\n"
            f"• Path is outside approved directory\n\n"
            f"**Approved directory:** `{settings.approved_directory_path}`\n\n"
            f"Use `/dirs` to see available directories.",
            parse_mode="Markdown"
        )


@require_auth
async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ls command - list current directory."""
    user_id = update.effective_user.id
    runner = get_or_create_runner(user_id)

    if not runner:
        await update.message.reply_text("❌ Cannot create session. Max sessions limit reached.")
        return

    try:
        entries = list(runner.working_directory.iterdir())
        dirs = sorted([e for e in entries if e.is_dir()], key=lambda x: x.name)
        files = sorted([e for e in entries if e.is_file()], key=lambda x: x.name)

        lines = [f"📂 `{runner.working_directory}`\n"]

        if dirs:
            lines.append("**Directories:**")
            for d in dirs[:20]:
                lines.append(f"  📁 {d.name}/")

        if files:
            lines.append("\n**Files:**")
            for f in files[:30]:
                size = f.stat().st_size
                size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                lines.append(f"  📄 {f.name} ({size_str})")

        if len(dirs) > 20 or len(files) > 30:
            lines.append(f"\n... and more ({len(dirs)} dirs, {len(files)} files total)")

        await send_long_message(update, "\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


@require_auth
async def pwd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pwd command - show current directory."""
    user_id = update.effective_user.id
    runner = get_or_create_runner(user_id)

    if not runner:
        await update.message.reply_text("❌ Cannot create session. Max sessions limit reached.")
        return

    await update.message.reply_text(
        f"📂 Current directory:\n`{runner.working_directory}`",
        parse_mode="Markdown"
    )


@require_auth
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show current status."""
    user_id = update.effective_user.id

    session = session_manager.get_active_session(user_id)
    runner = runner_manager.get_active_runner(session.session_id) if session else None

    # Get provider info
    provider = get_llm_provider()
    if provider:
        provider_info = f"🔌 Provider: {provider.get_name()}"
    else:
        provider_info = "🔌 Provider: Claude CLI (Interactive)"

    lines = ["**Status:**\n"]
    lines.append(provider_info)

    if runner:
        lines.append(f"🤖 Runner: {runner.state.value}")
        lines.append(f"🔄 Process: {'alive' if runner.is_alive else 'stopped'}")
        lines.append(f"📂 Directory: `{runner.working_directory}`")
    else:
        lines.append("🤖 Runner: Not started yet")

    if session:
        lines.append(f"\n**Session:** `{session.session_id}`")
        lines.append(f"💬 Messages: {len(session.messages)}")
        lines.append(f"💰 Cost: ${session.total_cost:.4f}")
        lines.append(f"📊 State: {session.state.value}")
        if runner.session_id:
            lines.append(f"🔗 Claude Session: `{runner.session_id[:8]}...`")

    # Tip for cost check
    if provider is None:
        lines.append("\n💡 **Tip:** Send `/cost` to check billing info")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_auth
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command - stop current task."""
    user_id = update.effective_user.id

    session = session_manager.get_active_session(user_id)
    if session:
        await runner_manager.stop_runner(session.session_id, user_id)
        session_manager.update_session_state(session.session_id, SessionState.IDLE)

    await update.message.reply_text("🛑 Stopped current task.")


@require_auth
async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /end command - end current session and save."""
    user_id = update.effective_user.id

    # Get and close session
    session = session_manager.get_active_session(user_id)
    if not session:
        await update.message.reply_text("No active session.")
        return

    # Stop any running task
    await runner_manager.stop_runner(session.session_id, user_id)

    # Save session to file
    await session_manager.save_session_to_file(session.session_id)

    # Extract user preferences and update USER.md
    messages_data = [
        {"role": m.role, "content": m.content}
        for m in session.messages
    ]
    profile_update = await memory_manager.extract_and_update_user_profile(
        messages_data,
        str(session.working_directory)
    )

    # Clear active session
    session_manager.update_session_state(session.session_id, SessionState.IDLE)
    session_manager._active_session.pop(user_id, None)

    # Build response
    response = (
        f"✅ Session `{session.session_id}` ended and saved.\n"
        f"💬 {len(session.messages)} messages\n"
        f"💰 Cost: ${session.total_cost:.4f}\n"
    )

    # Add profile update info
    if profile_update.get("updated"):
        response += "\n📝 **USER.md updated:**\n"
        if profile_update.get("new_languages"):
            response += f"  • Languages: {', '.join(profile_update['new_languages'])}\n"
        if profile_update.get("new_tools"):
            response += f"  • Tools: {', '.join(profile_update['new_tools'])}\n"
        if profile_update.get("new_projects"):
            response += f"  • Added {profile_update['new_projects']} project path(s)\n"

    response += "\nUse /new to start a new session."

    await update.message.reply_text(response, parse_mode="Markdown")


@require_auth
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /export command - export session history."""
    user_id = update.effective_user.id

    session = session_manager.get_active_session(user_id)
    if not session:
        await update.message.reply_text("No active session to export.")
        return

    markdown = session.to_markdown()

    # Save to file
    await session_manager.save_session_to_file(session.session_id)

    # Send as document if too long
    if len(markdown) > MAX_MESSAGE_LENGTH:
        filepath = settings.sessions_path / f"{session.session_id}.md"
        await update.message.reply_document(
            document=open(filepath, "rb"),
            filename=f"session_{session.session_id}.md",
            caption=f"Session export: {session.session_id}"
        )
    else:
        await update.message.reply_text(
            f"```\n{markdown}\n```",
            parse_mode="Markdown"
        )


@require_auth
async def tree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tree command - show directory tree structure."""
    user_id = update.effective_user.id
    runner = get_or_create_runner(user_id)

    if not runner:
        await update.message.reply_text("❌ Cannot create session. Max sessions limit reached.")
        return

    max_depth = 2
    if context.args:
        try:
            max_depth = int(context.args[0])
            max_depth = min(max_depth, 5)  # Limit to 5 levels
        except ValueError:
            await update.message.reply_text("Usage: /tree [depth]\nExample: /tree 3")
            return

    try:
        def build_tree(path: Path, prefix: str = "", depth: int = 0) -> list:
            """Recursively build directory tree."""
            if depth > max_depth:
                return []

            lines = []
            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                # Limit entries to prevent huge output
                entries = entries[:50]

                for i, entry in enumerate(entries):
                    is_last = i == len(entries) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = "    " if is_last else "│   "

                    if entry.is_dir():
                        lines.append(f"{prefix}{current_prefix}📁 {entry.name}/")
                        if depth < max_depth:
                            lines.extend(build_tree(entry, prefix + next_prefix, depth + 1))
                    else:
                        size = entry.stat().st_size
                        size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                        lines.append(f"{prefix}{current_prefix}📄 {entry.name} ({size_str})")

                if len(list(path.iterdir())) > 50:
                    lines.append(f"{prefix}... (truncated)")

            except PermissionError:
                lines.append(f"{prefix}[Permission Denied]")

            return lines

        tree_lines = [f"📂 {runner.working_directory}", ""]
        tree_lines.extend(build_tree(runner.working_directory))

        tree_text = "\n".join(tree_lines)
        await send_long_message(update, f"```\n{tree_text}\n```", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


@require_auth
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - clear session history but keep session active."""
    user_id = update.effective_user.id

    session = session_manager.get_active_session(user_id)
    if not session:
        await update.message.reply_text("No active session.")
        return

    # Save current session before clearing
    await session_manager.save_session_to_file(session.session_id)

    message_count = len(session.messages)
    cost = session.total_cost

    # Clear messages but keep session
    session.messages.clear()
    session.total_cost = 0

    await update.message.reply_text(
        f"🗑️ **Session History Cleared**\n\n"
        f"Cleared {message_count} messages (${cost:.4f})\n"
        f"Session `{session.session_id}` is still active.\n\n"
        f"The history was saved to file before clearing.",
        parse_mode="Markdown"
    )


@require_auth
async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /usage command - show Claude usage and provide web link."""
    user_id = update.effective_user.id

    # Get local stats
    sessions = session_manager.get_user_sessions(user_id)
    total_cost = sum(s.total_cost for s in sessions)
    total_messages = sum(len(s.messages) for s in sessions)

    # Build response
    response = (
        "📊 **Usage Information**\n\n"
        f"**Local Stats (This Bot):**\n"
        f"• Total sessions: {len(sessions)}\n"
        f"• Total messages: {total_messages}\n"
        f"• Estimated cost: ${total_cost:.4f}\n\n"
        f"**View Full Claude Usage:**\n"
        f"🌐 Visit: https://claude.ai/settings/usage\n\n"
        f"_Note: The link shows your overall Claude Pro usage, "
        f"including usage from this bot and claude.ai web._"
    )

    await update.message.reply_text(
        response,
        parse_mode="Markdown",
        disable_web_page_preview=False
    )


@require_auth
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show usage statistics."""
    user_id = update.effective_user.id

    sessions = session_manager.get_user_sessions(user_id)

    if not sessions:
        await update.message.reply_text("No session history yet.")
        return

    total_messages = sum(len(s.messages) for s in sessions)
    total_cost = sum(s.total_cost for s in sessions)
    total_sessions = len(sessions)

    # Calculate average
    avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
    avg_cost = total_cost / total_sessions if total_sessions > 0 else 0

    # Find most used directory
    dir_counts = {}
    for s in sessions:
        dir_name = str(s.working_directory)
        dir_counts[dir_name] = dir_counts.get(dir_name, 0) + 1

    most_used_dir = max(dir_counts.items(), key=lambda x: x[1])[0] if dir_counts else "N/A"

    stats_text = (
        f"📊 **Your Statistics**\n\n"
        f"**Total Sessions:** {total_sessions}\n"
        f"**Total Messages:** {total_messages}\n"
        f"**Total Cost:** ${total_cost:.4f}\n\n"
        f"**Averages per Session:**\n"
        f"  • Messages: {avg_messages:.1f}\n"
        f"  • Cost: ${avg_cost:.4f}\n\n"
        f"**Most Used Directory:**\n"
        f"  `{Path(most_used_dir).name}/`"
    )

    await update.message.reply_text(stats_text, parse_mode="Markdown")


# ============ Message Handler ============

async def _handle_with_claude_cli(message, text, session, user_id, context=None):
    """Handle message using Claude CLI with optimized streaming."""
    runner = get_or_create_runner(user_id, session)

    if not runner:
        await message.reply_text(
            "❌ Cannot create runner. Max sessions limit reached.\n\n"
            "Use /end to close an old session first."
        )
        return ""

    continue_session = runner.session_id is not None

    # Use the new streaming updater
    updater = StreamingMessageUpdater(message)
    response_parts = []
    last_typing_time = time.time()
    event_count = 0
    tool_uses = []

    try:
        async for event in runner.run(text, continue_session=continue_session):
            event_count += 1

            # Send typing indicator periodically
            current_time = time.time()
            if context and current_time - last_typing_time > 4:
                try:
                    await context.bot.send_chat_action(
                        chat_id=message.chat_id,
                        action=ChatAction.TYPING
                    )
                    last_typing_time = current_time
                except Exception:
                    pass

            if event.type == "text":
                # Append text to streaming buffer
                await updater.append(event.content)

            elif event.type == "tool_use":
                tool_uses.append(event.content)
                # Add tool notification
                tool_msg = f"\n\n🔧 Using tool: {event.content}"
                await updater.append(tool_msg, force=True)

            elif event.type == "result":
                # Store session info
                if event.metadata.get("session_id"):
                    session.claude_session_id = event.metadata["session_id"]
                    runner.session_id = event.metadata["session_id"]
                if event.metadata.get("cost"):
                    cost = event.metadata["cost"]
                    session_manager.add_cost(session.session_id, cost)
                    # Add cost info to message
                    await updater.append(f"\n\n💰 Cost: ${cost:.4f}", force=True)
                response_parts.append(event.content)

            elif event.type == "error":
                error_msg = f"\n\n❌ Error: {event.content}"
                await updater.append(error_msg, force=True)
                logger.error(f"Claude CLI error: {event.content}")

            elif event.type == "done":
                # Final flush
                await updater.finalize()

        # If no events received
        if event_count == 0:
            logger.warning("No events received from Claude CLI")
            await message.reply_text(
                "⚠️ No response from Claude CLI.\n\n"
                "Possible issues:\n"
                "• Claude CLI not properly configured\n"
                "• Session timeout\n"
                "• Network issues\n\n"
                "Please try again or use /new to start fresh."
            )
            return ""

        # Build final response
        final_response = updater.buffer or "\n".join(response_parts)

        # If we never sent a message, send the final response
        if updater.sent_message is None and final_response:
            await message.reply_text(smart_truncate(final_response))

        return final_response

    except asyncio.CancelledError:
        await message.reply_text("⏹️ Task cancelled by user.")
        raise
    except Exception as e:
        logger.exception(f"Error in Claude CLI handler: {e}")
        await message.reply_text(
            f"❌ Unexpected error: {str(e)}\n\n"
            "Please try again or contact admin if the problem persists."
        )
        raise


async def _handle_with_api_provider(message, text, session, provider, context=None):
    """Handle message using API provider with optimized streaming."""
    # Build messages from session history
    messages = []
    for msg in session.get_recent_messages(20):
        messages.append({
            "role": msg.role,
            "content": msg.content
        })
    # Add current message
    messages.append({"role": "user", "content": text})

    # Get system prompt from SOUL.md
    system = await memory_manager.get_soul()

    # Use streaming updater
    updater = StreamingMessageUpdater(message)
    last_typing_time = time.time()
    chunk_count = 0

    try:
        async for chunk in provider.chat(messages, system=system, stream=True):
            chunk_count += 1

            # Send typing indicator periodically
            current_time = time.time()
            if context and current_time - last_typing_time > 4:
                try:
                    await context.bot.send_chat_action(
                        chat_id=message.chat_id,
                        action=ChatAction.TYPING
                    )
                    last_typing_time = current_time
                except Exception:
                    pass

            # Append chunk to buffer
            await updater.append(chunk)

        # Final flush
        await updater.finalize()

        # Check if we got any response
        if chunk_count == 0 or not updater.buffer:
            logger.warning("No response from API provider")
            await message.reply_text(
                "⚠️ No response from API.\n\n"
                "Possible issues:\n"
                "• API key not configured\n"
                "• Rate limit exceeded\n"
                "• Network issues\n\n"
                "Please check your configuration and try again."
            )
            return ""

        return updater.buffer

    except asyncio.CancelledError:
        await message.reply_text("⏹️ Task cancelled by user.")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"API provider error: {e}")

        # Provide helpful error messages
        if "rate_limit" in error_msg.lower():
            await message.reply_text(
                "⚠️ Rate limit exceeded.\n\n"
                "Please wait a moment and try again."
            )
        elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            await message.reply_text(
                "❌ Authentication failed.\n\n"
                "Please check your API key configuration."
            )
        else:
            await message.reply_text(
                f"❌ API Error: {error_msg}\n\n"
                "Please try again or contact admin if the problem persists."
            )
        raise


@require_auth
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages - send to LLM with enhanced UX."""
    user_id = update.effective_user.id

    # Handle both new messages and edited messages
    message = update.message or update.edited_message
    if not message:
        return

    text = message.text
    if not text:
        return

    # Get or create session
    session = session_manager.get_active_session(user_id)
    if not session:
        session = session_manager.create_session(
            user_id=user_id,
            working_directory=settings.approved_directory_path
        )
        # Send welcome message for new session
        await message.reply_text(
            f"✨ New session started: `{session.session_id}`\n"
            f"📂 Working in: `{session.working_directory.name}/`",
            parse_mode="Markdown"
        )

    # Check if runner is busy before doing anything
    runner = runner_manager.get_active_runner(session.session_id)
    if runner and runner.is_running:
        await message.reply_text(
            "⏳ Still processing your previous request...\n\n"
            "You can:\n"
            "• Wait for it to complete\n"
            "• Use /stop to cancel\n"
            "• Use /status to check progress",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛑 Stop", callback_data="menu:stop_task")
            ]])
        )
        return

    # Add user message to session
    session.add_message("user", text)
    session_manager.update_session_state(session.session_id, SessionState.PROCESSING)

    # Show initial typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    # Send processing notification
    processing_msg = await message.reply_text("🤔 Processing your request...")

    try:
        # Check which provider to use
        provider = get_llm_provider()

        if provider is None:
            # Use Claude CLI (default)
            await processing_msg.edit_text("🤖 Invoking Claude Code CLI...")
            full_response = await _handle_with_claude_cli(message, text, session, user_id, context)
        else:
            # Use API provider
            provider_name = provider.get_name()
            await processing_msg.edit_text(f"🔌 Connecting to {provider_name}...")
            full_response = await _handle_with_api_provider(message, text, session, provider, context)

        # Delete processing message
        try:
            await processing_msg.delete()
        except Exception:
            pass

        # Add assistant response to session
        if full_response:
            session.add_message("assistant", full_response)

        session_manager.update_session_state(session.session_id, SessionState.IDLE)

        # Send completion notification with stats
        completion_text = (
            f"✅ Task completed\n"
            f"💬 Messages: {len(session.messages)}\n"
            f"💰 Total cost: ${session.total_cost:.4f}"
        )

        # Only send if response was actually generated
        if full_response:
            await message.reply_text(
                completion_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚡ Quick Actions", callback_data="show:actions"),
                    InlineKeyboardButton("📋 Menu", callback_data="menu:show")
                ]])
            )

    except asyncio.CancelledError:
        # Task was cancelled
        session_manager.update_session_state(session.session_id, SessionState.IDLE)
        runner = runner_manager.get_active_runner(session.session_id)
        if runner:
            runner.state = RunnerState.IDLE
        try:
            await processing_msg.edit_text("⏹️ Task cancelled.")
        except Exception:
            pass

    except Exception as e:
        logger.exception(f"Error processing message for user {user_id}")
        session_manager.update_session_state(session.session_id, SessionState.ERROR)

        # Reset runner state so it can accept new requests
        runner = runner_manager.get_active_runner(session.session_id)
        if runner:
            runner.state = RunnerState.IDLE

        # Provide detailed error message
        error_type = type(e).__name__
        error_msg = str(e)

        try:
            await processing_msg.edit_text(
                f"❌ **Error: {error_type}**\n\n"
                f"Details: {error_msg[:200]}\n\n"
                f"The error has been logged. You can:\n"
                f"• Try again with a different prompt\n"
                f"• Use /new to start fresh\n"
                f"• Use /status to check system status",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🆕 New Session", callback_data="menu:new"),
                    InlineKeyboardButton("📊 Status", callback_data="menu:status")
                ]])
            )
        except Exception:
            # If editing fails, send as new message
            await message.reply_text(f"❌ Error: {error_msg[:500]}")


# ============ Callback Handler ============

# Quick action prompts
QUICK_PROMPTS = {
    "review": "Please review the code in the current directory. Look for bugs, security issues, and suggest improvements.",
    "debug": "Help me debug the current project. Check for common issues and errors.",
    "explain": "Explain the main code structure and logic in the current directory.",
    "improve": "Suggest improvements for the code quality, performance, and maintainability.",
    "tests": "Write unit tests for the main functions in the current project.",
    "docs": "Add documentation comments to the code that lacks them.",
}


@require_auth
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    user_id = update.effective_user.id

    data = query.data

    # Handle menu actions
    if data.startswith("menu:"):
        action = data.split(":")[1]
        await query.answer()

        if action == "show":
            await query.edit_message_text(
                "📋 **Quick Menu**\n\nSelect an action:",
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )

        elif action == "new":
            # Create new session (runner will be created on first use)
            session = session_manager.create_session(
                user_id=user_id,
                working_directory=settings.approved_directory_path
            )

            await query.edit_message_text(
                f"✨ **New session started!**\n\n"
                f"Session ID: `{session.session_id}`\n"
                f"📂 Directory: `{session.working_directory}`\n\n"
                f"Send a message to start coding!",
                parse_mode="Markdown",
                reply_markup=get_quick_actions_keyboard()
            )

        elif action == "continue":
            session = session_manager.get_active_session(user_id)
            if session:
                await query.edit_message_text(
                    f"▶️ **Continuing session**\n\n"
                    f"Session: `{session.session_id}`\n"
                    f"💬 Messages: {len(session.messages)}\n"
                    f"📂 Directory: `{session.working_directory}`",
                    parse_mode="Markdown",
                    reply_markup=get_quick_actions_keyboard()
                )
            else:
                await query.edit_message_text(
                    "No active session. Create a new one?",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🆕 New Session", callback_data="menu:new")
                    ]])
                )

        elif action == "ls":
            runner = get_or_create_runner(user_id)
            if not runner:
                await query.edit_message_text("❌ Cannot create session. Max sessions limit reached.")
                return
            try:
                entries = list(runner.working_directory.iterdir())
                dirs = sorted([e for e in entries if e.is_dir()], key=lambda x: x.name)[:10]
                files = sorted([e for e in entries if e.is_file()], key=lambda x: x.name)[:15]

                lines = [f"📂 `{runner.working_directory}`\n"]
                if dirs:
                    lines.append("**Dirs:** " + ", ".join([f"`{d.name}/`" for d in dirs]))
                if files:
                    lines.append("**Files:** " + ", ".join([f"`{f.name}`" for f in files]))
                if len(entries) > 25:
                    lines.append(f"\n... +{len(entries) - 25} more")

                await query.edit_message_text(
                    "\n".join(lines),
                    parse_mode="Markdown",
                    reply_markup=get_main_menu_keyboard()
                )
            except Exception as e:
                await query.edit_message_text(f"❌ Error: {e}")

        elif action == "pwd":
            runner = get_or_create_runner(user_id)
            if not runner:
                await query.edit_message_text("❌ Cannot create session. Max sessions limit reached.")
                return
            await query.edit_message_text(
                f"📍 **Current Directory**\n\n`{runner.working_directory}`",
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )

        elif action == "show_dirs":
            # Show directory browser
            runner = get_or_create_runner(user_id)
            if not runner:
                await query.edit_message_text("❌ Cannot create session. Max sessions limit reached.")
                return

            try:
                approved_dir = settings.approved_directory_path
                subdirs = []
                if approved_dir.exists():
                    subdirs = [d for d in approved_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    subdirs = sorted(subdirs, key=lambda x: x.stat().st_mtime, reverse=True)[:8]

                lines = [
                    f"📂 **Directory Browser**\n",
                    f"**Current:** `{runner.working_directory.name}/`\n",
                    f"**Available Folders:**"
                ]

                keyboard = []
                for d in subdirs:
                    is_current = "👉 " if str(d) == str(runner.working_directory) else ""
                    lines.append(f"{is_current}📁 `{d.name}/`")
                    if str(d) != str(runner.working_directory):
                        keyboard.append([InlineKeyboardButton(
                            f"📁 {d.name}",
                            callback_data=f"chdir:{d.name}"
                        )])

                keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="menu:show")])

                await query.edit_message_text(
                    "\n".join(lines),
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                await query.edit_message_text(f"❌ Error: {e}")

        elif action == "status":
            session = session_manager.get_active_session(user_id)
            runner = runner_manager.get_active_runner(session.session_id) if session else None
            provider = get_llm_provider()
            provider_name = provider.get_name() if provider else "Claude CLI (Pro)"

            lines = [
                "📊 **Status**\n",
                f"🔌 Provider: {provider_name}",
            ]

            if runner:
                lines.append(f"🤖 Runner: {runner.state.value}")
                lines.append(f"📂 Dir: `{runner.working_directory.name}/`")
            else:
                lines.append("🤖 Runner: Not started yet")

            if session:
                lines.append(f"\n💬 Session: `{session.session_id}`")
                lines.append(f"📝 Messages: {len(session.messages)}")
                lines.append(f"💰 Cost: ${session.total_cost:.4f}")

            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )

        elif action == "sessions":
            sessions = session_manager.get_user_sessions(user_id)
            if sessions:
                keyboard = [
                    [InlineKeyboardButton(
                        f"{'🟢' if s.state.value == 'idle' else '🔄'} {s.session_id[:8]} ({len(s.messages)} msgs)",
                        callback_data=f"session:{s.session_id}"
                    )]
                    for s in sessions[:5]
                ]
                keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="menu:show")])

                await query.edit_message_text(
                    "📋 **Your Sessions**\n\nSelect one to switch:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    "No sessions yet.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🆕 New Session", callback_data="menu:new")
                    ]])
                )

        elif action == "export":
            session = session_manager.get_active_session(user_id)
            if session:
                await session_manager.save_session_to_file(session.session_id)
                await query.answer("Session exported to file!", show_alert=True)
                await query.edit_message_text(
                    f"💾 **Exported**\n\nSession `{session.session_id}` saved.",
                    parse_mode="Markdown",
                    reply_markup=get_main_menu_keyboard()
                )
            else:
                await query.answer("No active session", show_alert=True)

        elif action == "stop_task":
            # Stop current running task
            session = session_manager.get_active_session(user_id)
            if session:
                await runner_manager.stop_runner(session.session_id, user_id)
                session_manager.update_session_state(session.session_id, SessionState.IDLE)
            await query.edit_message_text(
                "🛑 **Task Stopped**\n\n"
                "Your current task has been cancelled.\n"
                "You can start a new one anytime.",
                reply_markup=get_main_menu_keyboard()
            )

        elif action == "end":
            session = session_manager.get_active_session(user_id)
            if session:
                await runner_manager.stop_runner(session.session_id, user_id)
                await session_manager.save_session_to_file(session.session_id)

                # Extract and update user profile
                messages_data = [{"role": m.role, "content": m.content} for m in session.messages]
                await memory_manager.extract_and_update_user_profile(
                    messages_data, str(session.working_directory)
                )

                session_manager._active_session.pop(user_id, None)

                await query.edit_message_text(
                    f"✅ **Session Ended**\n\n"
                    f"Session: `{session.session_id}`\n"
                    f"💬 Messages: {len(session.messages)}\n"
                    f"💰 Cost: ${session.total_cost:.4f}",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🆕 New Session", callback_data="menu:new")
                    ]])
                )
            else:
                await query.answer("No active session", show_alert=True)

    # Handle show actions
    elif data.startswith("show:"):
        action = data.split(":")[1]
        await query.answer()

        if action == "actions":
            await query.edit_message_text(
                "⚡ **Quick Actions**\n\nSelect a coding task:",
                parse_mode="Markdown",
                reply_markup=get_quick_actions_keyboard()
            )

    # Handle quick action prompts
    elif data.startswith("quick:"):
        action = data.split(":")[1]
        if action in QUICK_PROMPTS:
            await query.answer(f"Running {action}...")
            # Trigger the message handler with the prompt
            prompt = QUICK_PROMPTS[action]
            # Send as a new message from user perspective
            await query.message.reply_text(f"🚀 **{action.title()}**\n\n_{prompt}_", parse_mode="Markdown")

            # Create a fake update to process
            session = session_manager.get_active_session(user_id)
            if not session:
                session = session_manager.create_session(
                    user_id=user_id,
                    working_directory=settings.approved_directory_path
                )

            session.add_message("user", prompt)
            session_manager.update_session_state(session.session_id, SessionState.PROCESSING)

            # Show typing
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING
            )

            try:
                provider = get_llm_provider()
                if provider is None:
                    response = await _handle_with_claude_cli(query.message, prompt, session, user_id, context)
                else:
                    response = await _handle_with_api_provider(query.message, prompt, session, provider, context)

                if response:
                    session.add_message("assistant", response)
                session_manager.update_session_state(session.session_id, SessionState.IDLE)
            except Exception as e:
                logger.exception("Error in quick action")
                await query.message.reply_text(f"❌ Error: {e}")

    # Handle session switch
    elif data.startswith("session:"):
        session_id = data.split(":")[1]
        await query.answer()

        if session_manager.set_active_session(user_id, session_id):
            session = session_manager.get_session(session_id)

            await query.edit_message_text(
                f"✅ **Switched to session**\n\n"
                f"Session: `{session_id}`\n"
                f"📂 Directory: `{session.working_directory}`",
                parse_mode="Markdown",
                reply_markup=get_quick_actions_keyboard()
            )
        else:
            await query.edit_message_text("❌ Failed to switch session")

    # Handle directory change from button
    elif data.startswith("chdir:"):
        dir_name = data.split(":", 1)[1]
        await query.answer()

        session = session_manager.get_active_session(user_id)
        runner = get_or_create_runner(user_id, session)

        if not runner:
            await query.edit_message_text("❌ Cannot create session. Max sessions limit reached.")
            return

        # Try to find directory
        target_path = None

        # Try as subdirectory of approved directory
        candidate = settings.approved_directory_path / dir_name
        if candidate.exists() and candidate.is_dir():
            target_path = candidate
        else:
            # Try as subdirectory of current directory
            candidate = runner.working_directory / dir_name
            if candidate.exists() and candidate.is_dir():
                target_path = candidate

        if target_path and runner.change_directory(target_path):
            if session:
                session.working_directory = runner.working_directory

            await query.edit_message_text(
                f"✅ **Directory Changed**\n\n"
                f"📂 Now in: `{runner.working_directory}`\n\n"
                f"Ready to start coding!",
                parse_mode="Markdown",
                reply_markup=get_quick_actions_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ **Cannot change to:** `{dir_name}`\n\n"
                f"Use `/dirs` to see available directories.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📂 Show Dirs", callback_data="menu:show_dirs")
                ]])
            )


# ============ Application Setup ============

async def post_init(application: Application) -> None:
    """Set up bot commands after initialization."""
    commands = [
        ("new", "🆕 Start new session"),
        ("continue", "▶️ Continue last session"),
        ("menu", "📋 Show quick menu"),
        ("actions", "⚡ Quick coding actions"),
        ("status", "📊 Show current status"),
        ("usage", "💰 Claude usage & link"),
        ("stats", "📈 Session statistics"),
        ("dirs", "📂 Browse & switch folders"),
        ("cd", "📁 Change directory"),
        ("ls", "📄 List files"),
        ("tree", "🌳 Show directory tree"),
        ("pwd", "📍 Show current path"),
        ("sessions", "📋 List all sessions"),
        ("clear", "🗑️ Clear session history"),
        ("export", "💾 Export session"),
        ("end", "🛑 End current session"),
        ("stop", "⏹️ Stop current task"),
        ("help", "❓ Show help"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands menu set up successfully")


def create_bot_application() -> Application:
    """Create and configure the Telegram bot application."""
    builder = Application.builder().token(settings.telegram_bot_token)

    # Add proxy if configured
    if settings.proxy_url:
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(proxy=settings.proxy_url)
        builder = builder.request(request)

    # Add post_init callback to set commands
    builder = builder.post_init(post_init)

    application = builder.build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("actions", actions_command))
    application.add_handler(CommandHandler("new", new_session_command))
    application.add_handler(CommandHandler("continue", continue_session_command))
    application.add_handler(CommandHandler("sessions", sessions_command))
    application.add_handler(CommandHandler("dirs", dirs_command))
    application.add_handler(CommandHandler("cd", cd_command))
    application.add_handler(CommandHandler("ls", ls_command))
    application.add_handler(CommandHandler("tree", tree_command))
    application.add_handler(CommandHandler("pwd", pwd_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("usage", usage_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("end", end_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("export", export_command))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Unknown command handler - forwards Claude slash commands (like /cost, /compact)
    # Must be after registered commands but before the general message handler
    application.add_handler(MessageHandler(filters.COMMAND, handle_message))

    # Message handler (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application
