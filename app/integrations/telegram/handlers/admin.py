from telegram.ext import ContextTypes
from app.integrations.telegram.flows import admin as admin_flows


async def admin_command_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    await admin_flows.admin_command(bot_controller, update, context)

