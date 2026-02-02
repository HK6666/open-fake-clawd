"""Telegram bot middleware for authentication and rate limiting."""

import logging
import time
from collections import defaultdict
from datetime import datetime
from functools import wraps
from typing import Callable, Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from backend.config import settings
from backend.db.models import db

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[int, List[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """Check if a request is allowed for the given user."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self._requests[user_id] = [
            t for t in self._requests[user_id] if t > window_start
        ]

        # Check limit
        if len(self._requests[user_id]) >= self.max_requests:
            return False

        # Record this request
        self._requests[user_id].append(now)
        return True

    def get_retry_after(self, user_id: int) -> Optional[float]:
        """Get seconds until next request is allowed."""
        if not self._requests[user_id]:
            return None

        oldest = min(self._requests[user_id])
        retry_after = oldest + self.window_seconds - time.time()
        return max(0, retry_after)


# Global rate limiter
rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)


def is_user_allowed(user_id: int) -> bool:
    """Check if a user is in the allowed list."""
    # If no users configured, allow all (for testing)
    allowed = settings.allowed_users_list
    if not allowed:
        return True
    return user_id in allowed


class ActivityTracker:
    """Track user activity for analytics and auto-cleanup."""

    def __init__(self):
        self._last_activity: Dict[int, datetime] = {}
        self._command_count: Dict[int, int] = defaultdict(int)
        self._total_commands: int = 0

    def record_activity(self, user_id: int, command: str = ""):
        """Record user activity."""
        self._last_activity[user_id] = datetime.now()
        if command:
            self._command_count[user_id] += 1
            self._total_commands += 1

    def get_last_activity(self, user_id: int) -> Optional[datetime]:
        """Get last activity time for user."""
        return self._last_activity.get(user_id)

    def get_inactive_users(self, minutes: int = 60) -> List[int]:
        """Get users inactive for specified minutes."""
        now = datetime.now()
        inactive = []
        for user_id, last_time in self._last_activity.items():
            if (now - last_time).total_seconds() > minutes * 60:
                inactive.append(user_id)
        return inactive

    def get_stats(self) -> Dict:
        """Get activity statistics."""
        return {
            "total_users": len(self._last_activity),
            "total_commands": self._total_commands,
            "active_users": len([u for u in self._last_activity.keys()
                                if (datetime.now() - self._last_activity[u]).total_seconds() < 3600])
        }


# Global activity tracker
activity_tracker = ActivityTracker()


def require_auth(func: Callable) -> Callable:
    """Decorator to require user authentication with activity tracking."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        # Check if user is allowed
        if not is_user_allowed(user_id):
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            # Try to get message from update
            message = update.message or update.callback_query.message if update.callback_query else None
            if message:
                await message.reply_text(
                    "⛔ You are not authorized to use this bot.\n"
                    f"Your user ID: `{user_id}`",
                    parse_mode="Markdown"
                )
            return

        # Check rate limit
        if not rate_limiter.is_allowed(user_id):
            retry_after = rate_limiter.get_retry_after(user_id)
            logger.info(f"Rate limit exceeded for user {user_id}")
            message = update.message or update.callback_query.message if update.callback_query else None
            if message:
                await message.reply_text(
                    f"⏳ Rate limit exceeded.\n"
                    f"Please try again in {retry_after:.0f} seconds."
                )
            return

        # Record activity
        command_name = func.__name__.replace("_command", "").replace("_", " ")
        activity_tracker.record_activity(user_id, command_name)
        logger.info(f"User {user_id} ({user.username or user.first_name}) executed: {command_name}")
        
        # Record daily request count
        try:
            await db.increment_daily_request_count(user_id)
        except Exception as e:
            logger.error(f"Failed to record daily request count: {e}")

        return await func(update, context, *args, **kwargs)

    return wrapper


def admin_only(func: Callable) -> Callable:
    """Decorator to restrict to first user in allowed list (admin)."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        # First user in allowed list is admin
        allowed = settings.allowed_users_list
        if allowed and user.id != allowed[0]:
            await update.message.reply_text("⛔ This command is admin-only.")
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
