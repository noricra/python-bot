from telegram.ext import ContextTypes


async def callback_query_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    await bot_controller.button_handler(update, context)

