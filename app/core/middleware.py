"""
Telegram Bot Middleware
Handles rate limiting, logging, and error handling for all requests
"""
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from app.core.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


async def rate_limit_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Rate limiting middleware for Telegram bot.

    Args:
        update: Telegram update
        context: Bot context

    Returns:
        bool: True if request allowed, False if rate limited
    """
    # Skip rate limiting for callback queries (already rate limited by message handler)
    if update.callback_query:
        return True

    # Get user ID
    user = update.effective_user
    if not user:
        return True  # Allow if no user (shouldn't happen)

    user_id = user.id

    # Check rate limit
    rate_limiter = get_rate_limiter()
    is_allowed, remaining = rate_limiter.is_allowed(user_id)

    if not is_allowed:
        wait_time = rate_limiter.get_wait_time(user_id)

        # Send rate limit message
        rate_limit_message = f"""⚠️ **Trop de requêtes**

Vous avez atteint la limite de {rate_limiter.max_requests} requêtes par minute.

⏳ Veuillez patienter **{wait_time} secondes** avant de réessayer.

💡 Astuce : Prenez le temps d'explorer les fonctionnalités du bot sans précipitation."""

        if update.message:
            await update.message.reply_text(
                rate_limit_message,
                parse_mode='Markdown'
            )
        elif update.callback_query:
            await update.callback_query.answer(
                f"⚠️ Trop de requêtes. Attendez {wait_time}s.",
                show_alert=True
            )

        logger.warning(
            f"⚠️ Rate limit exceeded - User: {user_id} (@{user.username}), "
            f"Wait time: {wait_time}s, Remaining: {remaining}"
        )

        return False  # Block request

    # Log request (only if rate limit OK)
    if update.message and update.message.text:
        logger.info(
            f"📨 Message - User: {user_id} (@{user.username}), "
            f"Text: {update.message.text[:50]}, Remaining: {remaining}"
        )

    return True  # Allow request


def with_rate_limit(handler_func):
    """
    Decorator to add rate limiting to a handler function.

    Usage:
        @with_rate_limit
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Handler code
            ...

    Note: This is applied automatically to all message handlers via middleware.
    Only use this decorator if you need custom rate limiting on specific handlers.
    """
    @wraps(handler_func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Check rate limit
        is_allowed = await rate_limit_middleware(update, context)

        if not is_allowed:
            return  # Request blocked by rate limiter

        # Rate limit OK, call handler
        return await handler_func(update, context)

    return wrapper


async def error_handler_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception):
    """
    Global error handler middleware.

    Args:
        update: Telegram update
        context: Bot context
        error: Exception that occurred
    """
    logger.error(f"❌ Error in handler: {error}", exc_info=error)

    # Try to send error message to user
    try:
        if update and update.effective_user:
            error_message = """❌ **Une erreur s'est produite**

Nous avons rencontré un problème technique.

🔄 Veuillez réessayer dans quelques instants.
❓ Si le problème persiste, contactez le support."""

            if update.message:
                await update.message.reply_text(
                    error_message,
                    parse_mode='Markdown'
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "❌ Erreur technique. Réessayez.",
                    show_alert=True
                )

    except Exception as e:
        logger.error(f"❌ Failed to send error message to user: {e}")


def logging_middleware(handler_func):
    """
    Decorator to add logging to a handler function.

    Logs:
    - Handler execution time
    - User info
    - Success/failure

    Usage:
        @logging_middleware
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Handler code
            ...
    """
    import time

    @wraps(handler_func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        start_time = time.time()

        user = update.effective_user
        handler_name = handler_func.__name__

        try:
            # Call handler
            result = await handler_func(update, context)

            # Log success
            elapsed = time.time() - start_time
            logger.info(
                f"✅ Handler '{handler_name}' completed successfully - "
                f"User: {user.id if user else 'N/A'}, "
                f"Time: {elapsed:.3f}s"
            )

            return result

        except Exception as e:
            # Log failure
            elapsed = time.time() - start_time
            logger.error(
                f"❌ Handler '{handler_name}' failed - "
                f"User: {user.id if user else 'N/A'}, "
                f"Time: {elapsed:.3f}s, "
                f"Error: {e}"
            )
            raise

    return wrapper
