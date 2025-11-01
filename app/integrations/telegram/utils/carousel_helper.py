"""
Carousel Helper - Module universel pour affichage carousel unifié
Élimine la duplication entre buy/sell/library handlers
"""
from telegram import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Callable, Optional
import os
import logging

logger = logging.getLogger(__name__)


class CarouselHelper:
    """Helper universel pour affichage carousel avec navigation ⬅️ ➡️"""

    @staticmethod
    async def show_carousel(
        query,
        bot,
        products: List[Dict],
        index: int,
        caption_builder: Callable[[Dict, str], str],
        keyboard_builder: Callable[[Dict, int, int, str], List[List[InlineKeyboardButton]]],
        lang: str = 'fr',
        parse_mode: str = 'HTML'
    ) -> None:
        """
        Affiche un carousel de produits avec navigation

        Args:
            query: CallbackQuery Telegram
            bot: Instance du bot
            products: Liste des produits à afficher
            index: Index du produit actuel
            caption_builder: Fonction qui génère le caption (product, lang) -> str
            keyboard_builder: Fonction qui génère les boutons (product, index, total, lang) -> keyboard
            lang: Langue ('fr' ou 'en')
            parse_mode: Mode de parsing ('HTML' ou 'Markdown')
        """
        try:
            # Validation
            if not products or index >= len(products):
                await query.edit_message_text(
                    "❌ No products found" if lang == 'en' else "❌ Aucun produit trouvé"
                )
                return

            product = products[index]

            # Build caption using provided builder
            caption = caption_builder(product, lang)

            # Build keyboard using provided builder
            keyboard = keyboard_builder(product, index, len(products), lang)
            keyboard_markup = InlineKeyboardMarkup(keyboard)

            # Get image path
            thumbnail_url = CarouselHelper._get_image_path(product)

            # Display carousel (edit or send new)
            await CarouselHelper._display_message(
                query, bot, thumbnail_url, caption, keyboard_markup, parse_mode
            )

        except Exception as e:
            logger.error(f"Error in show_carousel: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                await query.edit_message_text(
                    "❌ Error displaying product" if lang == 'en' else "❌ Erreur affichage produit"
                )
            except:
                pass

    @staticmethod
    def _get_image_path(product: Dict) -> Optional[str]:
        """
        Récupère le chemin de l'image du produit avec fallback sur placeholder

        Args:
            product: Dictionnaire produit

        Returns:
            Chemin vers l'image ou None
        """
        thumbnail_url = product.get('thumbnail_url')

        # Check if thumbnail exists
        if thumbnail_url and os.path.exists(thumbnail_url):
            return thumbnail_url

        # Fallback: try to get placeholder
        try:
            from app.core.image_utils import ImageUtils
            placeholder_path = ImageUtils.create_or_get_placeholder(
                product_title=product.get('title', 'Produit'),
                category=product.get('category', 'General'),
                product_id=product.get('product_id', 'unknown')
            )
            if placeholder_path and os.path.exists(placeholder_path):
                return placeholder_path
        except Exception as e:
            logger.warning(f"Could not generate placeholder: {e}")

        return None

    @staticmethod
    async def _display_message(
        query,
        bot,
        thumbnail_url: Optional[str],
        caption: str,
        keyboard_markup: InlineKeyboardMarkup,
        parse_mode: str
    ) -> None:
        """
        Affiche ou met à jour le message carousel

        Tente d'abord edit_message_media/edit_message_text,
        si échec envoie un nouveau message

        Args:
            query: CallbackQuery
            bot: Instance bot
            thumbnail_url: Chemin image ou None
            caption: Caption formaté
            keyboard_markup: Clavier inline
            parse_mode: Mode parsing
        """
        # Check if this is a callback query or command (MockQuery)
        is_callback = hasattr(query, 'edit_message_media') and hasattr(query, 'message')

        try:
            if is_callback:
                # Try to edit existing message (callback query)
                if thumbnail_url and os.path.exists(thumbnail_url):
                    # Has image - use edit_message_media
                    with open(thumbnail_url, 'rb') as photo_file:
                        await query.edit_message_media(
                            media=InputMediaPhoto(
                                media=photo_file,
                                caption=caption,
                                parse_mode=parse_mode
                            ),
                            reply_markup=keyboard_markup
                        )
                else:
                    # No image - text only
                    await query.edit_message_text(
                        text=caption,
                        reply_markup=keyboard_markup,
                        parse_mode=parse_mode
                    )
            else:
                # Command (MockQuery) - send new message
                chat_id = query.effective_chat.id if hasattr(query, 'effective_chat') else query.message.chat_id

                if thumbnail_url and os.path.exists(thumbnail_url):
                    with open(thumbnail_url, 'rb') as photo_file:
                        await query.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo_file,
                            caption=caption,
                            reply_markup=keyboard_markup,
                            parse_mode=parse_mode
                        )
                else:
                    await query.bot.send_message(
                        chat_id=chat_id,
                        text=caption,
                        reply_markup=keyboard_markup,
                        parse_mode=parse_mode
                    )

        except Exception as e:
            # Edit failed (message too old, etc) - send new message
            logger.warning(f"Failed to edit/send message, trying fallback: {e}")

            try:
                if hasattr(query, 'message') and query.message:
                    await query.message.delete()
            except:
                pass  # Ignore if can't delete

            # Fallback: send new message
            chat_id = query.effective_chat.id if hasattr(query, 'effective_chat') else query.message.chat_id

            if thumbnail_url and os.path.exists(thumbnail_url):
                with open(thumbnail_url, 'rb') as photo_file:
                    await query.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_file,
                        caption=caption,
                        reply_markup=keyboard_markup,
                        parse_mode=parse_mode
                    )
            else:
                await query.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    reply_markup=keyboard_markup,
                    parse_mode=parse_mode
                )

    @staticmethod
    def build_navigation_row(
        index: int,
        total: int,
        callback_prefix: str,
        show_empty_buttons: bool = False
    ) -> List[InlineKeyboardButton]:
        """
        Construit la ligne de navigation ⬅️ X/Y ➡️

        Args:
            index: Index actuel
            total: Total d'items
            callback_prefix: Préfixe pour callback_data (ex: 'carousel_', 'seller_carousel_')
            show_empty_buttons: Si True, affiche des boutons vides au lieu de rien

        Returns:
            Liste de boutons pour navigation
        """
        nav_row = []

        # Left arrow
        if index > 0:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'{callback_prefix}{index-1}'))
        elif show_empty_buttons:
            nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))

        # Counter (always shown)
        nav_row.append(InlineKeyboardButton(
            f"{index+1}/{total}",
            callback_data='noop'
        ))

        # Right arrow
        if index < total - 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f'{callback_prefix}{index+1}'))
        elif show_empty_buttons:
            nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))

        return nav_row
