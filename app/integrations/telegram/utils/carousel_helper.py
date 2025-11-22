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

            # Get image (file_id or path) with Telegram cache
            image_source, is_file_id = CarouselHelper._get_image_path(product)

            # Display carousel with cache support
            await CarouselHelper._display_message(
                query, bot, product, image_source, is_file_id, caption, keyboard_markup, parse_mode
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
    def _get_image_path(product: Dict):
        """
        Récupère l'image du produit avec cache Telegram file_id (Railway-proof)

        Priority order (fastest to slowest):
        1. Telegram file_id (instant, free, survives restarts)
        2. Local cache (fast)
        3. Download from B2 (first time)
        4. Placeholder (fallback)

        Args:
            product: Dictionnaire produit

        Returns:
            tuple: (image_source, is_file_id)
                - image_source: file_id (str) or local path (str)
                - is_file_id: True if file_id, False if path
        """
        product_id = product.get('product_id')
        seller_id = product.get('seller_user_id')
        thumbnail_url = product.get('thumbnail_url')

        # 1. PRIORITY: Check Telegram file_id cache
        if product_id:
            try:
                from app.services.telegram_cache_service import get_telegram_cache_service
                telegram_cache = get_telegram_cache_service()
                file_id = telegram_cache.get_product_image_file_id(product_id, 'thumb')

                if file_id:
                    logger.info(f"⚡ Using cached file_id: {product_id}")
                    return (file_id, True)
            except Exception as e:
                logger.warning(f"⚠️ Could not check file_id cache: {e}")

        # 2. Check if thumbnail_url is B2 URL
        if thumbnail_url and thumbnail_url.startswith('https://'):
            logger.info(f"🌐 Thumbnail is B2 URL: {product_id}")
            # Try to download from B2 to local cache
            if product_id and seller_id:
                try:
                    from app.services.image_sync_service import ImageSyncService
                    image_sync = ImageSyncService()
                    local_path = image_sync.get_image_path_with_fallback(
                        product_id=product_id,
                        seller_id=seller_id,
                        image_type='thumb'
                    )
                    if local_path and os.path.exists(local_path):
                        logger.info(f"📥 Downloaded from B2: {product_id}")
                        return (local_path, False)
                except Exception as e:
                    logger.warning(f"⚠️ B2 download failed: {e}")

        # 3. Check if thumbnail exists locally
        if thumbnail_url and os.path.exists(thumbnail_url):
            return (thumbnail_url, False)

        # 4. Try to download from B2 if missing
        if product_id and seller_id:
            try:
                from app.services.image_sync_service import ImageSyncService
                logger.info(f"🔄 Image missing, downloading from B2: {product_id}")
                image_sync = ImageSyncService()
                b2_path = image_sync.get_image_path_with_fallback(
                    product_id=product_id,
                    seller_id=seller_id,
                    image_type='thumb'
                )
                if b2_path and os.path.exists(b2_path):
                    logger.info(f"✅ Downloaded from B2: {product_id}")
                    return (b2_path, False)
            except Exception as e:
                logger.warning(f"⚠️ Could not download from B2: {e}")

        # 5. FALLBACK: generate placeholder
        try:
            from app.core.image_utils import ImageUtils
            placeholder_path = ImageUtils.create_or_get_placeholder(
                product_title=product.get('title', 'Produit'),
                category=product.get('category', 'General'),
                product_id=product_id or 'unknown'
            )
            if placeholder_path and os.path.exists(placeholder_path):
                return (placeholder_path, False)
        except Exception as e:
            logger.warning(f"Could not generate placeholder: {e}")

        return (None, False)

    @staticmethod
    async def _display_message(
        query,
        bot,
        product: Dict,
        image_source: Optional[str],
        is_file_id: bool,
        caption: str,
        keyboard_markup: InlineKeyboardMarkup,
        parse_mode: str
    ) -> None:
        """
        Affiche ou met à jour le message carousel avec cache Telegram file_id

        Args:
            query: CallbackQuery
            bot: Instance bot
            product: Product dict (pour sauvegarder file_id)
            image_source: file_id Telegram ou chemin local
            is_file_id: True si image_source est un file_id
            caption: Caption formaté
            keyboard_markup: Clavier inline
            parse_mode: Mode parsing
        """
        product_id = product.get('product_id')

        # Check if this is a callback query or command (MockQuery)
        is_callback = hasattr(query, 'edit_message_media') and hasattr(query, 'message')

        try:
            sent_message = None

            if is_callback:
                # Try to edit existing message (callback query)
                if image_source:
                    if is_file_id:
                        # Use cached file_id (instant)
                        logger.info(f"⚡ Sending with cached file_id: {product_id}")
                        sent_message = await query.edit_message_media(
                            media=InputMediaPhoto(
                                media=image_source,
                                caption=caption,
                                parse_mode=parse_mode
                            ),
                            reply_markup=keyboard_markup
                        )
                    elif os.path.exists(image_source):
                        # Send from local file
                        with open(image_source, 'rb') as photo_file:
                            sent_message = await query.edit_message_media(
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

                if image_source:
                    if is_file_id:
                        # Use cached file_id
                        sent_message = await query.bot.send_photo(
                            chat_id=chat_id,
                            photo=image_source,
                            caption=caption,
                            reply_markup=keyboard_markup,
                            parse_mode=parse_mode
                        )
                    elif os.path.exists(image_source):
                        # Send from local file
                        with open(image_source, 'rb') as photo_file:
                            sent_message = await query.bot.send_photo(
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

            # Save file_id if sent from local file (not already cached)
            if sent_message and not is_file_id and product_id:
                try:
                    from app.services.telegram_cache_service import get_telegram_cache_service
                    if hasattr(sent_message, 'photo') and sent_message.photo:
                        file_id = sent_message.photo[-1].file_id
                        telegram_cache = get_telegram_cache_service()
                        telegram_cache.save_telegram_file_id(product_id, file_id, 'thumb')
                        logger.info(f"💾 Cached new file_id: {product_id}")
                except Exception as cache_error:
                    logger.warning(f"⚠️ Failed to cache file_id: {cache_error}")

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

            if image_source:
                if is_file_id:
                    await query.bot.send_photo(
                        chat_id=chat_id,
                        photo=image_source,
                        caption=caption,
                        reply_markup=keyboard_markup,
                        parse_mode=parse_mode
                    )
                elif os.path.exists(image_source):
                    with open(image_source, 'rb') as photo_file:
                        sent_message = await query.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo_file,
                            caption=caption,
                            reply_markup=keyboard_markup,
                            parse_mode=parse_mode
                        )
                        # Save file_id from fallback send
                        if sent_message and product_id:
                            try:
                                from app.services.telegram_cache_service import get_telegram_cache_service
                                if hasattr(sent_message, 'photo') and sent_message.photo:
                                    file_id = sent_message.photo[-1].file_id
                                    telegram_cache = get_telegram_cache_service()
                                    telegram_cache.save_telegram_file_id(product_id, file_id, 'thumb')
                                    logger.info(f"💾 Cached file_id (fallback): {product_id}")
                            except Exception as cache_error:
                                logger.warning(f"⚠️ Failed to cache file_id: {cache_error}")
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
