from telegram import InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.integrations.telegram.keyboards import main_menu_keyboard


async def start_command_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_controller.add_user(
        user.id,
        user.username,
        user.first_name,
        user.language_code or 'fr'
    )

    welcome_text = (
        """🏪 **TECHBOT MARKETPLACE**
*La première marketplace crypto pour formations*

🎯 **Découvrez des formations premium**
📚 **Vendez vos connaissances**  
💰 **Wallet crypto intégré**

Choisissez une option pour commencer :"""
    )

    keyboard = main_menu_keyboard()
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

