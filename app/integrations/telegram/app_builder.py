from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, AIORateLimiter
from telegram.request import HTTPXRequest
from telegram import BotCommand
import logging

from app.core import settings as core_settings


def build_application(bot_instance) -> Application:
    # Configure HTTP client with pooling & timeouts
    request = HTTPXRequest(
        connection_pool_size=getattr(core_settings, "TELEGRAM_POOL_SIZE", 20),
        proxy_url=getattr(core_settings, "TELEGRAM_PROXY_URL", None),
        connect_timeout=getattr(core_settings, "TELEGRAM_CONNECT_TIMEOUT", 5.0),
        read_timeout=getattr(core_settings, "TELEGRAM_READ_TIMEOUT", 30.0),
        write_timeout=getattr(core_settings, "TELEGRAM_WRITE_TIMEOUT", 30.0),
        pool_timeout=getattr(core_settings, "TELEGRAM_POOL_TIMEOUT", 5.0),
    )

    builder = Application.builder().token(core_settings.TELEGRAM_TOKEN).request(request)

    # Optional base URL (useful for MTProto proxies or test environments)
    if getattr(core_settings, "TELEGRAM_BASE_URL", None):
        builder = builder.base_url(core_settings.TELEGRAM_BASE_URL)

    # Enable concurrent updates and rate limiting for better throughput
    if getattr(core_settings, "TELEGRAM_CONCURRENT_UPDATES", True):
        builder = builder.concurrent_updates(True)
    if getattr(core_settings, "TELEGRAM_RATE_LIMITER", True):
        builder = builder.rate_limiter(AIORateLimiter())

    application = builder.build()

    application.add_handler(CommandHandler("start", bot_instance.start_command))
    application.add_handler(CommandHandler("admin", bot_instance.admin_command))
    # Help/support commands
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    application.add_handler(CommandHandler("support", bot_instance.support_command))
    application.add_handler(CallbackQueryHandler(bot_instance.button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_text_message)
    )
    application.add_handler(MessageHandler(filters.Document.ALL, bot_instance.handle_document_upload))

    # Set bot commands asynchronously after initialization to avoid unawaited coroutine
    async def _post_init(app: Application) -> None:
        try:
            commands = [
                BotCommand("start", "Ouvrir le menu principal"),
                BotCommand("buy", "Acheter une formation"),
                BotCommand("sell", "Espace vendeur"),
                BotCommand("support", "Support & aide"),
            ]
            await app.bot.set_my_commands(commands)
        except Exception as exc:
            logging.getLogger(__name__).warning("Impossible de définir les commandes du bot: %s", exc)

    application.post_init = _post_init

    return application

