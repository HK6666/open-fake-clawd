"""Telegram bot command handlers."""

import html
import logging
import os
from pathlib import Path
from typing import Optional

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
from backend.claude.runner import runner_manager, StreamEvent
from backend.claude.session import session_manager, SessionState
from backend.memory.manager import memory_manager
from backend.db.models import db

logger = logging.getLogger(__name__)


# Maximum message length for Telegram
MAX_MESSAGE_LENGTH = 4096


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Truncate message if too long."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 100] + "\n\n... (truncated)"


async def send_long_message(update: Update, text: str, parse_mode: Optional[str] = None):
    """Send a message, splitting if necessary."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        await update.message.reply_text(text, parse_mode=parse_mode)
        return

    # Split into chunks
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH - 50:
            chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line

    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        prefix = f"[{i+1}/{len(chunks)}]\n" if len(chunks) > 1 else ""
        await update.message.reply_text(prefix + chunk, parse_mode=parse_mode)


# ============ Command Handlers ============

@require_auth
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}!\n\n"
        "I'm ccBot - your Claude Code assistant in Telegram.\n\n"
        "**Commands:**\n"
        "• `/new` - Start a new session\n"
        "• `/continue` - Continue last session\n"
        "• `/sessions` - List your sessions\n"
        "• `/cd <path>` - Change working directory\n"
        "• `/ls` - List current directory\n"
        "• `/pwd` - Show current directory\n"
        "• `/status` - Show current status\n"
        "• `/stop` - Stop current task\n"
        "• `/export` - Export session history\n"
        "• `/help` - Show this help\n\n"
        "Just send me a message to start coding!",
        parse_mode="Markdown"
    )


@require_auth
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start_command(update, context)


@require_auth
async def new_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - start a new session."""
    user_id = update.effective_user.id

    # Create new session
    session = session_manager.create_session(
        user_id=user_id,
        working_directory=settings.approved_directory
    )

    # Get runner and reset
    runner = runner_manager.get_runner(user_id)
    runner.session_id = None
    runner.working_directory = settings.approved_directory

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

    runner = runner_manager.get_runner(user_id)
    runner.session_id = session.claude_session_id
    runner.working_directory = session.working_directory

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
async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cd command - change working directory."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /cd <path>")
        return

    path_str = " ".join(context.args)
    path = Path(path_str).expanduser()

    runner = runner_manager.get_runner(user_id)

    # Handle relative paths
    if not path.is_absolute():
        path = runner.working_directory / path

    if runner.change_directory(path):
        session = session_manager.get_active_session(user_id)
        if session:
            session.working_directory = runner.working_directory

        await update.message.reply_text(
            f"📂 Changed to: `{runner.working_directory}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ Cannot change to: `{path}`\n"
            f"Path must exist and be within: `{settings.approved_directory}`",
            parse_mode="Markdown"
        )


@require_auth
async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ls command - list current directory."""
    user_id = update.effective_user.id
    runner = runner_manager.get_runner(user_id)

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
    runner = runner_manager.get_runner(user_id)

    await update.message.reply_text(
        f"📂 Current directory:\n`{runner.working_directory}`",
        parse_mode="Markdown"
    )


@require_auth
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show current status."""
    user_id = update.effective_user.id

    runner = runner_manager.get_runner(user_id)
    session = session_manager.get_active_session(user_id)

    lines = ["**Status:**\n"]
    lines.append(f"🤖 Runner: {runner.state.value}")
    lines.append(f"📂 Directory: `{runner.working_directory}`")

    if session:
        lines.append(f"\n**Session:** `{session.session_id}`")
        lines.append(f"💬 Messages: {len(session.messages)}")
        lines.append(f"💰 Cost: ${session.total_cost:.4f}")
        lines.append(f"📊 State: {session.state.value}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_auth
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command - stop current task."""
    user_id = update.effective_user.id

    await runner_manager.stop_runner(user_id)

    session = session_manager.get_active_session(user_id)
    if session:
        session_manager.update_session_state(session.session_id, SessionState.IDLE)

    await update.message.reply_text("🛑 Stopped current task.")


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


# ============ Message Handler ============

@require_auth
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages - send to Claude Code."""
    user_id = update.effective_user.id
    text = update.message.text

    if not text:
        return

    # Get or create session
    session = session_manager.get_active_session(user_id)
    if not session:
        session = session_manager.create_session(
            user_id=user_id,
            working_directory=settings.approved_directory
        )

    # Add user message to session
    session.add_message("user", text)
    session_manager.update_session_state(session.session_id, SessionState.PROCESSING)

    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    # Get runner
    runner = runner_manager.get_runner(user_id)
    runner.working_directory = session.working_directory

    # Determine if continuing session
    continue_session = runner.session_id is not None

    # Collect response
    response_parts = []
    current_message = None
    message_buffer = ""

    try:
        async for event in runner.run(text, continue_session=continue_session):
            if event.type == "text":
                message_buffer += event.content

                # Send updates periodically
                if len(message_buffer) > 500 or event.content.endswith("\n\n"):
                    if current_message:
                        try:
                            new_text = truncate_message(message_buffer)
                            await current_message.edit_text(new_text)
                        except Exception:
                            pass
                    else:
                        current_message = await update.message.reply_text(
                            truncate_message(message_buffer)
                        )

            elif event.type == "tool_use":
                # Notify about tool use
                tool_msg = f"🔧 Using: {event.content}"
                if current_message:
                    message_buffer += f"\n\n{tool_msg}"
                    try:
                        await current_message.edit_text(truncate_message(message_buffer))
                    except Exception:
                        pass
                else:
                    current_message = await update.message.reply_text(tool_msg)

            elif event.type == "result":
                # Update session with Claude's session ID
                if event.metadata.get("session_id"):
                    session.claude_session_id = event.metadata["session_id"]
                    runner.session_id = event.metadata["session_id"]

                # Record cost
                if event.metadata.get("cost"):
                    session_manager.add_cost(session.session_id, event.metadata["cost"])

                response_parts.append(event.content)

            elif event.type == "error":
                error_msg = f"❌ Error: {event.content}"
                if current_message:
                    message_buffer += f"\n\n{error_msg}"
                    await current_message.edit_text(truncate_message(message_buffer))
                else:
                    await update.message.reply_text(error_msg)

            elif event.type == "done":
                # Final update
                if message_buffer and current_message:
                    try:
                        await current_message.edit_text(truncate_message(message_buffer))
                    except Exception:
                        pass

        # Add assistant response to session
        full_response = message_buffer or "\n".join(response_parts)
        if full_response:
            session.add_message("assistant", full_response)

        session_manager.update_session_state(session.session_id, SessionState.IDLE)

    except Exception as e:
        logger.exception("Error processing message")
        session_manager.update_session_state(session.session_id, SessionState.ERROR)
        await update.message.reply_text(f"❌ Error: {e}")


# ============ Callback Handler ============

@require_auth
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data.startswith("session:"):
        session_id = data.split(":")[1]
        if session_manager.set_active_session(user_id, session_id):
            session = session_manager.get_session(session_id)
            runner = runner_manager.get_runner(user_id)
            runner.session_id = session.claude_session_id
            runner.working_directory = session.working_directory

            await query.edit_message_text(
                f"✅ Switched to session `{session_id}`\n"
                f"📂 Directory: `{session.working_directory}`",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Failed to switch session")


# ============ Application Setup ============

def create_bot_application() -> Application:
    """Create and configure the Telegram bot application."""
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_session_command))
    application.add_handler(CommandHandler("continue", continue_session_command))
    application.add_handler(CommandHandler("sessions", sessions_command))
    application.add_handler(CommandHandler("cd", cd_command))
    application.add_handler(CommandHandler("ls", ls_command))
    application.add_handler(CommandHandler("pwd", pwd_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("export", export_command))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Message handler (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application
