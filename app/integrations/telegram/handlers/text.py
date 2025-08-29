from telegram.ext import ContextTypes


async def text_message_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    await bot_controller.handle_text_message(update, context)

