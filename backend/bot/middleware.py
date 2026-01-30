"""Telegram bot middleware for authentication and rate limiting."""

import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from backend.config import settings


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
    if not settings.allowed_users:
        return True
    return user_id in settings.allowed_users


def require_auth(func: Callable) -> Callable:
    """Decorator to require user authentication."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        # Check if user is allowed
        if not is_user_allowed(user_id):
            await update.message.reply_text(
                "⛔ You are not authorized to use this bot.\n"
                f"Your user ID: `{user_id}`",
                parse_mode="Markdown"
            )
            return

        # Check rate limit
        if not rate_limiter.is_allowed(user_id):
            retry_after = rate_limiter.get_retry_after(user_id)
            await update.message.reply_text(
                f"⏳ Rate limit exceeded. Please try again in {retry_after:.0f} seconds."
            )
            return

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
        if settings.allowed_users and user.id != settings.allowed_users[0]:
            await update.message.reply_text("⛔ This command is admin-only.")
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
