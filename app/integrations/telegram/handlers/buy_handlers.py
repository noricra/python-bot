"""Buy Handlers - Purchase and navigation functions with dependency injection"""

import re
import asyncio
import uuid
import os
from app.core.utils import logger
import time
from typing import Optional, Dict, List
from datetime import datetime
from io import BytesIO


from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.i18n import t as i18n
from app.core import settings as core_settings
from app.core.error_messages import get_error_message, send_error_message
from app.core.seller_notifications import SellerNotifications
from app.integrations.telegram.keyboards import buy_menu_keyboard


class BuyHandlers:
    def __init__(self, product_repo, order_repo, payment_service):
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.payment_service = payment_service

    async def _safe_transition_to_text(self, query, text: str, keyboard=None, parse_mode='Markdown'):
        """
        Gère intelligemment la transition d'un message (photo ou texte) vers un message texte

        Problème résolu:
        - Les carousels ont des photos → edit_message_text() échoue
        - Solution: Détecter photo et supprimer/renvoyer au lieu d'éditer
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
            logger.error(f"Error in _safe_transition_to_text: {e}")
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

    async def buy_menu(self, bot, query, lang: str) -> None:
        """Menu d'achat"""
        keyboard = buy_menu_keyboard(lang)
        buy_text = i18n(lang, 'buy_menu_text')

        await query.edit_message_text(
            buy_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def search_product_prompt(self, bot, query, lang: str) -> None:
        """Demande de saisir un ID produit"""
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_for_product_id'})
        bot.state_manager.update_state(query.from_user.id, waiting_for_product_id=True, lang=lang)

        prompt_text = i18n(lang, 'search_prompt')

        try:
            await query.edit_message_text(
                prompt_text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour",
                                           callback_data='buy_menu')]]),
                parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(
                prompt_text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour",
                                           callback_data='buy_menu')]]),
                parse_mode='Markdown')

    async def browse_categories(self, bot, query, lang: str) -> None:
        """Parcourir les catégories de produits"""
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT name, icon, products_count FROM categories ORDER BY products_count DESC'
            )
            categories = cursor.fetchall()
            conn.close()

            if not categories:
                # Use user-friendly error message system
                error_data = get_error_message('no_products', lang)
                await self._safe_transition_to_text(
                    query,
                    error_data['text'],
                    error_data['keyboard']
                )
                return

            keyboard = []
            # Grouper les catégories par 2 avec truncation intelligente adaptative
            for i in range(0, len(categories), 2):
                row = []
                for j in range(i, min(i + 2, len(categories))):
                    cat_name, cat_icon, products_count = categories[j]

                    # Calcul dynamique de la largeur disponible
                    # Telegram inline buttons : ~40 chars max par bouton sur 2 colonnes
                    # Format: "🔧 Category Name (123)"
                    # Réserver: emoji (2) + espaces (2) + parenthèses+nombre (5) = 9 chars
                    # Reste: 40 - 9 = 31 chars pour le nom

                    max_name_length = 28  # Conservative pour s'assurer que tout rentre
                    display_name = cat_name

                    if len(cat_name) > max_name_length:
                        display_name = cat_name[:max_name_length-1] + "…"

                    row.append(InlineKeyboardButton(
                        f"{cat_icon} {display_name} ({products_count})",
                        callback_data=f'category_{cat_name}'
                    ))
                keyboard.append(row)

            keyboard.append([InlineKeyboardButton(
                "🔙 Back" if lang == 'en' else "🔙 Retour", callback_data='buy_menu'
            )])

            categories_text = i18n(lang, 'categories_title')
            await self._safe_transition_to_text(
                query,
                categories_text,
                InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            await self._safe_transition_to_text(
                query,
                "❌ Error loading categories." if lang == 'en' else "❌ Erreur chargement catégories."
            )

    async def send_product_card(self, bot, chat_id: int, product: dict, lang: str = 'fr'):
        """
        Send visual product card with image + inline buttons

        Args:
            bot: Bot instance
            chat_id: Telegram chat ID
            product: Product dict with all fields
            lang: Language code
        """
        try:
            from app.core.image_utils import ImageUtils
            import os

            # Get thumbnail path (or generate placeholder)
            thumbnail_path = product.get('thumbnail_path')

            if not thumbnail_path or not os.path.exists(thumbnail_path):
                # Generate placeholder if no image
                thumbnail_path = ImageUtils.create_or_get_placeholder(
                    product_title=product.get('title', 'Product'),
                    category=product.get('category', 'default'),
                    product_id=product.get('product_id', 'UNKNOWN')
                )

            # Format rating stars
            rating = product.get('rating', 0.0) or 0.0
            reviews_count = product.get('reviews_count', 0) or 0
            if reviews_count > 0:
                stars = "⭐" * int(round(rating))
                rating_text = f"{stars} {rating:.1f}/5 ({reviews_count} avis)"
            else:
                rating_text = "Aucun avis" if lang == 'fr' else "No reviews"

            # Build caption
            caption = (
                f"🏷️ **{product['title']}**\n"
                f"💰 **{product['price_eur']}€**\n"
                f"{rating_text}\n\n"
                f"🏪 {product.get('seller_name', 'Vendeur')}\n"
                f"📊 {product.get('sales_count', 0)} ventes | {product.get('views_count', 0)} vues"
            )

            # Inline keyboard with actions
            keyboard = [
                [InlineKeyboardButton(
                    "🛒 Acheter" if lang == 'fr' else "🛒 Buy",
                    callback_data=f'buy_{product["product_id"]}'
                )],
                [
                    InlineKeyboardButton(
                        "ℹ️ Détails" if lang == 'fr' else "ℹ️ Details",
                        callback_data=f'product_{product["product_id"]}'
                    ),
                    InlineKeyboardButton(
                        "👁️ Preview",
                        callback_data=f'preview_{product["product_id"]}'
                    )
                ]
            ]

            # Send photo with caption
            if thumbnail_path and os.path.exists(thumbnail_path):
                await bot.application.bot.send_photo(
                    chat_id=chat_id,
                    photo=open(thumbnail_path, 'rb'),
                    caption=caption,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Fallback: send text-only if image fails
                await bot.application.bot.send_message(
                    chat_id=chat_id,
                    text=caption + "\n\n_[Image non disponible]_",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        except Exception as e:
            logger.error(f"Error sending product card: {e}")
            # Fallback text message
            await bot.application.bot.send_message(
                chat_id=chat_id,
                text=f"📦 {product.get('title', 'Product')} - {product.get('price_eur', 0)}€",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("ℹ️ Détails", callback_data=f'product_{product["product_id"]}')
                ]])
            )

    def get_product_badges(self, product: Dict) -> List[str]:
        """Generate badges for product based on stats (Phase 2 - Gamification)"""
        from datetime import datetime, timedelta
        badges = []

        # Best seller (50+ sales)
        if product.get('sales_count', 0) >= 50:
            badges.append("🏆 Best-seller")

        # Nouveauté (< 7 days)
        created_at = product.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_date = created_at

                days_since_creation = (datetime.now() - created_date).days
                if days_since_creation < 7:
                    badges.append("🆕 Nouveau")
            except:
                pass

        # Top rated (4.5+ stars with 10+ reviews)
        if product.get('rating', 0) >= 4.5 and product.get('reviews_count', 0) >= 10:
            badges.append("⭐ Top noté")

        # Trending (high views recently)
        if product.get('views_count', 0) >= 100:
            badges.append("🔥 Populaire")

        return badges

    async def show_product_carousel(self, bot, query, category_key: str, products: List[Dict], index: int = 0, lang: str = 'fr') -> None:
        """
        Phase 2: Carousel navigation - Single message with ⬅️ ➡️ buttons
        UX Type: Instagram Stories / Amazon Product Slider
        """
        try:
            from telegram import InputMediaPhoto
            from app.core.image_utils import ImageUtils
            import os

            if not products or index >= len(products):
                await query.edit_message_text("❌ No products found" if lang == 'en' else "❌ Aucun produit trouvé")
                return

            product = products[index]

            # Get badges
            badges = self.get_product_badges(product)

            # Build caption - UX OPTIMIZED avec hiérarchie visuelle claire
            caption = ""

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 0. BREADCRUMB (Fil d'Ariane - contexte)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            category = product.get('category', 'Produits')
            caption += f"📂 _{category}_\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. BADGES (si présents)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if badges:
                caption += "  ".join(badges) + "\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. TITRE (GRAS pour maximum visibilité)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"**{product['title']}**\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 3. PRIX (TRÈS VISIBLE - élément critique)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"💰 **{product['price_eur']:.2f} €**\n"
            caption += "─────────────────────\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 4. SOCIAL PROOF (Rating + Vendeur)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if product.get('rating', 0) > 0:
                rating_stars = "⭐" * int(product.get('rating', 0))
                caption += f"{rating_stars} **{product.get('rating', 0):.1f}**/5"
                if product.get('reviews_count', 0) > 0:
                    caption += f" _({product.get('reviews_count', 0)} avis)_"
                caption += "\n"

            # Vendeur + Stats ventes
            caption += f"🏪 {product.get('seller_name', 'Vendeur')}"
            if product.get('sales_count', 0) > 0:
                caption += f" • **{product['sales_count']}** ventes"
            caption += "\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 5. DESCRIPTION (Texte utilisateur - GARDER LE MARKDOWN)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if product.get('description'):
                # Limiter longueur mais GARDER le formatage markdown original
                desc = product['description']
                if len(desc) > 180:
                    # Couper intelligemment (au dernier espace avant 180 chars)
                    desc = desc[:180].rsplit(' ', 1)[0] + "..."
                caption += f"{desc}\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 6. MÉTADONNÉES (Catégorie, Taille)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"📂 _{product.get('category', 'N/A')}_"
            if product.get('file_size_mb'):
                caption += f" • 📁 {product.get('file_size_mb', 0):.1f} MB"

            # Get image or placeholder
            thumbnail_path = product.get('thumbnail_path')

            # DEBUG LOG
            logger.info(f"🖼️ CAROUSEL DISPLAY - Product: {product['product_id']}, thumbnail_path from DB: {thumbnail_path}")

            if not thumbnail_path or not os.path.exists(thumbnail_path):
                # Generate placeholder
                logger.info(f"⚠️ Image not found at {thumbnail_path}, generating placeholder")
                thumbnail_path = ImageUtils.create_or_get_placeholder(
                    product_title=product['title'],
                    category=product.get('category', 'General'),
                    product_id=product['product_id']
                )
            else:
                logger.info(f"✅ Using stored image: {thumbnail_path}")

            # Build keyboard - Optimized for purchase (big CTA)
            keyboard = []

            # Row 1: 🛒 GROS BOUTON ACHETER (main CTA - full width when possible)
            keyboard.append([
                InlineKeyboardButton(
                    f"🛒 ACHETER - {product['price_eur']}€" if lang == 'fr' else f"🛒 BUY - {product['price_eur']}€",
                    callback_data=f'buy_product_{product["product_id"]}'
                )
            ])

            # Row 2: Navigation arrows (⬅️ ➡️)
            nav_row = []
            if index > 0:
                nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'carousel_{category_key}_{index-1}'))
            else:
                nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))  # Spacer

            nav_row.append(InlineKeyboardButton(
                f"{index+1}/{len(products)}",
                callback_data='noop'  # Non-clickable position indicator
            ))

            if index < len(products) - 1:
                nav_row.append(InlineKeyboardButton("➡️", callback_data=f'carousel_{category_key}_{index+1}'))
            else:
                nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))  # Spacer

            keyboard.append(nav_row)

            # Row 3: Secondary actions
            keyboard.append([
                InlineKeyboardButton("ℹ️ Détails" if lang == 'fr' else "ℹ️ Details",
                                   callback_data=f'product_details_{product["product_id"]}'),
                InlineKeyboardButton("👁️ Preview" if lang == 'fr' else "👁️ Preview",
                                   callback_data=f'product_preview_{product["product_id"]}')
            ])

            # Row 4: Back to categories
            keyboard.append([
                InlineKeyboardButton("🔙 Catégories" if lang == 'fr' else "🔙 Categories",
                                   callback_data='browse_categories')
            ])

            # Check if this is first call (edit_message_text) or navigation (edit_message_media)
            try:
                if thumbnail_path and os.path.exists(thumbnail_path):
                    # Has image - use edit_message_media
                    with open(thumbnail_path, 'rb') as photo_file:
                        await query.edit_message_media(
                            media=InputMediaPhoto(
                                media=photo_file,
                                caption=caption,
                                parse_mode='Markdown'
                            ),
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                else:
                    # No image - fallback to text only
                    await query.edit_message_text(
                        text=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
            except Exception as e:
                # If edit fails (message too old, etc), send new message
                logger.warning(f"Failed to edit message, sending new: {e}")
                await query.message.delete()

                if thumbnail_path and os.path.exists(thumbnail_path):
                    with open(thumbnail_path, 'rb') as photo_file:
                        await bot.application.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=photo_file,
                            caption=caption,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                else:
                    await bot.application.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )

        except Exception as e:
            logger.error(f"Error in show_product_carousel: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Use user-friendly error message
            error_data = get_error_message('product_load_error', lang)
            try:
                await query.edit_message_text(
                    text=error_data['text'],
                    reply_markup=error_data['keyboard'],
                    parse_mode='Markdown'
                )
            except:
                pass

    async def show_category_products(self, bot, query, category_key: str, lang: str, page: int = 0) -> None:
        """
        Phase 2: Affiche les produits en mode CAROUSEL
        Navigation ⬅️ ➡️ dans un seul message (Instagram Stories style)
        """
        try:
            # Get ALL products from category for carousel navigation
            products = self.product_repo.get_products_by_category(category_key, limit=100, offset=0)

            if not products:
                # Use user-friendly error message
                error_data = get_error_message('no_products', lang,
                    custom_message=f"La catégorie '{category_key}' ne contient pas encore de produits." if lang == 'fr'
                    else f"Category '{category_key}' does not contain any products yet.")
                await query.edit_message_text(
                    text=error_data['text'],
                    reply_markup=error_data['keyboard'],
                    parse_mode='Markdown'
                )
                return

            # Launch carousel mode starting at index 0
            await self.show_product_carousel(bot, query, category_key, products, index=0, lang=lang)

        except Exception as e:
            logger.error(f"Error showing category products: {e}")
            # Use user-friendly error message
            error_data = get_error_message('product_load_error', lang)
            await query.edit_message_text(
                text=error_data['text'],
                reply_markup=error_data['keyboard'],
                parse_mode='Markdown'
            )

    async def show_product_details(self, bot, query, product_id: str, lang: str) -> None:
        """
        Affiche les détails d'un produit - NOUVEAU FORMAT VISUEL AVEC IMAGE
        Redirige vers le format moderne avec carte visuelle
        """
        product = bot.get_product_by_id(product_id)

        if not product:
            await query.edit_message_text(
                (f"❌ **Product not found:** `{product_id}`\n\nCheck the ID or browse categories." if lang=='en'
                 else f"❌ **Produit introuvable :** `{product_id}`\n\nVérifiez l'ID ou cherchez dans les catégories."),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_search'),
                                         callback_data='search_product'),
                    InlineKeyboardButton(i18n(lang, 'btn_categories'),
                                         callback_data='browse_categories')
                ]]),
                parse_mode='Markdown')
            return

        self.product_repo.increment_views(product_id)

        # Use new visual format with image
        await self._show_product_visual(bot, query, product, lang)

    async def _show_product_visual(self, bot, query, product: dict, lang: str):
        """Unified visual product display with image (used by carousel, details, preview back)"""
        from app.core.image_utils import ImageUtils
        from telegram import InputMediaPhoto
        import os

        # Get badges
        badges = self.get_product_badges(product)
        badge_line = " | ".join(badges) if badges else ""

        # Build caption
        rating_stars = "⭐" * int(product.get('rating', 0))

        caption = ""

        if badge_line:
            caption += f"{badge_line}\n\n"

        caption += f"**{product['title']}**\n"
        caption += f"💰 **{product['price_eur']}€**\n\n"

        if product.get('rating', 0) > 0:
            caption += f"{rating_stars} {product.get('rating', 0):.1f}/5 · {product.get('reviews_count', 0)} {'avis' if lang == 'fr' else 'reviews'}\n"

        seller_info = f"🏪 {product.get('seller_name', 'Vendeur' if lang == 'fr' else 'Seller')}"
        if product.get('sales_count', 0) > 0:
            seller_info += f" · {product['sales_count']} {'ventes' if lang == 'fr' else 'sales'}"
        caption += f"{seller_info}\n"

        if product.get('description'):
            caption += f"\n📋 {product['description']}\n"

        caption += f"\n📊 {product.get('views_count', 0)} {'vues' if lang == 'fr' else 'views'} · 📁 {product.get('file_size_mb', 0):.1f} MB"

        # Get image or placeholder
        thumbnail_path = product.get('thumbnail_path')
        logger.info(f"🖼️ VISUAL DISPLAY - Product: {product['product_id']}, thumbnail_path from DB: {thumbnail_path}")

        if not thumbnail_path or not os.path.exists(thumbnail_path):
            logger.info(f"⚠️ Image not found at {thumbnail_path}, generating placeholder")
            thumbnail_path = ImageUtils.create_or_get_placeholder(
                product_title=product['title'],
                category=product.get('category', 'General'),
                product_id=product['product_id']
            )
        else:
            logger.info(f"✅ Using stored image: {thumbnail_path}")

        # Build keyboard
        keyboard = []

        keyboard.append([
            InlineKeyboardButton(
                f"🛒 {'ACHETER' if lang == 'fr' else 'BUY'} - {product['price_eur']}€",
                callback_data=f'buy_product_{product["product_id"]}'
            )
        ])

        keyboard.append([
            InlineKeyboardButton(i18n(lang, 'btn_preview'), callback_data=f'product_preview_{product["product_id"]}')
        ])

        keyboard.append([
            InlineKeyboardButton(i18n(lang, 'btn_categories'), callback_data='browse_categories'),
            InlineKeyboardButton("🏠" + (" Accueil" if lang == 'fr' else " Home"), callback_data='back_main')
        ])

        # Send with image
        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                with open(thumbnail_path, 'rb') as photo_file:
                    await query.edit_message_media(
                        media=InputMediaPhoto(
                            media=photo_file,
                            caption=caption,
                            parse_mode='Markdown'
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            else:
                # Fallback to text only if image completely fails
                await query.edit_message_text(
                    caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error displaying product visual: {e}")
            # Final fallback
            await query.edit_message_text(
                caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    async def process_product_search(self, bot, update, message_text):
        """Traite la recherche de produit par ID"""
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)

        product_id = message_text.strip().upper()

        # No format validation - accept any input for searching

        product = bot.get_product_by_id(product_id)

        if user_id in bot.state_manager.user_states:
            state = bot.state_manager.get_state(user_id)
            for k in ['waiting_for_product_id']:
                state.pop(k, None)
            bot.state_manager.update_state(user_id, **state)

        if product:
            await self.show_product_details_from_search(bot, update, product)
        else:
            await update.message.reply_text(
                f"❌ **Produit introuvable :** `{product_id}`\n\nVérifiez l'ID ou explorez les catégories.",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("📂 Parcourir catégories",
                                             callback_data='browse_categories')
                    ],
                     [
                         InlineKeyboardButton("🔙 Menu achat",
                                              callback_data='buy_menu')
                     ]]),
                parse_mode='Markdown')

    async def show_product_details_from_search(self, bot, update, product):
        """Affiche les détails d'un produit trouvé par recherche - FORMAT VISUEL UNIFIÉ"""
        from app.core.image_utils import ImageUtils
        import os

        # Get badges
        badges = self.get_product_badges(product)

        # Build caption - UX OPTIMIZED (identique au carousel)
        caption = ""

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 0. BREADCRUMB (Fil d'Ariane)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        category = product.get('category', 'Produits')
        caption += f"📂 _{category}_ › Recherche\n\n"

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1. BADGES
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if badges:
            caption += "  ".join(badges) + "\n\n"

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2. TITRE (GRAS pour maximum visibilité)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        caption += f"**{product['title']}**\n\n"

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3. PRIX
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        caption += f"💰 **{product['price_eur']:.2f} €**\n"
        caption += "─────────────────────\n\n"

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4. SOCIAL PROOF
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if product.get('rating', 0) > 0:
            rating_stars = "⭐" * int(product.get('rating', 0))
            caption += f"{rating_stars} **{product.get('rating', 0):.1f}**/5"
            if product.get('reviews_count', 0) > 0:
                caption += f" _({product.get('reviews_count', 0)} avis)_"
            caption += "\n"

        caption += f"🏪 {product.get('seller_name', 'Vendeur')}"
        if product.get('sales_count', 0) > 0:
            caption += f" • **{product['sales_count']}** ventes"
        caption += "\n\n"

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 5. DESCRIPTION COMPLÈTE (Texte utilisateur - GARDER LE MARKDOWN)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if product.get('description'):
            caption += f"{product['description']}\n\n"

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 6. MÉTADONNÉES
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        caption += f"📂 _{product.get('category', 'N/A')}_"
        if product.get('file_size_mb'):
            caption += f"  •  📁 {product.get('file_size_mb', 0):.1f} MB"
        if product.get('views_count', 0) > 0:
            caption += f"  •  👁 {product.get('views_count', 0)} vues"

        # Get image or placeholder
        thumbnail_path = product.get('thumbnail_path')

        # DEBUG LOG
        logger.info(f"🖼️ SEARCH DISPLAY - Product: {product['product_id']}, thumbnail_path from DB: {thumbnail_path}")

        if not thumbnail_path or not os.path.exists(thumbnail_path):
            # Generate placeholder
            logger.info(f"⚠️ Image not found at {thumbnail_path}, generating placeholder")
            thumbnail_path = ImageUtils.create_or_get_placeholder(
                product_title=product['title'],
                category=product.get('category', 'General'),
                product_id=product['product_id']
            )
        else:
            logger.info(f"✅ Using stored image: {thumbnail_path}")

        # Build keyboard - Big CTA button
        keyboard = []

        # Row 1: Big buy button
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 ACHETER - {product['price_eur']}€",
                callback_data=f'buy_product_{product["product_id"]}'
            )
        ])

        # Row 2: Secondary actions
        keyboard.append([
            InlineKeyboardButton("👁️ Aperçu", callback_data=f'product_preview_{product["product_id"]}')
        ])

        # Row 3: Navigation
        keyboard.append([
            InlineKeyboardButton("📂 Catégories", callback_data='browse_categories'),
            InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
        ])

        # Send with image
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            # Fallback to text only if image completely fails
            await update.message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    async def check_payment_handler(self, bot, query, order_id, lang):
        """Vérifie le statut du paiement, met à jour les entités et crée un payout vendeur."""
        # Check if message has photo (QR code) - can't edit photo message text
        try:
            if query.message.photo:
                # Send new message instead of editing
                await query.message.reply_text("🔍 Vérification en cours...")
            else:
                await query.edit_message_text("🔍 Vérification en cours...")
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            # Fallback: send new message
            await query.message.reply_text("🔍 Vérification en cours...")

        conn = bot.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id, ))
            order = cursor.fetchone()
        except Exception as e:
            conn.close()
            return

        if not order:
            await query.edit_message_text("❌ Commande introuvable!")
            return

        payment_id = order[12]

        # Check if payment_id exists
        if not payment_id:
            conn.close()
            logger.error(f"No payment_id for order {order_id}")
            try:
                error_keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 Support", callback_data='support_menu'),
                    InlineKeyboardButton("🏠 Menu", callback_data='back_main')
                ]])
                await self._safe_edit_message(query,
                    "❌ Erreur: Paiement non trouvé. Contactez le support." if lang == 'fr'
                    else "❌ Error: Payment not found. Contact support.",
                    error_keyboard)
            except Exception:
                await query.message.reply_text(
                    "❌ Erreur: Paiement non trouvé. Contactez le support." if lang == 'fr'
                    else "❌ Error: Payment not found. Contact support.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💬 Support", callback_data='support_menu')
                    ]])
                )
            return

        payment_status = await asyncio.to_thread(self.payment_service.check_payment_status, payment_id)

        if payment_status:
            status = payment_status.get('payment_status', 'waiting')

            if status in ['finished', 'confirmed']:
                try:
                    cursor.execute(
                        '''
                        UPDATE orders
                        SET payment_status = 'completed',
                            completed_at = CURRENT_TIMESTAMP,
                            file_delivered = TRUE
                        WHERE order_id = ?
                    ''', (order_id, ))

                    cursor.execute(
                        '''
                        UPDATE products
                        SET sales_count = sales_count + 1
                        WHERE product_id = ?
                    ''', (order[3], ))

                    cursor.execute(
                        '''
                        UPDATE users
                        SET total_sales = total_sales + 1,
                            total_revenue = total_revenue + ?
                        WHERE user_id = ?
                    ''', (order[7], order[4]))

                    # Partner commission removed - referral system deleted

                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    conn.close()
                    return

                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 📢 NOTIFICATION VENDEUR : Paiement confirmé
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                try:
                    # Get product data and buyer info for notification
                    cursor.execute('SELECT * FROM products WHERE product_id = ?', (order[3],))
                    product_row = cursor.fetchone()

                    if product_row:
                        product_data = {
                            'product_id': product_row[0],
                            'title': product_row[1],
                            'seller_user_id': product_row[4]
                        }

                        buyer_name = query.from_user.first_name or query.from_user.username or "Acheteur"

                        # Send notification to seller
                        await SellerNotifications.notify_payment_confirmed(
                            bot=bot,
                            seller_id=product_row[4],  # seller_user_id
                            product_data=product_data,
                            buyer_name=buyer_name,
                            amount_eur=order[7],  # price_eur
                            crypto_code=order[8],  # payment_currency
                            tx_hash=payment_status.get('payment_hash')
                        )
                        logger.info(f"✅ Seller notification sent for order {order_id}")
                except Exception as notif_error:
                    logger.error(f"❌ Failed to send seller notification: {notif_error}")
                    # Don't fail the payment if notification fails

                try:
                    payout_created = await bot.auto_create_seller_payout(order_id)
                except Exception as e:
                    payout_created = False
                finally:
                    conn.close()

                success_text = f"""🎉 **FÉLICITATIONS !**

✅ **Paiement confirmé** - Commande : {order_id}
{"✅ Payout vendeur créé automatiquement" if payout_created else "⚠️ Payout vendeur en attente"}

📚 **ACCÈS IMMÉDIAT À VOTRE FORMATION**"""

                keyboard = [[
                    InlineKeyboardButton(
                        "📥 Télécharger maintenant",
                        callback_data=f'download_product_{order[3]}')
                ], [
                    InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')
                ]]

                await self._safe_edit_message(query, success_text, InlineKeyboardMarkup(keyboard))
            else:
                conn.close()
                try:
                    status_text = (f"⏳ **PAYMENT IN PROGRESS**\n\n🔍 **Status:** {status}\n\n💡 Confirmations can take 5-30 min" if lang == 'en' else f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Les confirmations peuvent prendre 5-30 min")
                    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
                        "🔄 Refresh" if lang == 'en' else "🔄 Rafraîchir", callback_data=f'check_payment_{order_id}')]])
                    await self._safe_edit_message(query, status_text, keyboard)
                except Exception:
                    await query.message.reply_text(
                        (f"⏳ **PAYMENT IN PROGRESS**\n\n🔍 **Status:** {status}\n\n💡 Confirmations can take 5-30 min" if lang == 'en' else f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Les confirmations peuvent prendre 5-30 min"),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                            "🔄 Refresh" if lang == 'en' else "🔄 Rafraîchir", callback_data=f'check_payment_{order_id}')]]),
                        parse_mode='Markdown')
        else:
            conn.close()
            try:
                error_keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Retry" if lang == 'en' else "🔄 Réessayer",
                                         callback_data=f'check_payment_{order_id}')
                ], [
                    InlineKeyboardButton("💬 Support", callback_data='support_menu')
                ]])
                await self._safe_edit_message(query, i18n(lang, 'err_verify'), error_keyboard)
            except Exception:
                await query.message.reply_text(
                    i18n(lang, 'err_verify'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Retry" if lang == 'en' else "🔄 Réessayer",
                                             callback_data=f'check_payment_{order_id}')
                    ], [
                        InlineKeyboardButton("💬 Support", callback_data='support_menu')
                    ]]),
                    parse_mode='Markdown')

    # Library Methods - Extracted from bot_mlt.py
    async def show_my_library(self, bot, query, lang):
        """Bibliothèque utilisateur"""
        user_id = query.from_user.id
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.product_id, p.title, MAX(o.completed_at) as completed_at
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = ? AND o.payment_status = 'completed'
                GROUP BY p.product_id, p.title
                ORDER BY MAX(o.completed_at) DESC
                LIMIT 10
            ''', (user_id,))
            purchases = cursor.fetchall()
            conn.close()

            if not purchases:
                await query.edit_message_text(
                    "📚 Aucun achat trouvé." if lang == 'fr' else "📚 No purchases found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🛒 Acheter" if lang == 'fr' else "🛒 Buy", callback_data='buy_menu'),
                        InlineKeyboardButton("🏠 Accueil" if lang == 'fr' else "🏠 Home", callback_data='back_main')
                    ]])
                )
                return

            text = "📚 **MA BIBLIOTHÈQUE**\n\n" if lang == 'fr' else "📚 **MY LIBRARY**\n\n"
            keyboard = []
            for product_id, title, completed_at in purchases:
                text += f"📖 {title[:30]}...\n"
                keyboard.append([
                    InlineKeyboardButton(f"⬇️ Télécharger" if lang == 'fr' else f"⬇️ Download", callback_data=f'download_product_{product_id}'),
                    InlineKeyboardButton(f"📞 Contact" if lang == 'fr' else f"📞 Contact", callback_data=f'contact_seller_{product_id}')
                ])
            keyboard.append([InlineKeyboardButton("🏠 Accueil" if lang == 'fr' else "🏠 Home", callback_data='back_main')])

            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erreur bibliothèque: {e}")
            await query.edit_message_text(
                "❌ Erreur chargement bibliothèque." if lang == 'fr' else "❌ Error loading library.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Accueil" if lang == 'fr' else "🏠 Home", callback_data='back_main')
                ]])
            )

    async def download_product(self, bot, query, context, product_id, lang):
        """Télécharger produit acheté"""
        user_id = query.from_user.id
        try:
            # Vérifier achat
            conn = bot.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.main_file_path, p.title
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = ? AND o.product_id = ? AND o.payment_status = 'completed'
            ''', (user_id, product_id))
            result = cursor.fetchone()
            conn.close()

            if not result:
                await query.edit_message_text(
                    "❌ Produit non acheté ou introuvable." if lang == 'fr' else "❌ Product not purchased or not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Accueil" if lang == 'fr' else "🏠 Home", callback_data='back_main')
                    ]])
                )
                return

            file_path, title = result

            # Construire le chemin complet vers le fichier
            from app.core.settings import settings
            full_file_path = os.path.join(settings.UPLOADS_DIR, file_path) if file_path else None

            if not file_path or not os.path.exists(full_file_path):
                await query.edit_message_text(
                    "❌ Fichier introuvable." if lang == 'fr' else "❌ File not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Accueil" if lang == 'fr' else "🏠 Home", callback_data='back_main')
                    ]])
                )
                return

            # Envoyer le fichier - utiliser query.get_bot() si context n'est pas disponible
            bot_instance = context.bot if context else query.get_bot()
            await bot_instance.send_document(
                chat_id=query.message.chat_id,
                document=open(full_file_path, 'rb'),
                caption=f"📖 {title}"
            )

        except Exception as e:
            logger.error(f"Erreur téléchargement: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du téléchargement." if lang == 'fr' else "❌ Download error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Accueil" if lang == 'fr' else "🏠 Home", callback_data='back_main')
                ]])
            )

    async def buy_product(self, bot, query, product_id: str, lang: str):
        """Show crypto selection for product purchase"""
        try:
            # Get product details
            product = bot.get_product_by_id(product_id)
            if not product:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='browse_categories')
                ]])
                await self._safe_transition_to_text(query, i18n(lang, 'err_product_not_found'), keyboard)
                return

            # Check if user already owns this product
            user_id = query.from_user.id
            if self.order_repo.check_user_purchased_product(user_id, product_id):
                # User already owns this product, redirect to library
                already_owned_text = (
                    "✅ **YOU ALREADY OWN THIS PRODUCT**\n\n"
                    "This product is already in your library.\n"
                    "You can download it anytime from your library."
                    if lang == 'en' else
                    "✅ **VOUS POSSÉDEZ DÉJÀ CE PRODUIT**\n\n"
                    "Ce produit est déjà dans votre bibliothèque.\n"
                    "Vous pouvez le télécharger à tout moment."
                )

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "📚 My Library" if lang == 'en' else "📚 Ma Bibliothèque",
                        callback_data='library_menu'
                    )],
                    [InlineKeyboardButton(
                        "📥 Download Now" if lang == 'en' else "📥 Télécharger",
                        callback_data=f'download_product_{product_id}'
                    )],
                    [InlineKeyboardButton(
                        "🔙 Back" if lang == 'en' else "🔙 Retour",
                        callback_data=f'product_{product_id}'
                    )]
                ])

                # Gérer transition depuis carousel (message avec photo)
                await self._safe_transition_to_text(query, already_owned_text, keyboard)
                return

            # Show crypto selection menu
            title = product.get('title', 'Produit')
            price_eur = product.get('price_eur', 0)

            text = f"💳 **{i18n(lang, 'payment_title')}**\n\n📦 {bot.escape_markdown(title)}\n💰 {price_eur}€\n\n{i18n(lang, 'crypto_selection_text')}"

            keyboard = []
            from app.core.settings import settings

            # Display available cryptos from settings
            for crypto_code, (display_name, time_info) in settings.CRYPTO_DISPLAY_INFO.items():
                keyboard.append([InlineKeyboardButton(
                    f"{display_name} {time_info}",
                    callback_data=f'pay_crypto_{crypto_code}_{product_id}'
                )])

            keyboard.append([InlineKeyboardButton(
                i18n(lang, 'btn_back'),
                callback_data=f'product_{product_id}'
            )])

            # Gérer transition depuis carousel (message avec photo)
            await self._safe_transition_to_text(query, text, InlineKeyboardMarkup(keyboard))

        except Exception as e:
            logger.error(f"Error buying product: {e}")
            keyboard_error = InlineKeyboardMarkup([[
                InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='browse_categories')
            ]])
            await self._safe_transition_to_text(query, i18n(lang, 'err_purchase_error'), keyboard_error)

    async def process_crypto_payment(self, bot, query, crypto_code: str, product_id: str, lang: str):
        """Create payment with selected crypto using NowPayments"""
        try:
            # Get product details
            product = bot.get_product_by_id(product_id)
            if not product:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='browse_categories')
                ]])
                await self._safe_transition_to_text(query, i18n(lang, 'err_product_not_found'), keyboard)
                return

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # LOADING STATE (création paiement NowPayments peut prendre 2-3s)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                await self._safe_transition_to_text(
                    query,
                    "🔄 Création du paiement en cours..." if lang == 'fr' else "🔄 Creating payment..."
                )
            except:
                pass

            user_id = query.from_user.id
            title = product.get('title', 'Produit')
            price_eur = product.get('price_eur', 0)
            price_usd = price_eur * self.payment_service.get_exchange_rate()

            # Create order in database
            order_id = f"TBO-{user_id}-{int(time.time())}"

            # Create NowPayments payment with enhanced data
            payment_data = self.payment_service.create_payment(
                amount_usd=price_usd,
                pay_currency=crypto_code,
                order_id=order_id,
                description=title,
                ipn_callback_url=core_settings.IPN_CALLBACK_URL
            )

            if not payment_data:
                await query.edit_message_text(
                    "❌ Failed to create payment. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data=f'buy_product_{product_id}')
                    ]])
                )
                return

            # Store order in database
            from app.core import get_sqlite_connection
            from app.core.settings import settings

            conn = get_sqlite_connection(settings.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (order_id, buyer_user_id, seller_user_id, product_id,
                                  product_title, product_price_eur, payment_id, payment_currency,
                                  payment_status, created_at, nowpayments_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, user_id, product.get('seller_user_id'), product_id, title,
                  price_eur, payment_data.get('payment_id'), crypto_code, 'waiting',
                  int(time.time()), payment_data.get('payment_id')))
            conn.commit()
            conn.close()

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 📢 NOTIFICATION VENDEUR : Nouvel achat initié
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                buyer_name = query.from_user.first_name or query.from_user.username or "Acheteur anonyme"

                await SellerNotifications.notify_new_purchase(
                    bot=bot,
                    seller_id=product.get('seller_user_id'),
                    product_data={
                        'product_id': product_id,
                        'title': title
                    },
                    buyer_name=buyer_name,
                    amount_eur=price_eur,
                    crypto_code=crypto_code
                )
                logger.info(f"✅ New purchase notification sent to seller for order {order_id}")
            except Exception as notif_error:
                logger.error(f"❌ Failed to send new purchase notification: {notif_error}")
                # Don't fail the purchase if notification fails

            # Display comprehensive payment info with QR code
            await self._display_payment_details(query, payment_data, title, price_eur, price_usd, order_id, product_id, crypto_code, lang)

        except Exception as e:
            logger.error(f"Error processing crypto payment: {e}")
            await query.edit_message_text(
                i18n(lang, 'err_payment_creation'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data=f'buy_product_{product_id}')
                ]])
            )

    async def preview_product(self, query, product_id: str, lang: str):
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # LOADING STATE (opération potentiellement longue pour PDF)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            await query.answer(
                "🔄 Génération de l'aperçu..." if lang == 'fr' else "🔄 Generating preview...",
                show_alert=False
            )
        except:
            pass  # Pas grave si ça échoue

        from app.core.utils import escape_markdown
        product = self.product_repo.get_product_by_id(product_id)
        if not product:
            from app.core.i18n import t as i18n
            await query.edit_message_text(i18n(lang, 'err_product_not_found'))
            return

        # Extrait de description (200-300 chars)
        desc = (product['description'] or '')
        snippet_raw = (desc[:300] + '…') if len(desc) > 300 else desc or ("No preview available" if lang=='en' else "Aucun aperçu disponible")
        safe_title = escape_markdown(str(product.get('title') or ''))
        snippet = escape_markdown(snippet_raw)
        text = (
            f"👀 **PREVIEW**\n\n📦 {safe_title}\n\n{snippet}" if lang=='en'
            else f"👀 **APERÇU**\n\n📦 {safe_title}\n\n{snippet}"
        )

        media_preview_sent = False

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ENHANCED PREVIEW SYSTEM - Supports PDF, Video, Zip
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            import os
            from io import BytesIO
            from app.core.settings import settings

            main_path = product.get('main_file_path') or ''
            logger.info(f"[Preview] Product main_file_path: {main_path}")
            logger.info(f"[Preview] UPLOADS_DIR: {settings.UPLOADS_DIR}")

            if isinstance(main_path, str) and main_path:
                # Construire le chemin complet
                full_path = os.path.join(settings.UPLOADS_DIR, main_path)
                logger.info(f"[Preview] Full path constructed: {full_path}")
                logger.info(f"[Preview] File exists check: {os.path.exists(full_path)}")

                if os.path.exists(full_path):
                    file_ext = main_path.lower().split('.')[-1]

                    # ═══════════════════════════════════════
                    # PDF PREVIEW (first page as image)
                    # ═══════════════════════════════════════
                    if file_ext == 'pdf':
                        logger.info(f"[PDF Preview] Generating preview...")
                        try:
                            import fitz  # PyMuPDF
                            doc = fitz.open(full_path)
                            if doc.page_count > 0:
                                page = doc.load_page(0)
                                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                                bio = BytesIO(pix.tobytes('png'))
                                bio.seek(0)

                                caption_text = (
                                    f"📄 **Preview — Page 1/{doc.page_count}**\n\n"
                                    f"_{safe_title}_" if lang=='en'
                                    else f"📄 **Aperçu — Page 1/{doc.page_count}**\n\n"
                                    f"_{safe_title}_"
                                )

                                # Delete original message first
                                try:
                                    await query.delete_message()
                                except:
                                    pass

                                # Send PDF preview
                                await query.message.reply_photo(photo=bio, caption=caption_text, parse_mode='Markdown')
                                doc.close()
                                logger.info(f"[PDF Preview] Preview sent successfully!")
                                media_preview_sent = True
                            else:
                                logger.warning(f"[PDF Preview] PDF has no pages")
                        except Exception as e:
                            logger.error(f"[PDF Preview] Error: {e}")

                    # ═══════════════════════════════════════
                    # VIDEO PREVIEW (first frame thumbnail)
                    # ═══════════════════════════════════════
                    elif file_ext in ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv']:
                        logger.info(f"[Video Preview] Generating thumbnail...")
                        try:
                            # Generate thumbnail from first frame
                            thumbnail_path = f"/tmp/video_thumb_{product_id}.jpg"

                            # Use ffmpeg to extract first frame
                            import subprocess
                            result = subprocess.run([
                                'ffmpeg', '-i', full_path,
                                '-ss', '00:00:01',  # 1 second in
                                '-vframes', '1',  # Extract 1 frame
                                '-vf', 'scale=800:-1',  # Resize to 800px width
                                '-y',  # Overwrite
                                thumbnail_path
                            ], capture_output=True, timeout=10)

                            if os.path.exists(thumbnail_path):
                                # Get video duration
                                duration_result = subprocess.run([
                                    'ffprobe', '-v', 'error',
                                    '-show_entries', 'format=duration',
                                    '-of', 'default=noprint_wrappers=1:nokey=1',
                                    full_path
                                ], capture_output=True, text=True, timeout=5)

                                duration_sec = int(float(duration_result.stdout.strip() or 0))
                                duration_min = duration_sec // 60
                                duration_sec_rem = duration_sec % 60
                                duration_str = f"{duration_min}:{duration_sec_rem:02d}"

                                caption_text = (
                                    f"🎬 **Video Preview**\n\n"
                                    f"_{safe_title}_\n\n"
                                    f"⏱️ Duration: {duration_str}\n"
                                    f"💡 Full video available after purchase" if lang=='en'
                                    else f"🎬 **Aperçu Vidéo**\n\n"
                                    f"_{safe_title}_\n\n"
                                    f"⏱️ Durée: {duration_str}\n"
                                    f"💡 Vidéo complète disponible après achat"
                                )

                                # Delete original message
                                try:
                                    await query.delete_message()
                                except:
                                    pass

                                # Send thumbnail
                                with open(thumbnail_path, 'rb') as thumb_file:
                                    await query.message.reply_photo(
                                        photo=thumb_file,
                                        caption=caption_text,
                                        parse_mode='Markdown'
                                    )

                                # Cleanup
                                os.remove(thumbnail_path)
                                logger.info(f"[Video Preview] Thumbnail sent successfully!")
                                media_preview_sent = True
                            else:
                                logger.warning(f"[Video Preview] Thumbnail not generated")
                        except Exception as e:
                            logger.error(f"[Video Preview] Error: {e}")

                    # ═══════════════════════════════════════
                    # ZIP/ARCHIVE PREVIEW (file list)
                    # ═══════════════════════════════════════
                    elif file_ext in ['zip', 'rar', '7z', 'tar', 'gz']:
                        logger.info(f"[Archive Preview] Listing contents...")
                        try:
                            import zipfile

                            file_list = []
                            total_size = 0

                            if file_ext == 'zip':
                                with zipfile.ZipFile(full_path, 'r') as zip_ref:
                                    info_list = zip_ref.infolist()

                                    # Get first 10 files
                                    for info in info_list[:10]:
                                        if not info.is_dir():
                                            size_mb = info.file_size / (1024 * 1024)
                                            file_list.append(f"  • {info.filename} ({size_mb:.1f} MB)")
                                            total_size += info.file_size

                                    if len(info_list) > 10:
                                        file_list.append(f"  ... et {len(info_list) - 10} fichiers de plus")

                            total_size_mb = total_size / (1024 * 1024)
                            files_text = '\n'.join(file_list) if file_list else ("No files found" if lang=='en' else "Aucun fichier trouvé")

                            caption_text = (
                                f"📦 **Archive Preview**\n\n"
                                f"_{safe_title}_\n\n"
                                f"**Contents ({len(file_list)} files shown):**\n{files_text}\n\n"
                                f"📊 Total size: {total_size_mb:.1f} MB" if lang=='en'
                                else f"📦 **Aperçu Archive**\n\n"
                                f"_{safe_title}_\n\n"
                                f"**Contenu ({len(file_list)} fichiers affichés):**\n{files_text}\n\n"
                                f"📊 Taille totale: {total_size_mb:.1f} MB"
                            )

                            # Delete original message
                            try:
                                await query.delete_message()
                            except:
                                pass

                            # Send archive preview
                            await query.message.reply_text(caption_text, parse_mode='Markdown')
                            logger.info(f"[Archive Preview] Preview sent successfully!")
                            media_preview_sent = True
                        except Exception as e:
                            logger.error(f"[Archive Preview] Error: {e}")
                else:
                    logger.warning(f"[Preview] File does not exist: {full_path}")
        except Exception as e:
            logger.error(f"[Preview] General error: {e}")

        # Show text preview if no media preview was sent
        if not media_preview_sent:
            try:
                await query.edit_message_text(text, parse_mode='Markdown')
            except Exception as e:
                logger.warning(f"Fallback to reply_text for preview: {e}")
                await query.message.reply_text(text, parse_mode='Markdown')

        # Now send action buttons AFTER the preview content (at the bottom, easy to access)
        from app.core.i18n import t as i18n
        keyboard = [
            [InlineKeyboardButton(i18n(lang, 'btn_buy'), callback_data=f'buy_product_{product_id}')],
            [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data=f'product_{product_id}')]
        ]

        action_text = (
            "👇 **What would you like to do?**" if lang=='en'
            else "👇 **Que souhaitez-vous faire ?**"
        )

        await query.message.reply_text(
            action_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def mark_as_paid(self, bot, query, product_id: str, lang: str):
        """Mark order as paid (test functionality)"""
        try:
            user_id = query.from_user.id

            # Create mock order in database
            conn = bot.get_db_connection()
            cursor = conn.cursor()

            # Insert order
            order_id = f"ord_{user_id}_{product_id}_{int(datetime.now().timestamp())}"
            cursor.execute('''
                INSERT OR REPLACE INTO orders
                (order_id, buyer_user_id, product_id, payment_status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, user_id, product_id, 'completed', datetime.now().isoformat()))

            conn.commit()
            conn.close()

            # Get product details for confirmation
            product = bot.get_product_by_id(product_id)
            title = product.get('title', 'Produit') if product else 'Produit'

            await query.edit_message_text(
                f"✅ **Paiement confirmé !**\n\n📦 {title}\n\n🎉 Votre commande est maintenant disponible dans votre bibliothèque.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Ma bibliothèque" if lang == 'fr' else "📚 My library",
                                        callback_data='library')],
                    [InlineKeyboardButton("⬇️ Télécharger maintenant" if lang == 'fr' else "⬇️ Download now",
                                        callback_data=f'download_product_{product_id}')],
                    [InlineKeyboardButton("🏠 Accueil" if lang == 'fr' else "🏠 Home", callback_data='back_main')]
                ]),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error marking as paid: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de la confirmation du paiement." if lang == 'fr' else "❌ Payment confirmation error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='browse_categories')
                ]])
            )

    async def _display_payment_details(self, query, payment_data, title, price_eur, price_usd, order_id, product_id, crypto_code, lang):
        """Display comprehensive payment details with QR code and exact amounts"""
        try:
            # Get payment details
            payment_details = payment_data.get('payment_details', {})
            payment_address = payment_details.get('address') or payment_data.get('pay_address', '')
            exact_amount = payment_details.get('amount') or payment_data.get('exact_crypto_amount')
            formatted_amount = payment_data.get('formatted_amount', f"{exact_amount:.8f}" if exact_amount else "N/A")
            network = payment_details.get('network', crypto_code.upper())
            qr_code = payment_data.get('qr_code')

            # Build payment message
            text = f"💳 **Payment Created / Paiement Créé**\n\n"
            text += f"📦 **Product / Produit:** {title}\n"
            text += f"💰 **Price / Prix:** {price_eur}€ ({price_usd:.2f} USD)\n"
            text += f"🔗 **Network / Réseau:** {network}\n\n"

            text += f"**💎 Exact Amount / Montant Exact:**\n"
            text += f"`{formatted_amount} {crypto_code.upper()}`\n\n"

            text += f"**📍 Payment Address / Adresse de Paiement:**\n"
            text += f"`{payment_address}`\n\n"

            text += f"**📋 Order ID:** `{order_id}`\n\n"

            text += "⏰ **Payment expires in 1 hour / Le paiement expire dans 1 heure**\n"
            text += "🔔 You will receive automatic notification when payment is confirmed"

            keyboard = [
                [InlineKeyboardButton(f"🔄 Refresh Status / Actualiser", callback_data=f'refresh_payment_{order_id}')],
                [InlineKeyboardButton(f"👁️ Preview / Aperçu", callback_data=f'preview_product_{product_id}')],
                [InlineKeyboardButton("🔙 Back / Retour", callback_data=f'buy_product_{product_id}')]
            ]

            # Try to send QR code image if available
            if qr_code:
                try:
                    import base64
                    from io import BytesIO

                    # Decode base64 QR code
                    img_data = base64.b64decode(qr_code)
                    img_buffer = BytesIO(img_data)
                    img_buffer.name = f'payment_qr_{order_id}.png'

                    # Delete the original message first
                    try:
                        await query.delete_message()
                    except:
                        pass

                    # Send QR code as photo WITHOUT caption (separate messages)
                    await query.message.reply_photo(
                        photo=img_buffer
                    )

                    # Send payment details as separate text message with buttons
                    await query.message.reply_text(
                        text,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )

                    return

                except Exception as e:
                    logger.error(f"Error sending QR code: {e}")
                    # Fall back to text-only message

            # Fallback: send text-only message
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error displaying payment details: {e}")
            # Basic fallback message
            await query.edit_message_text(
                f"💳 Payment created for order `{order_id}`\n\nAddress: `{payment_address}`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data=f'buy_product_{product_id}')
                ]])
            )

    async def _safe_edit_message(self, query, text: str, reply_markup=None):
        """Safely edit message, handling photo messages and identical content"""
        try:
            if query.message.photo:
                # Can't edit photo caption as text message, send new message
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in _safe_edit_message: {e}")
            # Fallback: send new message
            try:
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as fallback_error:
                logger.error(f"Fallback message failed: {fallback_error}")