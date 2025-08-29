"""
Base handler for Telegram bot operations.
"""

from abc import ABC
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes

from app.core.utils import escape_markdown


class BaseHandler(ABC):
    """Base class for all Telegram handlers."""
    
    def __init__(self):
        self.user_states: Dict[int, Dict[str, Any]] = {}
    
    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """Get user state from memory cache."""
        return self.user_states.setdefault(user_id, {})
    
    def update_user_state(self, user_id: int, **kwargs) -> None:
        """Update user state in memory cache."""
        state = self.user_states.setdefault(user_id, {})
        state.update(kwargs)
    
    def clear_user_state(self, user_id: int) -> None:
        """Clear user state."""
        self.user_states.pop(user_id, None)
    
    def reset_user_state_preserve_login(self, user_id: int) -> None:
        """Reset user state but preserve login status."""
        state = self.user_states.get(user_id, {})
        seller_logged_in = state.get('seller_logged_in', False)
        self.user_states[user_id] = {'seller_logged_in': seller_logged_in}
    
    def is_seller_logged_in(self, user_id: int) -> bool:
        """Check if seller is logged in."""
        state = self.user_states.get(user_id, {})
        return state.get('seller_logged_in', False)
    
    def set_seller_logged_in(self, user_id: int, logged_in: bool) -> None:
        """Set seller login status."""
        self.update_user_state(user_id, seller_logged_in=logged_in)
    
    @staticmethod
    def escape_markdown_text(text: str) -> str:
        """Escape markdown special characters."""
        return escape_markdown(text)
    
    @staticmethod
    def get_user_display_name(update: Update) -> str:
        """Get user display name from update."""
        user = update.effective_user
        if user.first_name:
            return user.first_name
        if user.username:
            return user.username
        return f"User_{user.id}"
    
    @staticmethod
    async def safe_edit_message(update: Update, text: str, **kwargs) -> None:
        """Safely edit message with error handling."""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, **kwargs)
            else:
                await update.message.edit_text(text, **kwargs)
        except Exception as e:
            # Log error but don't crash
            print(f"Error editing message: {e}")
    
    @staticmethod
    async def safe_reply(update: Update, text: str, **kwargs) -> None:
        """Safely reply to message with error handling."""
        try:
            if update.callback_query:
                await update.callback_query.message.reply_text(text, **kwargs)
            else:
                await update.message.reply_text(text, **kwargs)
        except Exception as e:
            # Log error but don't crash
            print(f"Error replying to message: {e}")
    
    @staticmethod
    async def answer_callback_query(update: Update, text: str = None) -> None:
        """Answer callback query with optional text."""
        try:
            if update.callback_query:
                await update.callback_query.answer(text)
        except Exception as e:
            print(f"Error answering callback query: {e}")
    
    def format_price(self, amount: float) -> str:
        """Format price for display."""
        return f"{amount:.2f} EUR"
    
    def format_crypto_amount(self, amount: float, currency: str) -> str:
        """Format crypto amount for display."""
        if currency.upper() in ['BTC']:
            return f"{amount:.8f} {currency.upper()}"
        elif currency.upper() in ['ETH']:
            return f"{amount:.6f} {currency.upper()}"
        else:
            return f"{amount:.4f} {currency.upper()}"