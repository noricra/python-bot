"""Message utilities for Telegram bot handlers"""

from app.core.utils import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def safe_transition_to_text(query, text: str, keyboard=None, parse_mode='Markdown'):
    """
    Gère intelligemment la transition d'un message (photo ou texte) vers un message texte

    Problème résolu:
    - Les carousels ont des photos → edit_message_text() échoue
    - Solution: Détecter photo et supprimer/renvoyer au lieu d'éditer

    Args:
        query: Telegram CallbackQuery object
        text: Text to display
        keyboard: Optional InlineKeyboardMarkup
        parse_mode: 'Markdown' or 'HTML' (default: 'Markdown')
    """
    try:
        # Si le message original a une photo, on ne peut pas edit_message_text
        if query.message.photo:
            # Supprimer l'ancien message avec photo
            try:
                await query.message.delete()
            except:
                pass

            # Envoyer nouveau message texte
            await query.message.get_bot().send_message(
                chat_id=query.message.chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
        else:
            # Message texte normal, on peut éditer
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
    except Exception as e:
        logger.error(f"Error in safe_transition_to_text: {e}")
        # Fallback ultime : nouveau message
        try:
            await query.message.delete()
        except:
            pass
        await query.message.get_bot().send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode
        )


def create_product_success_message(product_id: str, title: str, price: float, lang: str = 'fr'):
    """
    Génère le message de succès et le keyboard pour la création d'un produit

    Utilisé par:
    - upload-complete (ipn_server.py)
    - import-complete (ipn_server.py)
    - sell_handlers.py (upload classique)

    Args:
        product_id: ID du produit créé
        title: Titre du produit
        price: Prix en USD
        lang: Langue ('fr' ou 'en')

    Returns:
        tuple: (message, keyboard)
    """
    message = f"✅ **Produit créé avec succès!**\n\n**ID:** {product_id}\n**Titre:** {title}\n**Prix:** ${price:.2f}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏪 Dashboard" if lang == 'en' else "🏪 Dashboard", callback_data='seller_dashboard'),
        InlineKeyboardButton("📦 Mes produits" if lang == 'fr' else "📦 My Products", callback_data='my_products')
    ]])

    return message, keyboard
