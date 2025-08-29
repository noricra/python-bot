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

    return application

