from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from app.core import settings as core_settings


def build_application(bot_instance) -> Application:
    application = Application.builder().token(core_settings.TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", bot_instance.start_command))
    application.add_handler(CommandHandler("admin", bot_instance.admin_command))
    application.add_handler(CallbackQueryHandler(bot_instance.button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_text_message)
    )
    application.add_handler(MessageHandler(filters.Document.ALL, bot_instance.handle_document_upload))

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

