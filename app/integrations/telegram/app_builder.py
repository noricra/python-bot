from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import BotCommand

from app.core import settings as core_settings
from app.core.i18n import t as i18n


def build_application(bot_instance) -> Application:
    application = Application.builder().token(core_settings.TELEGRAM_TOKEN).build()

    # Use handlers instead of direct bot methods
    application.add_handler(CommandHandler("start", lambda update, context: bot_instance.core_handlers.start_command(bot_instance, update, context)))
    # Simple admin command handler
    async def admin_command_wrapper(update, context):
        # Check if user is admin (simplified check using ADMIN_USER_ID from settings)
        if update.effective_user.id == core_settings.ADMIN_USER_ID:
            # Create a mock query object for admin menu
            class MockQuery:
                def __init__(self, user, bot):
                    self.from_user = user
                    self._bot = bot
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

            mock_query = MockQuery(update.effective_user, bot_instance)
            # Get user language and call admin_menu
            lang = bot_instance.get_user_language(update.effective_user.id)
            await bot_instance.admin_handlers.admin_menu(bot_instance, mock_query, lang)
        else:
            await update.message.reply_text(i18n('fr', 'bot_access_denied'))

    application.add_handler(CommandHandler("admin", admin_command_wrapper))
    # Help/support commands
    application.add_handler(CommandHandler("help", lambda update, context: bot_instance.core_handlers.help_command(bot_instance, update, context)))
    application.add_handler(CommandHandler("support", lambda update, context: bot_instance.support_handlers.support_command(bot_instance, update, context)))
    # Use callback router for button handling
    async def callback_handler_wrapper(update, context):
        query = update.callback_query
        print(f"DEBUG CALLBACK: {query.data}")  # Debug immédiat
        await query.answer()
        # Route through the centralized callback router
        success = await bot_instance.callback_router.route(query)
        if not success:
            # Fallback error message
            from app.core.i18n import t as i18n
            lang = bot_instance.get_user_language(query.from_user.id)
            await query.edit_message_text(i18n(lang, 'err_temp'))

    application.add_handler(CallbackQueryHandler(callback_handler_wrapper))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_text_message)
    )
    # Document handler for file uploads
    application.add_handler(MessageHandler(filters.Document.ALL, bot_instance.handle_document_upload))

    # Photo handler for cover image uploads
    application.add_handler(MessageHandler(filters.PHOTO, bot_instance.handle_photo_upload))

    # Set bot commands for quick access - will be set when bot starts
    async def post_init(app):
        try:
            commands = [
                ("start", i18n('fr', 'bot_commands_start')),
                ("help", i18n('fr', 'bot_commands_help')),
                ("support", i18n('fr', 'bot_commands_support')),
            ]
            await app.bot.set_my_commands([BotCommand(name, desc) for name, desc in commands])
        except Exception:
            pass

    application.post_init = post_init

    return application

