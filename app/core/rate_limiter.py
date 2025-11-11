"""
Rate Limiter - Protect against spam and DDoS
Limits requests per user per time window
"""
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter with sliding window.

    Features:
    - Per-user rate limiting
    - Configurable window and max requests
    - Automatic cleanup of old entries
    - Thread-safe (for single process)
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # Store: {user_id: [(timestamp1, timestamp2, ...)]}
        self._requests: Dict[int, list] = defaultdict(list)

        # Last cleanup timestamp
        self._last_cleanup = time.time()

        # Cleanup interval (5 minutes)
        self._cleanup_interval = 300

        logger.info(f"🛡️ Rate limiter initialized: {max_requests} requests / {window_seconds}s per user")

    def is_allowed(self, user_id: int) -> Tuple[bool, int]:
        """
        Check if user is allowed to make a request.

        Args:
            user_id: Telegram user ID

        Returns:
            tuple: (is_allowed: bool, remaining_requests: int)
        """
        current_time = time.time()

        # Periodic cleanup
        self._maybe_cleanup()

        # Get user's request timestamps
        timestamps = self._requests[user_id]

        # Remove timestamps outside window
        cutoff_time = current_time - self.window_seconds
        timestamps = [ts for ts in timestamps if ts > cutoff_time]

        # Update cleaned timestamps
        self._requests[user_id] = timestamps

        # Check if limit exceeded
        if len(timestamps) >= self.max_requests:
            remaining = 0
            is_allowed = False
            logger.warning(f"⚠️ Rate limit exceeded for user {user_id}: {len(timestamps)}/{self.max_requests} requests")
        else:
            # Allow request and record timestamp
            timestamps.append(current_time)
            self._requests[user_id] = timestamps
            remaining = self.max_requests - len(timestamps)
            is_allowed = True

        return is_allowed, remaining

    def get_wait_time(self, user_id: int) -> int:
        """
        Get time in seconds user must wait before next request.

        Args:
            user_id: Telegram user ID

        Returns:
            int: Seconds to wait (0 if allowed now)
        """
        current_time = time.time()
        timestamps = self._requests.get(user_id, [])

        if not timestamps or len(timestamps) < self.max_requests:
            return 0

        # Time until oldest request expires
        cutoff_time = current_time - self.window_seconds
        oldest_timestamp = min(timestamps)

        if oldest_timestamp <= cutoff_time:
            return 0

        wait_time = int(oldest_timestamp - cutoff_time) + 1
        return wait_time

    def reset_user(self, user_id: int):
        """
        Reset rate limit for specific user.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self._requests:
            del self._requests[user_id]
            logger.info(f"🔄 Rate limit reset for user {user_id}")

    def get_user_stats(self, user_id: int) -> Dict:
        """
        Get statistics for specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            dict: User rate limit statistics
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        timestamps = self._requests.get(user_id, [])
        active_timestamps = [ts for ts in timestamps if ts > cutoff_time]

        return {
            'user_id': user_id,
            'requests_in_window': len(active_timestamps),
            'max_requests': self.max_requests,
            'remaining_requests': max(0, self.max_requests - len(active_timestamps)),
            'window_seconds': self.window_seconds,
            'wait_time': self.get_wait_time(user_id)
        }

    def get_global_stats(self) -> Dict:
        """
        Get global rate limiter statistics.

        Returns:
            dict: Global statistics
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        total_users = len(self._requests)
        active_users = 0
        total_requests = 0

        for user_id, timestamps in self._requests.items():
            active_timestamps = [ts for ts in timestamps if ts > cutoff_time]
            if active_timestamps:
                active_users += 1
                total_requests += len(active_timestamps)

        return {
            'total_users_tracked': total_users,
            'active_users_in_window': active_users,
            'total_requests_in_window': total_requests,
            'max_requests_per_user': self.max_requests,
            'window_seconds': self.window_seconds
        }

    def _maybe_cleanup(self):
        """
        Periodically clean up old entries to prevent memory leak.
        """
        current_time = time.time()

        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        logger.info("🧹 Running rate limiter cleanup...")

        cutoff_time = current_time - self.window_seconds
        users_to_remove = []

        for user_id, timestamps in self._requests.items():
            # Remove old timestamps
            active_timestamps = [ts for ts in timestamps if ts > cutoff_time]

            if active_timestamps:
                self._requests[user_id] = active_timestamps
            else:
                # No active timestamps, mark for removal
                users_to_remove.append(user_id)

        # Remove users with no active timestamps
        for user_id in users_to_remove:
            del self._requests[user_id]

        self._last_cleanup = current_time

        if users_to_remove:
            logger.info(f"✅ Cleaned up {len(users_to_remove)} inactive users from rate limiter")


# Global rate limiter instance
_rate_limiter: RateLimiter = None


def init_rate_limiter(max_requests: int = 10, window_seconds: int = 60):
    """
    Initialize global rate limiter.

    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(max_requests, window_seconds)


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance.

    Returns:
        RateLimiter: Global rate limiter

    Raises:
        RuntimeError: If rate limiter not initialized
    """
    global _rate_limiter

    if _rate_limiter is None:
        raise RuntimeError("Rate limiter not initialized. Call init_rate_limiter() first.")

    return _rate_limiter


# Decorator for rate-limited functions
def rate_limit(func):
    """
    Decorator to add rate limiting to a function.

    Usage:
        @rate_limit
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # This function is now rate-limited
            ...

    The decorator will:
    - Check rate limit before calling function
    - Send rate limit message if exceeded
    - Log rate limit violations
    """
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        rate_limiter = get_rate_limiter()

        is_allowed, remaining = rate_limiter.is_allowed(user_id)

        if not is_allowed:
            wait_time = rate_limiter.get_wait_time(user_id)

            # Send rate limit message
            rate_limit_message = f"""⚠️ **Trop de requêtes**

Vous avez atteint la limite de {rate_limiter.max_requests} requêtes par minute.

⏳ Veuillez patienter {wait_time} secondes avant de réessayer."""

            await update.message.reply_text(
                rate_limit_message,
                parse_mode='Markdown'
            )

            logger.warning(
                f"⚠️ Rate limit exceeded - User: {user_id}, "
                f"Function: {func.__name__}, Wait time: {wait_time}s"
            )

            return  # Don't call the function

        # Rate limit OK, call function
        return await func(update, context, *args, **kwargs)

    return wrapper
