from telegram.ext import ContextTypes


async def admin_command_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    await bot_controller.admin_command(update, context)

