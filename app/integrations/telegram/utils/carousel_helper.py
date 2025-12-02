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
        """
        try:
            # 🔧 FIX: Extraire l'instance Telegram du MarketplaceBot
            # bot peut être soit MarketplaceBot (avec .application.bot) soit telegram.Bot direct
            telegram_bot = bot.application.bot if hasattr(bot, 'application') else bot

            # Validation
            if not products or index >= len(products):
                try:
                    # Tentative d'édition si possible
                    if hasattr(query, 'edit_message_text'):
                        await query.edit_message_text(
                            "❌ No products found" if lang == 'en' else "❌ Aucun produit trouvé"
                        )
                    # Sinon envoi nouveau message
                    elif hasattr(query, 'message') and query.message:
                        await query.message.reply_text("❌ Aucun produit trouvé")
                except:
                    pass
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
                query, telegram_bot, product, image_source, is_file_id, caption, keyboard_markup, parse_mode
            )

        except Exception as e:
            logger.error(f"Error in show_carousel: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                if hasattr(query, 'edit_message_text'):
                    await query.edit_message_text(
                        "❌ Error displaying product" if lang == 'en' else "❌ Erreur affichage produit"
                    )
            except:
                pass

    @staticmethod
    def _get_safe_chat_id(query):
        """
        Méthode robuste pour récupérer le chat_id depuis n'importe quel objet
        (Update, CallbackQuery, Message, ou Mock custom)
        """
        # 1. Update standard ou Context
        if hasattr(query, 'effective_chat') and query.effective_chat:
            return query.effective_chat.id
        
        # 2. CallbackQuery (a un attribut .message)
        if hasattr(query, 'message') and query.message:
            return query.message.chat_id
            
        # 3. Message direct
        if hasattr(query, 'chat_id') and query.chat_id:
            return query.chat_id
            
        # 4. Fallback pour les MockQuery (Commandes /start, etc)
        # Souvent l'ID utilisateur = ID chat en privé
        if hasattr(query, 'from_user') and hasattr(query.from_user, 'id'):
            return query.from_user.id
            
        return None

    @staticmethod
    def _get_image_path(product: Dict):
        """
        Récupère l'image du produit avec cache Telegram file_id (Railway-proof)
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
                    # logger.info(f"⚡ Using cached file_id: {product_id}")
                    return (file_id, True)
            except Exception as e:
                logger.warning(f"⚠️ Could not check file_id cache: {e}")

        # 2. Check if thumbnail_url is B2 URL
        if thumbnail_url and thumbnail_url.startswith('https://'):
            # logger.info(f"🌐 Thumbnail is B2 URL: {product_id}")
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
                        # logger.info(f"📥 Downloaded from B2: {product_id}")
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
                # logger.info(f"🔄 Image missing, downloading from B2: {product_id}")
                image_sync = ImageSyncService()
                b2_path = image_sync.get_image_path_with_fallback(
                    product_id=product_id,
                    seller_id=seller_id,
                    image_type='thumb'
                )
                if b2_path and os.path.exists(b2_path):
                    # logger.info(f"✅ Downloaded from B2: {product_id}")
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
        """
        product_id = product.get('product_id')

        # Check if this is a callback query or command (MockQuery)
        # Un vrai CallbackQuery a .edit_message_media ET .message
        is_callback = hasattr(query, 'edit_message_media') and hasattr(query, 'message') and query.message

        try:
            sent_message = None

            if is_callback:
                # Try to edit existing message (callback query)
                if image_source:
                    if is_file_id:
                        # Use cached file_id (instant)
                        # logger.info(f"⚡ Sending with cached file_id: {product_id}")
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
                
                # --- CORRECTION ICI : Utilisation de la méthode robuste ---
                chat_id = CarouselHelper._get_safe_chat_id(query)
                
                if not chat_id:
                    logger.error(f"❌ Impossible de trouver chat_id sur l'objet {type(query)}")
                    return

                if image_source:
                    if is_file_id:
                        # Use cached file_id
                        sent_message = await bot.send_photo(
                            chat_id=chat_id,
                            photo=image_source,
                            caption=caption,
                            reply_markup=keyboard_markup,
                            parse_mode=parse_mode
                        )
                    elif os.path.exists(image_source):
                        # Send from local file
                        with open(image_source, 'rb') as photo_file:
                            sent_message = await bot.send_photo(
                                chat_id=chat_id,
                                photo=photo_file,
                                caption=caption,
                                reply_markup=keyboard_markup,
                                parse_mode=parse_mode
                            )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=caption,
                        reply_markup=keyboard_markup,
                        parse_mode=parse_mode
                    )

            # Save file_id if sent from local file (not already cached)
            if sent_message and not is_file_id and product_id:
                try:
                    from app.services.telegram_cache_service import get_telegram_cache_service
                    # Gérer différents types de retours (Message ou bool)
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
            # --- CORRECTION ICI AUSSI ---
            chat_id = CarouselHelper._get_safe_chat_id(query)
            
            if not chat_id:
                logger.error("❌ Fallback impossible: chat_id introuvable")
                return

            if image_source:
                if is_file_id:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=image_source,
                        caption=caption,
                        reply_markup=keyboard_markup,
                        parse_mode=parse_mode
                    )
                elif os.path.exists(image_source):
                    with open(image_source, 'rb') as photo_file:
                        sent_message = await bot.send_photo(
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
                                    # logger.info(f"💾 Cached file_id (fallback): {product_id}")
                            except Exception as cache_error:
                                logger.warning(f"⚠️ Failed to cache file_id: {cache_error}")
            else:
                await bot.send_message(
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
