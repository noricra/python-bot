"""Message utilities for Telegram bot handlers"""

from app.core.utils import logger


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
