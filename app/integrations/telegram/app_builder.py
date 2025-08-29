from functools import partial
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from app.core import settings as core_settings
from app.integrations.telegram.handlers import (
    start_command_handler,
    admin_command_handler,
    callback_query_handler,
    text_message_handler,
    document_upload_handler,
)


def build_application(bot_instance) -> Application:
    application = Application.builder().token(core_settings.TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", partial(start_command_handler, bot_instance)))
    application.add_handler(CommandHandler("admin", partial(admin_command_handler, bot_instance)))
    application.add_handler(CallbackQueryHandler(partial(callback_query_handler, bot_instance)))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, partial(text_message_handler, bot_instance))
    )
    application.add_handler(MessageHandler(filters.Document.ALL, partial(document_upload_handler, bot_instance)))

    # Set bot commands for quick access
    try:
        commands = [
            ("start", "Ouvrir le menu principal"),
            ("buy", "Acheter une formation"),
            ("sell", "Espace vendeur"),
            ("support", "Support & aide"),
        ]
        application.bot.set_my_commands([bot_instance.BotCommand(name, desc) if hasattr(bot_instance, 'BotCommand') else __import__('telegram').BotCommand(name, desc) for name, desc in commands])
    except Exception:
        pass

    return application

