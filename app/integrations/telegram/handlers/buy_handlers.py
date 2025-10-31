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
import psycopg2
import psycopg2.extras


from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.i18n import t as i18n
from app.core import settings as core_settings
from app.core.error_messages import get_error_message
from app.core.seller_notifications import SellerNotifications
from app.integrations.telegram.keyboards import buy_menu_keyboard, back_to_main_button
from app.integrations.telegram.utils import safe_transition_to_text


class BuyHandlers:
    def __init__(self, product_repo, order_repo, payment_service, review_repo=None):
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.payment_service = payment_service
        self.review_repo = review_repo  # V2: Added for reviews functionality

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # V2 WORKFLOW: HELPER FUNCTIONS (Refactored to eliminate code duplication)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _format_number(self, num: int) -> str:
        """Format numbers: 1234 → 1.2k, 12345 → 12.3k"""
        if num >= 1000:
            return f"{num/1000:.1f}k"
        return str(num)

    def _build_buy_button_label(self, price_usd: float, lang: str = 'fr') -> str:
        """Génère le label du bouton buy (réutilisable partout)"""
        return f"💳 ACHETER - ${price_usd:.2f} 💳 💳" if lang == 'fr' else f"💳 BUY - ${price_usd:.2f} 💳 💳"

    def _build_product_caption(self, product: Dict, mode: str = 'short', lang: str = 'fr') -> str:
        """
        Build product caption with smart truncation

        Args:
            product: Product dict
            mode: 'short' (MINIMAL - fits iPhone screen) or 'full' (complete description)
            lang: Language code

        Returns:
            Formatted caption string
        """
        caption = ""

        if mode == 'short':
            # V2 REDESIGN: Card Courte (Carousel) - Design épuré et moderne

            category = product.get('category', 'Produits')
            title = product['title']
            price = product['price_usd']
            seller = product.get('seller_name', 'Vendeur')
            rating = product.get('rating', 0)
            reviews_count = product.get('reviews_count', 0)
            sales = product.get('sales_count', 0)
            views = product.get('views_count', 0)
            file_size = product.get('file_size_mb', 0)

            # Format numbers (1234 → 1.2k)
            sales_formatted = self._format_number(sales) if sales >= 1000 else str(sales)
            views_formatted = self._format_number(views)

            # ✨ BADGES AUTOMATIQUES (Gamification)
            badges = self.get_product_badges(product)
            if badges:
                badge_line = " | ".join(badges)
                caption += f"{badge_line}\n\n"

            # Seller bio display (only shown in seller shop view)
            seller_bio = product.get('seller_bio_display')
            if seller_bio:
                caption += f"🏪 <b>{seller}</b>\n"
                caption += f"<i>{seller_bio}</i>\n\n"
                caption += "────────────────\n\n"

            # Titre (BOLD uniquement)
            caption += f"<b>{title}</b>\n"

            # Vendeur (texte normal, pas de bold ni italique)
            caption += f"<i>par {seller}</i>\n\n" if lang == 'fr' else f"<i>by {seller}</i>\n\n"

            # Stats avec labels texte complets
            stats_text = f"⭐ {rating:.1f}/5 ({reviews_count})" if lang == 'fr' else f"⭐ {rating:.1f}/5 ({reviews_count})"
            stats_text += f"  •  {sales_formatted} ventes\n" if lang == 'fr' else f"  •  {sales_formatted} sales\n"
           # stats_text += f" • {views_formatted} vues\n" if lang == 'fr' else f" • {views_formatted} views\n"
            caption += stats_text

            # Séparateur #2
            caption += "────────────────\n"

            # Métadonnées (catégorie + taille)
            caption += f"📂 {category} • 📁 {file_size:.1f} MB"

        
        elif mode == 'full':
            # V2 REDESIGN: Card Complète (Détails) - Design épuré avec description

            category = product.get('category', 'Produits')
            title = product['title']
            price = product['price_usd']
            seller = product.get('seller_name', 'Vendeur')
            rating = product.get('rating', 0)
            reviews_count = product.get('reviews_count', 0)
            sales = product.get('sales_count', 0)
            views = product.get('views_count', 0)
            file_size = product.get('file_size_mb', 0)

            # Format numbers (1234 → 1.2k)
            sales_formatted = self._format_number(sales) if sales >= 1000 else str(sales)
            views_formatted = self._format_number(views)

            # ✨ BADGES AUTOMATIQUES (Gamification)
            badges = self.get_product_badges(product)
            if badges:
                badge_line = " | ".join(badges)
                caption += f"{badge_line}\n\n"

            # Titre (BOLD uniquement)
            caption += f"<b>{title}</b>\n"

            # Vendeur (texte normal, pas de bold ni italique)
            caption += f"<i>par {seller}</i>\n\n" if lang == 'fr' else f"<i>by {seller}</i>\n\n"


            # Stats avec labels texte complets
            stats_text = f"⭐ {rating:.1f}/5 ({reviews_count})" if lang == 'fr' else f"⭐ {rating:.1f}/5 ({reviews_count})"
            stats_text += f" • {sales_formatted} ventes" if lang == 'fr' else f" • {sales_formatted} sales"
            stats_text += f" • {views_formatted} vues\n\n" if lang == 'fr' else f" • {views_formatted} views\n\n"
            caption += stats_text

            # Description avec label italique discret (MODE FULL uniquement)
            if product.get('description'):
                about_label = "<i>À propos :</i>\n" if lang == 'fr' else "<i>About:</i>\n"
                caption += f"{about_label}{product['description']}\n\n"

            # Métadonnées (catégorie + taille)
            caption += f"📂 {category} • 📁 {file_size:.1f} MB\n"

            # Product ID
            product_id = product.get('product_id', '')
            if product_id:
                caption += f"🔖 ID: <code>{product_id}</code>\n"

            # Séparateur #2
            caption += "────────────────\n"

            # Message recherche ID (gardé pour visibilité)
            search_hint = "🔍 Vous avez un ID ? Entrez-le directement" if lang == 'fr' else "🔍 Have an ID? Enter it directly"
            caption += search_hint


        return caption

    def _get_product_image_or_placeholder(self, product: Dict) -> str:
        """
        Get product image path or generate placeholder

        Args:
            product: Product dict

        Returns:
            Path to image file (absolute path)
        """
        from app.core.image_utils import ImageUtils
        from app.core.settings import get_absolute_path
        import os

        thumbnail_path = product.get('thumbnail_url')

        logger.info(f"🖼️ Image lookup - Product: {product['product_id']}, thumbnail_url (raw): {thumbnail_path}")

        # Convert to absolute path if relative
        if thumbnail_path:
            thumbnail_path_abs = get_absolute_path(thumbnail_path)
            logger.info(f"📁 Resolved absolute path: {thumbnail_path_abs}")
        else:
            thumbnail_path_abs = None

        # Check if file exists (with absolute path)
        if not thumbnail_path_abs or not os.path.exists(thumbnail_path_abs):
            if thumbnail_path_abs:
                logger.warning(f"⚠️ Image not found at: {thumbnail_path_abs}")
            else:
                logger.warning(f"⚠️ No thumbnail_url in product")

            logger.info(f"🎨 Generating placeholder...")
            placeholder_path = ImageUtils.create_or_get_placeholder(
                product_title=product['title'],
                category=product.get('category', 'General'),
                product_id=product['product_id']
            )
            # Placeholder paths are already absolute
            return placeholder_path if placeholder_path else None
        else:
            logger.info(f"✅ Using stored image: {thumbnail_path_abs}")
            return thumbnail_path_abs

    def _build_product_keyboard(self, product: Dict, context: str, lang: str = 'fr',
                                 category_key: str = None, index: int = 0,
                                 total_products: int = 0, all_categories: List = None) -> InlineKeyboardMarkup:
        """
        Build product keyboard based on context

        Args:
            product: Product dict
            context: 'carousel' | 'details' | 'search' | 'reviews'
            lang: Language code
            category_key: Category key (for carousel navigation)
            index: Current product index (for carousel)
            total_products: Total products in category (for carousel)
            all_categories: List of all categories (for category navigation)

        Returns:
            InlineKeyboardMarkup
        """
        keyboard = []
        product_id = product['product_id']

        # Row 1: BIG BUY BUTTON EN VALEUR (CTA principal ultra-visible)
        if context == 'carousel' and category_key is not None and index is not None:
            buy_callback = f'buy_product_{product_id}_{category_key}_{index}'
        else:
            buy_callback = f'buy_product_{product_id}'

        # Utiliser la fonction helper réutilisable
        buy_label = self._build_buy_button_label(product['price_usd'], lang)

        keyboard.append([
            InlineKeyboardButton(buy_label, callback_data=buy_callback)
        ])

        if context == 'carousel':
            # Row 2: Product navigation (⬅️ 1/5 ➡️) - Asymétrique sans boutons vides
            nav_row = []

            # Ajouter flèche gauche SI pas au début
            if index > 0:
                nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'carousel_{category_key}_{index-1}'))

            # Toujours afficher compteur au centre
            nav_row.append(InlineKeyboardButton(
                f"{index+1}/{total_products}",
                callback_data='noop'
            ))

            # Ajouter flèche droite SI pas à la fin
            if index < total_products - 1:
                nav_row.append(InlineKeyboardButton("➡️", callback_data=f'carousel_{category_key}_{index+1}'))

            keyboard.append(nav_row)

            # Row 3: Détails (sans emoji superflu)
            keyboard.append([
                InlineKeyboardButton("Détails" if lang == 'fr' else "Details",
                                   callback_data=f'product_details_{product_id}_{category_key}_{index}')
            ])

            # Row 4: Category navigation - Asymétrique sans boutons vides
            if all_categories and len(all_categories) > 1:
                cat_nav_row = []

                # Trouver l'index de la catégorie actuelle (None si non trouvée)
                try:
                    current_cat_index = all_categories.index(category_key)
                except ValueError:
                    # Catégorie non trouvée dans la liste, on saute la navigation
                    current_cat_index = None

                if current_cat_index is not None:
                    # Flèche gauche SI pas première catégorie ET catégorie précédente a des produits
                    if current_cat_index > 0:
                        # Chercher la première catégorie précédente avec des produits
                        for i in range(current_cat_index - 1, -1, -1):
                            prev_cat = all_categories[i]
                            # Vérifier si cette catégorie a des produits
                            prev_cat_products = self.product_repo.get_products_by_category(prev_cat, limit=1, offset=0)
                            if prev_cat_products:
                                cat_nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'navcat_{prev_cat}'))
                                break

                    # Nom catégorie (tronqué si nécessaire)
                    cat_display = category_key
                    if len(cat_display) > 20:
                        cat_display = cat_display[:18] + "…"
                    cat_nav_row.append(InlineKeyboardButton(cat_display, callback_data='noop'))

                    # Flèche droite SI pas dernière catégorie ET catégorie suivante a des produits
                    if current_cat_index < len(all_categories) - 1:
                        # Chercher la première catégorie suivante avec des produits
                        for i in range(current_cat_index + 1, len(all_categories)):
                            next_cat = all_categories[i]
                            if next_cat and next_cat != category_key:
                                # Vérifier si cette catégorie a des produits
                                next_cat_products = self.product_repo.get_products_by_category(next_cat, limit=1, offset=0)
                                if next_cat_products:
                                    cat_nav_row.append(InlineKeyboardButton("➡️", callback_data=f'navcat_{next_cat}'))
                                    break

                    # N'ajouter la row que si elle contient au moins le nom de catégorie
                    if cat_nav_row:
                        keyboard.append(cat_nav_row)

            # Row 5: Accueil (sans emoji superflu)
            keyboard.append([
                InlineKeyboardButton("Accueil" if lang == 'fr' else "Home",
                                   callback_data='back_main')
            ])

        elif context == 'details':
            # Row 2: Avis + Preview
            # V2: Pass context to both buttons for closed circuit navigation
            if category_key and index is not None:
                preview_callback = f'product_preview_{product_id}_{category_key}_{index}'
                reviews_callback = f'reviews_{product_id}_0_{category_key}_{index}'
            else:
                preview_callback = f'product_preview_{product_id}'
                reviews_callback = f'reviews_{product_id}_0'

            keyboard.append([
                InlineKeyboardButton("Avis" if lang == 'fr' else "Reviews",
                                   callback_data=reviews_callback),
                InlineKeyboardButton("Aperçu" if lang == 'fr' else "Preview",
                                   callback_data=preview_callback)
            ])

            # Row 3: View seller shop
            seller_user_id = product.get('seller_user_id')
            if seller_user_id:
                keyboard.append([
                    InlineKeyboardButton("🏪 Boutique vendeur" if lang == 'fr' else "🏪 Seller shop",
                                       callback_data=f'seller_shop_{seller_user_id}')
                ])

            # Row 4: Réduire (back to carousel - V2 NEW FEATURE)
            if category_key is not None and index is not None:
                keyboard.append([
                    InlineKeyboardButton("Résumé" if lang == 'fr' else "Summary",
                                       callback_data=f'collapse_{product_id}_{category_key}_{index}')
                ])
                # Row 5: Précédent (back to carousel with context)
                keyboard.append([
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                       callback_data=f'carousel_{category_key}_{index}')
                ])
            else:
                # No context: back to main menu
                keyboard.append([
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                       callback_data='back_main')
                ])

        elif context == 'reviews':
            # Row 2: Précédent (back to details)
            keyboard.append([
                InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                   callback_data=f'product_details_{product_id}')
            ])

        elif context == 'search':
            # Simple layout for search results
            keyboard.append([
                InlineKeyboardButton("Détails" if lang == 'fr' else "Details",
                                   callback_data=f'product_details_{product_id}'),
                InlineKeyboardButton("Aperçu" if lang == 'fr' else "Preview",
                                   callback_data=f'product_preview_{product_id}')
            ])
            keyboard.append([
                InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                   callback_data='back_main')
            ])

        return InlineKeyboardMarkup(keyboard)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # END V2 HELPER FUNCTIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def buy_menu(self, bot, query, lang: str) -> None:
        """
        V2 WORKFLOW ÉTAPE 1: Click "Acheter" → DIRECT carousel (first category, first product)
        No intermediate menu, no category selection screen
        """
        # Reset conflicting states when entering buy workflow
        bot.reset_conflicting_states(query.from_user.id, keep={'lang'})

        # V2: Load first category and show carousel immediately
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Get first category (ordered by products_count DESC = most popular)
            cursor.execute('SELECT name FROM categories ORDER BY products_count DESC LIMIT 1')
            first_category = cursor.fetchone()
            conn.close()

            if first_category:
                category_name = first_category['name']
                # Show products in carousel for this category
                await self.show_category_products(bot, query, category_name, lang, page=0)
            else:
                # No categories = no products at all in marketplace
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                no_products_text = (
                    "🚧 **AUCUN PRODUIT DISPONIBLE**\n\n"
                    "La marketplace ne contient pas encore de produits.\n\n"
                    "💡 **SUGGESTIONS :**\n"
                    "• Revenir plus tard\n"
                    "• Devenir vendeur et ajouter vos produits"
                ) if lang == 'fr' else (
                    "🚧 **NO PRODUCTS AVAILABLE**\n\n"
                    "The marketplace does not contain any products yet.\n\n"
                    "💡 **SUGGESTIONS:**\n"
                    "• Come back later\n"
                    "• Become a seller and add your products"
                )

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        " Devenir vendeur" if lang == 'fr' else " Become a seller",
                        callback_data='sell_menu'
                    )],
                    [InlineKeyboardButton(
                        "Retour" if lang == 'fr' else "Back",
                        callback_data='back_main'
                    )]
                ])

                await query.edit_message_text(
                    text=no_products_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in buy_menu V2: {e}")
            await query.edit_message_text(
                "❌ Error loading products" if lang == 'en' else "❌ Erreur chargement produits",
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
                    [[InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                           callback_data='buy_menu')]]),
                parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(
                prompt_text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                           callback_data='buy_menu')]]),
                parse_mode='Markdown')

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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAYMENT TEXT BUILDERS (Centralized & Modifiable)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_crypto_selection_text(self, title: str, price_usd: float, lang: str = 'fr') -> str:
        """
        Génère le texte de sélection crypto avec prix et frais détaillés (Format HTML)
        Utilise settings.CRYPTO_DISPLAY_INFO pour centraliser les infos crypto

        Args:
            title: Titre du produit
            price_usd: Prix en euros
            lang: Langue (fr/en)

        Returns:
            Texte formaté pour la sélection crypto (HTML)
        """
        from app.core.settings import settings

        # Calcul des frais (2.78% de frais NowPayments)
        fees = round(price_usd * 0.0278, 2)
        total = round(price_usd + fees, 2)

        # Construire la liste des cryptos depuis settings.CRYPTO_DISPLAY_INFO
        crypto_lines = []
        priority_order = ['btc', 'eth', 'sol', 'usdc', 'usdt']  # Ordre d'affichage

        for crypto_code in priority_order:
            if crypto_code in settings.CRYPTO_DISPLAY_INFO:
                display_name, time_info = settings.CRYPTO_DISPLAY_INFO[crypto_code]
                # Extraire le nom sans emoji et le temps
                name_clean = display_name.split()[1] if ' ' in display_name else display_name
                time_clean = time_info.replace('⚡ ', '')

                crypto_lines.append(f"<b>{name_clean}</b> - {time_clean}")

        crypto_list_text = '\n'.join(crypto_lines)

        if lang == 'fr':
            return f""" <b>CHOISISSEZ VOTRE CRYPTO</b>

<b>{title}</b>

<b>Prix :</b> ${price_usd:.2f}
<b>Frais de gestion :</b> ${fees:.2f}
────────────────
<b>Total :</b> ${total:.2f}

<b>Délais de confirmation :</b>

{crypto_list_text}

────────────────
💡 <b>Recommandé : Solana</b> (le plus rapide)"""
        else:
            return f"""💳 <b>CHOOSE YOUR CRYPTO</b>

<b>{title}</b>

<b>Price:</b> ${price_usd:.2f}
<b>Processing fee:</b> ${fees:.2f}
────────────────
<b>Total:</b> ${total:.2f}

<b>Time for confirmation:</b>

{crypto_list_text}

────────────────
💡 <b>Recommended: Solana</b> (fastest)"""

    def _build_payment_confirmation_text(self, title: str, price_usd: float,
                                         exact_amount: str, crypto_code: str, payment_address: str,
                                         order_id: str, network: str = None, lang: str = 'fr') -> str:
        """
        Génère le texte de confirmation de paiement avec adresse et montant exact (Format HTML)

        Args:
            title: Titre du produit
            price_usd: Prix en USD
            exact_amount: Montant exact en crypto
            crypto_code: Code de la crypto (BTC, ETH, SOL, etc.)
            payment_address: Adresse de paiement
            order_id: ID de commande
            network: Réseau optionnel
            lang: Langue (fr/en)

        Returns:
            Texte formaté pour la confirmation de paiement (HTML)
        """
        crypto_upper = crypto_code.upper()
        network_display = network or crypto_upper

        # Calcul des frais (2.78%)
        fees = round(price_usd * 0.0278, 2)
        total_usd = round(price_usd + fees, 2)

        if lang == 'fr':
            return f"""<b>{title}</b>
Prix total : <b>${total_usd:.2f}</b>
<i>Frais inclus</i>

<b>Envoyez EXACTEMENT :</b>
<code>{exact_amount} {crypto_upper}</code>

<b>ADRESSE DE PAIEMENT {network_display} :</b>
<code>{payment_address}</code>

<b>Order ID :</b> <code>{order_id}</code>

<b>⚠️ IMPORTANT</b>
• Le paiement expire dans <b>1 heure</b>
• Vous recevrez un email de confirmation automatique

<b>❓ BESOIN D'AIDE ?</b>
Contactez le support avec votre Order ID"""
        else:
            return f"""<b>{title}</b>
Total Price: <b>${total_usd:.2f}</b>
<i>Fees included</i>

<b>Send EXACTLY:</b>
<code>{exact_amount} {crypto_upper}</code>

<b>{network_display} PAYMENT ADDRESS:</b>
<code>{payment_address}</code>

<b>Order ID:</b> <code>{order_id}</code>

<b>⚠️ IMPORTANT</b>
• Payment expires in <b>1 hour</b>
• You will receive an automatic confirmation email

<b>❓ NEED HELP?</b>
Contact support with your Order ID"""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # V2 NEW FEATURES (Spec Section 8: Missing Functionality)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def show_product_reviews(self, bot, query, product_id: str, page: int = 0, lang: str = 'fr', category_key: str = None, index: int = None) -> None:
        """
        V2 SPEC - VARIANTE 1B: Display product reviews page with pagination

        Args:
            bot: Bot instance
            query: CallbackQuery
            product_id: Product ID
            page: Page number (0-indexed, 5 reviews per page)
            lang: Language code
            category_key: Optional category for maintaining closed circuit
            index: Optional product index for maintaining closed circuit
        """
        try:
            if not self.review_repo:
                await safe_transition_to_text(
                    query,
                    "❌ Service d'avis temporairement indisponible" if lang == 'fr' else "❌ Reviews service temporarily unavailable",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                           callback_data=f'product_details_{product_id}')
                    ]])
                )
                return

            # Get product for context
            product = bot.get_product_by_id(product_id)
            if not product:
                await safe_transition_to_text(query, i18n(lang, 'err_product_not_found'))
                return

            # Get reviews (5 per page)
            reviews_per_page = 5
            reviews = self.review_repo.get_product_reviews(product_id, limit=reviews_per_page, offset=page * reviews_per_page)
            total_reviews = product.get('reviews_count', 0)
            avg_rating = product.get('rating', 0.0)

            # Build message - Format simplifié
            text = f"**⭐ AVIS CLIENTS**\n\n"
            text += f"**{product['title']}**\n"

            # Rating summary
            if total_reviews > 0:
                text += f"⭐ **{avg_rating:.1f}/5** ({total_reviews})\n\n"
            else:
                text += "⭐ Aucun avis\n\n"
                text += ("Soyez le premier à donner votre avis après l'achat!\n\n"
                        if lang == 'fr' else "Be the first to review after purchase!\n\n")

            # Display reviews
            if reviews:
                from datetime import datetime

                for review in reviews:
                    text += "─────────────────────\n"

                    # User info
                    buyer_name = review.get('buyer_first_name', 'Acheteur')
                    if len(buyer_name) > 20:
                        buyer_name = buyer_name[:18] + "..."
                    text += f"👤 **{buyer_name}**\n"

                    # Rating stars
                    stars = "⭐" * review['rating']
                    text += f"{stars} {review['rating']}/5\n"

                    # Review text
                    review_text = review.get('review_text') or review.get('comment') or ""
                    if review_text:
                        # Limit to 150 chars per review for readability
                        if len(review_text) > 150:
                            review_text = review_text[:147] + "..."
                        text += f"{review_text}\n"

                    # Time ago
                    created_at = review.get('created_at')
                    if created_at:
                        try:
                            if isinstance(created_at, str):
                                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            else:
                                created_date = created_at

                            days_ago = (datetime.now() - created_date).days
                            if days_ago == 0:
                                time_text = "Aujourd'hui" if lang == 'fr' else "Today"
                            elif days_ago == 1:
                                time_text = "Hier" if lang == 'fr' else "Yesterday"
                            elif days_ago < 7:
                                time_text = f"Il y a {days_ago}j" if lang == 'fr' else f"{days_ago}d ago"
                            elif days_ago < 30:
                                weeks = days_ago // 7
                                time_text = f"Il y a {weeks}sem" if lang == 'fr' else f"{weeks}w ago"
                            else:
                                months = days_ago // 30
                                time_text = f"Il y a {months}mois" if lang == 'fr' else f"{months}m ago"

                            text += f"🕒 {time_text}\n"
                        except:
                            pass

                    text += "\n"

            # Build keyboard
            keyboard = []

            # Row 1: BUY BUTTON (always accessible - V2 SPEC)
            # Pass context to maintain closed circuit
            if category_key and index is not None:
                buy_callback = f'buy_product_{product_id}_{category_key}_{index}'
            else:
                buy_callback = f'buy_product_{product_id}'

            keyboard.append([
                InlineKeyboardButton(
                    f"💳 ACHETER - {product['price_usd']}€ 💳" if lang == 'fr' else f"💳 BUY - {product['price_usd']}€ 💳",
                    callback_data=buy_callback
                )
            ])

            # Row 2: Pagination (if needed) - Asymétrique sans boutons vides
            if total_reviews > reviews_per_page:
                nav_row = []
                total_pages = (total_reviews + reviews_per_page - 1) // reviews_per_page

                # Build pagination callbacks with context
                if category_key and index is not None:
                    prev_callback = f'reviews_{product_id}_{page-1}_{category_key}_{index}'
                    next_callback = f'reviews_{product_id}_{page+1}_{category_key}_{index}'
                else:
                    prev_callback = f'reviews_{product_id}_{page-1}'
                    next_callback = f'reviews_{product_id}_{page+1}'

                # Ajouter flèche gauche SI pas première page
                if page > 0:
                    nav_row.append(InlineKeyboardButton("⬅️", callback_data=prev_callback))

                # Toujours afficher compteur au centre
                nav_row.append(InlineKeyboardButton(
                    f"{page+1}/{total_pages}",
                    callback_data='noop'
                ))

                # Ajouter flèche droite SI pas dernière page
                if page < total_pages - 1:
                    nav_row.append(InlineKeyboardButton("➡️", callback_data=next_callback))

                keyboard.append(nav_row)

            # Row 3: Back to details (with context for closed circuit)
            if category_key and index is not None:
                back_callback = f'product_details_{product_id}_{category_key}_{index}'
            else:
                back_callback = f'product_details_{product_id}'

            keyboard.append([
                InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                   callback_data=back_callback)
            ])

            # Transition from photo message (details page) to text
            await safe_transition_to_text(query, text, InlineKeyboardMarkup(keyboard))

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error showing product reviews: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await safe_transition_to_text(
                query,
                "❌ Erreur lors du chargement des avis" if lang == 'fr' else "❌ Error loading reviews",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                       callback_data=f'product_details_{product_id}')
                ]])
            )

    async def collapse_product_details(self, bot, query, product_id: str, category_key: str, index: int, lang: str = 'fr') -> None:
        """
        V2 SPEC - NEW FEATURE: Collapse details back to carousel (short card)

        Args:
            bot: Bot instance
            query: CallbackQuery
            product_id: Product ID
            category_key: Category key
            index: Product index in category
            lang: Language code
        """
        try:
            # Get all products in category
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT * FROM products
                WHERE category = %s AND status = 'active'
                ORDER BY created_at DESC
            ''', (category_key,))

            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            conn.close()

            products = []
            for row in rows:
                product_dict = dict(zip(columns, row))
                products.append(product_dict)

            if not products:
                await safe_transition_to_text(query, "❌ No products found" if lang == 'en' else "❌ Aucun produit trouvé")
                return

            # Show carousel at saved index
            await self.show_product_carousel(bot, query, category_key, products, index, lang)

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error collapsing details: {e}")
            await safe_transition_to_text(
                query,
                "❌ Erreur" if lang == 'fr' else "❌ Error",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                       callback_data='back_main')
                ]])
            )

    async def navigate_categories(self, bot, query, target_category: str, lang: str = 'fr') -> None:
        """
        V2 SPEC - NEW FEATURE: Navigate between categories (← Category →)

        Args:
            bot: Bot instance
            query: CallbackQuery
            target_category: Target category name
            lang: Language code
        """
        try:
            # Show first product of target category
            await self.show_category_products(bot, query, target_category, lang, page=0)

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error navigating categories: {e}")
            await safe_transition_to_text(
                query,
                "❌ Erreur de navigation" if lang == 'fr' else "❌ Navigation error",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back",
                                       callback_data='back_main')
                ]])
            )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # END V2 NEW FEATURES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def show_product_carousel(self, bot, query, category_key: str, products: List[Dict], index: int = 0, lang: str = 'fr') -> None:
        """
        V2 WORKFLOW - ÉTAPE 1: Card Produit (version courte)
        Carousel navigation with ⬅️ ➡️ buttons + category navigation
        UX Type: Instagram Stories / Amazon Product Slider
        """
        from app.integrations.telegram.utils.carousel_helper import CarouselHelper

        # Caption builder for buy carousel
        def build_caption(product, lang):
            return self._build_product_caption(product, mode='short', lang=lang)

        # Keyboard builder for buy carousel
        def build_keyboard(product, index, total, lang):
            # Get all categories for navigation
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT name FROM categories ORDER BY products_count DESC')
            all_categories = [row['name'] for row in cursor.fetchall()]
            conn.close()

            # Use existing helper
            keyboard_markup = self._build_product_keyboard(
                product,
                context='carousel',
                lang=lang,
                category_key=category_key,
                index=index,
                total_products=total,
                all_categories=all_categories
            )
            return keyboard_markup.inline_keyboard  # Return keyboard rows

        # Use carousel helper (eliminates duplication)
        await CarouselHelper.show_carousel(
            query=query,
            bot=bot,
            products=products,
            index=index,
            caption_builder=build_caption,
            keyboard_builder=build_keyboard,
            lang=lang,
            parse_mode='HTML'
        )

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

                # Delete message and send new one (avoids edit_message_text on photo messages)
                try:
                    await query.message.delete()
                except:
                    pass  # Ignore if can't delete

                await query.message.reply_text(
                    text=error_data['text'],
                    reply_markup=error_data['keyboard'],
                    parse_mode='Markdown'
                )
                return

            # Launch carousel mode starting at index 0
            await self.show_product_carousel(bot, query, category_key, products, index=0, lang=lang)

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error showing category products: {e}")
            # Use user-friendly error message
            error_data = get_error_message('product_load_error', lang)

            # Delete message and send new one (avoids edit_message_text on photo messages)
            try:
                await query.message.delete()
            except:
                pass  # Ignore if can't delete

            await query.message.reply_text(
                text=error_data['text'],
                reply_markup=error_data['keyboard'],
                parse_mode='Markdown'
            )

    async def show_product_details(self, bot, query, product_id: str, lang: str, category_key: str = None, index: int = None) -> None:
        """
        V2 WORKFLOW - VARIANTE 1A: Card Détails (version longue)

        Args:
            bot: Bot instance
            query: CallbackQuery
            product_id: Product ID
            lang: Language code
            category_key: Optional category key for "Réduire" button context
            index: Optional product index for "Réduire" button context
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
                                         callback_data='back_main')
                ]]),
                parse_mode='Markdown')
            return

        self.product_repo.increment_views(product_id)

        # V2: Display full details with helper functions
        await self._show_product_visual_v2(bot, query, product, lang, category_key, index)

    async def _show_product_visual_v2(self, bot, query, product: dict, lang: str, category_key: str = None, index: int = None):
        """
        V2: Visual product display with FULL description + V2 features
        Uses helper functions + supports "Réduire" button with context
        """
        from telegram import InputMediaPhoto
        import os

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # V2: USE HELPER FUNCTIONS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        # Build caption with FULL description (mode='full')
        caption = self._build_product_caption(product, mode='full', lang=lang)

        # Get image or placeholder
        thumbnail_path = self._get_product_image_or_placeholder(product)

        # Build keyboard using helper with 'details' context
        # This will include: ACHETER, Avis, Preview, Réduire (if context provided), Précédent
        keyboard_markup = self._build_product_keyboard(
            product,
            context='details',
            lang=lang,
            category_key=category_key,
            index=index
        )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # DISPLAY
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                with open(thumbnail_path, 'rb') as photo_file:
                    await query.edit_message_media(
                        media=InputMediaPhoto(
                            media=photo_file,
                            caption=caption,
                            parse_mode='HTML'
                        ),
                        reply_markup=keyboard_markup
                    )
            else:
                # Fallback to text only if image completely fails
                await query.edit_message_text(
                    caption,
                    reply_markup=keyboard_markup,
                    parse_mode='HTML'
                )
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error displaying product details V2: {e}")
            # Final fallback
            await query.edit_message_text(
                caption,
                reply_markup=keyboard_markup,
                parse_mode='HTML'
            )

    async def process_product_search(self, bot, update, message_text):
        """Traite la recherche de produit par ID OU texte libre"""
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)
        lang = user_state.get('lang', 'fr')

        search_input = message_text.strip()

        # Reset state
        if user_id in bot.state_manager.user_states:
            state = bot.state_manager.get_state(user_id)
            for k in ['waiting_for_product_id']:
                state.pop(k, None)
            bot.state_manager.update_state(user_id, **state)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STRATÉGIE 1: Essayer recherche par ID (si ressemble à un ID)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        product_id_upper = search_input.upper()

        # Si ça ressemble à un ID (format TBF-XXX ou contient des tirets)
        if 'TBF-' in product_id_upper or '-' in search_input:
            product = bot.get_product_by_id(product_id_upper)
            if product:
                logger.info(f"✅ Product found by ID: {product_id_upper}")
                await self.show_product_details_from_search(bot, update, product)
                return

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STRATÉGIE 2: Recherche textuelle (titre + description)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        logger.info(f"🔍 Text search for: {search_input}")
        results = self.product_repo.search_products(search_input, limit=10)

        if results:
            logger.info(f"✅ Found {len(results)} products matching '{search_input}'")
            await self.show_search_results(bot, update, results, search_input, index=0, lang=lang)
        else:
            # Aucun résultat
            no_results_text = (
                f"🔍 **Aucun résultat pour :** `{search_input}`\n\n"
                "💡 **Essayez :**\n"
                "• Des mots-clés plus courts\n"
                "• Rechercher par ID produit (ex: TBF-123...)\n"
                "• Parcourir les catégories"
            ) if lang == 'fr' else (
                f"🔍 **No results for:** `{search_input}`\n\n"
                "💡 **Try:**\n"
                "• Shorter keywords\n"
                "• Search by product ID (e.g. TBF-123...)\n"
                "• Browse categories"
            )

            await update.message.reply_text(
                no_results_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 Retour" if lang == 'fr' else "🔙 Back",
                        callback_data='buy_menu'
                    )]
                ]),
                parse_mode='Markdown'
            )

    async def show_search_results(self, bot, update, results, search_query, index=0, lang='fr'):
        """
        Affiche les résultats de recherche textuelle en carousel

        Args:
            bot: Bot instance
            update: Telegram update
            results: Liste des produits trouvés
            search_query: Requête de recherche
            index: Index du produit affiché
            lang: Langue
        """
        if not results:
            return

        product = results[index]
        total = len(results)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # CAPTION en mode 'short' (compact pour carousel)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        caption = self._build_product_caption(product, mode='short', lang=lang)

        # Ajouter header recherche
        search_header = (
            f"🔍 Recherche: <b>{search_query}</b>\n"
            f"📊 {total} résultat{'s' if total > 1 else ''}\n\n"
        ) if lang == 'fr' else (
            f"🔍 Search: <b>{search_query}</b>\n"
            f"📊 {total} result{'s' if total > 1 else ''}\n\n"
        )

        caption_with_header = search_header + caption

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # IMAGE
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        thumbnail_path = self._get_product_image_or_placeholder(product)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KEYBOARD avec navigation carousel
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        keyboard = []

        # Ligne 1: Bouton Acheter (en premier comme recherche par ID)
        buy_label = self._build_buy_button_label(product['price_usd'], lang)
        keyboard.append([
            InlineKeyboardButton(
                buy_label,
                callback_data=f'buy_product_{product["product_id"]}'
            )
        ])

        # Ligne 2: Navigation carousel
        nav_row = []

        # Bouton précédent (seulement si pas au début)
        if index > 0:
            nav_row.append(InlineKeyboardButton(
                "⬅️",
                callback_data=f'search_nav_{search_query}_{index-1}'
            ))

        # Position
        nav_row.append(InlineKeyboardButton(
            f"{index + 1}/{total}",
            callback_data='noop'
        ))

        # Bouton suivant (seulement si pas à la fin)
        if index < total - 1:
            nav_row.append(InlineKeyboardButton(
                "➡️",
                callback_data=f'search_nav_{search_query}_{index+1}'
            ))

        keyboard.append(nav_row)

        # Ligne 3: Retour
        keyboard.append([
            InlineKeyboardButton(
                "🔙 Nouvelle recherche" if lang == 'fr' else "🔙 New search",
                callback_data='buy_menu'
            )
        ])

        keyboard_markup = InlineKeyboardMarkup(keyboard)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # DISPLAY
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if thumbnail_path and os.path.exists(thumbnail_path):
            await update.message.reply_photo(
                photo=open(thumbnail_path, 'rb'),
                caption=caption_with_header,
                reply_markup=keyboard_markup,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                caption_with_header,
                reply_markup=keyboard_markup,
                parse_mode='HTML'
            )

    async def show_product_details_from_search(self, bot, update, product):
        """Affiche les détails d'un produit trouvé par recherche - STRUCTURE IDENTIQUE À MODE 'FULL'"""
        user_id = update.effective_user.id
        user_data = bot.user_repo.get_user(user_id)
        lang = user_data['language_code'] if user_data else 'fr'

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # CAPTION : Utiliser la fonction unifiée en mode 'full'
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        caption = self._build_product_caption(product, mode='full', lang=lang)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # IMAGE : Utiliser la fonction unifiée
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        thumbnail_path = self._get_product_image_or_placeholder(product)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # KEYBOARD : Utiliser la fonction unifiée avec contexte 'search'
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        keyboard_markup = self._build_product_keyboard(
            product,
            context='search',  # Contexte spécifique pour recherche
            lang=lang
        )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # DISPLAY : Envoyer avec image ou texte
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=caption,
                    reply_markup=keyboard_markup,
                    parse_mode='HTML'  # Mode 'full' utilise HTML
                )
        else:
            # Fallback to text only if image completely fails
            await update.message.reply_text(
                caption,
                reply_markup=keyboard_markup,
                parse_mode='HTML'
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
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error updating message: {e}")
            # Fallback: send new message
            await query.message.reply_text("🔍 Vérification en cours...")

        conn = bot.get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT * FROM orders WHERE order_id = %s', (order_id, ))
            order = cursor.fetchone()
        except (psycopg2.Error, Exception) as e:
            conn.close()
            return

        if not order:
            await query.edit_message_text("❌ Commande introuvable!")
            return
        logger.info(order)
        payment_id = order[7]

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
                        WHERE order_id = %s
                    ''', (order_id, ))

                    cursor.execute(
                        '''
                        UPDATE products
                        SET sales_count = sales_count + 1
                        WHERE product_id = %s
                    ''', (order[3], ))

                    cursor.execute(
                        '''
                        UPDATE users
                        SET total_sales = total_sales + 1,
                            total_revenue = total_revenue + %s
                        WHERE user_id = %s
                    ''', (order[7], order[4]))

                    # Partner commission removed - referral system deleted

                    conn.commit()
                except (psycopg2.Error, Exception) as e:
                    conn.rollback()
                    conn.close()
                    return

                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 📢 NOTIFICATION VENDEUR : Paiement confirmé
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                try:
                    # Get product data and buyer info for notification
                    cursor.execute('SELECT * FROM products WHERE product_id = %s', (order[3],))
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
                            amount_eur=order[7],  # price_usd
                            crypto_code=order[8],  # payment_currency
                            tx_hash=payment_status.get('payment_hash')
                        )
                        logger.info(f"✅ Seller notification sent for order {order_id}")
                except Exception as notif_error:
                    logger.error(f"❌ Failed to send seller notification: {notif_error}")
                    # Don't fail the payment if notification fails

                try:
                    payout_created = await bot.auto_create_seller_payout(order_id)
                except (psycopg2.Error, Exception) as e:
                    payout_created = False

                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # 📦 ENVOI AUTOMATIQUE DU FICHIER
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                file_sent = False
                try:
                    # Check if file was already delivered (by IPN webhook)
                    cursor.execute('SELECT file_delivered FROM orders WHERE order_id = %s', (order_id,))
                    already_delivered = cursor.fetchone()

                    if already_delivered and already_delivered[0]:
                        logger.info(f"File already delivered for order {order_id} (likely by IPN webhook)")
                        file_sent = True  # Mark as sent so we show correct message
                    else:
                        # Get product file URL (from B2)
                        cursor.execute('SELECT title, main_file_url FROM products WHERE product_id = %s', (order[3],))
                        product_file = cursor.fetchone()

                        if product_file and product_file[1]:
                            product_title, file_url = product_file

                            # Send success message first
                            success_text = f"""🎉 **FÉLICITATIONS !**

✅ **Paiement confirmé** - Commande : {order_id}
{"✅ Payout vendeur créé automatiquement" if payout_created else "⚠️ Payout vendeur en attente"}

📚 **Envoi de votre formation en cours...**"""

                            await self._safe_edit_message(query, success_text, None)

                            # Download file from B2 and send it
                            try:
                                from app.core.file_utils import download_product_file_from_b2

                                # Download from B2 to temp location
                                local_path = await download_product_file_from_b2(file_url, order[3])

                                if local_path and os.path.exists(local_path):
                                    # Send the file
                                    with open(local_path, 'rb') as file:
                                        await query.message.reply_document(
                                            document=file,
                                            caption=f"📚 **{product_title}**\n\n✅ Téléchargement réussi !\n\n💡 Conservez ce fichier précieusement.",
                                            parse_mode='Markdown'
                                        )
                                        file_sent = True

                                        # Mark as delivered and update download count
                                        cursor.execute('''UPDATE orders
                                                         SET file_delivered = TRUE,
                                                             download_count = download_count + 1
                                                         WHERE order_id = %s''', (order_id,))
                                        conn.commit()

                                        logger.info(f"✅ Formation sent via manual check to user {query.from_user.id} for order {order_id}")

                                    # Clean up temp file
                                    try:
                                        os.remove(local_path)
                                        logger.info(f"🗑️ Temp file cleaned up: {local_path}")
                                    except Exception as cleanup_error:
                                        logger.warning(f"⚠️ Could not clean up temp file: {cleanup_error}")
                                else:
                                    logger.error(f"❌ Failed to download file from B2: {file_url}")
                            except FileNotFoundError:
                                logger.error(f"File not found after B2 download")
                            except Exception as file_error:
                                logger.error(f"Error downloading/sending file from B2: {file_error}")
                except Exception as delivery_error:
                    logger.error(f"Error in automatic file delivery: {delivery_error}")
                finally:
                    conn.close()

                # Send final confirmation with buttons
                final_text = f"""🎉 **FÉLICITATIONS !**

✅ **Paiement confirmé** - Commande : {order_id}
{"✅ Payout vendeur créé automatiquement" if payout_created else "⚠️ Payout vendeur en attente"}

{"📚 **Votre formation a été envoyée ci-dessus !**" if file_sent else "📚 **ACCÈS À VOTRE FORMATION**"}"""

                keyboard = [[
                    InlineKeyboardButton(
                        "📥 Télécharger à nouveau" if file_sent else "📥 Télécharger maintenant",
                        callback_data=f'download_product_{order[3]}')
                ], [
                    InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')
                ]]

                await query.message.reply_text(final_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
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

    async def buy_product(self, bot, query, product_id: str, lang: str, category_key: str = None, index: int = None):
        """
        Show crypto selection for product purchase

        Args:
            category_key: Optional category for "Précédent" button context
            index: Optional product index for "Précédent" button context
        """
        try:
            # Get product details
            product = bot.get_product_by_id(product_id)
            if not product:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='back_main')
                ]])
                await safe_transition_to_text(query, i18n(lang, 'err_product_not_found'), keyboard)
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
                        "Retour" if lang == 'fr' else "Back",
                        callback_data=f'product_{product_id}'
                    )]
                ])

                # Gérer transition depuis carousel (message avec photo)
                await safe_transition_to_text(query, already_owned_text, keyboard)
                return

            # Show crypto selection menu
            title = product.get('title', 'Produit')
            price_usd = product.get('price_usd', 0)

            # Utiliser la fonction centralisée de génération de texte
            text = self._build_crypto_selection_text(title, price_usd, lang)

            # V2 SPEC: Layout crypto en grille 2x2 + 1 (ÉTAPE 2)
            keyboard = []
            from app.core.settings import settings

            # Get crypto list
            crypto_list = list(settings.CRYPTO_DISPLAY_INFO.items())

            # Row 1: BTC + ETH (most popular)
            if len(crypto_list) >= 2:
                row1 = []
                # BTC
                if 'btc' in settings.CRYPTO_DISPLAY_INFO:
                    display_name, time_info = settings.CRYPTO_DISPLAY_INFO['btc']
                    row1.append(InlineKeyboardButton(
                        " BTC",
                        callback_data=f'pay_crypto_btc_{product_id}'
                    ))
                # ETH
                if 'eth' in settings.CRYPTO_DISPLAY_INFO:
                    display_name, time_info = settings.CRYPTO_DISPLAY_INFO['eth']
                    row1.append(InlineKeyboardButton(
                        " ETH",
                        callback_data=f'pay_crypto_eth_{product_id}'
                    ))
                if row1:
                    keyboard.append(row1)

            # Row 2: SOLANA (full width - fastest)
            if 'sol' in settings.CRYPTO_DISPLAY_INFO:
                display_name, time_info = settings.CRYPTO_DISPLAY_INFO['sol']
                keyboard.append([InlineKeyboardButton(
                    f" SOLANA {time_info}",
                    callback_data=f'pay_crypto_sol_{product_id}'
                )])

            # Row 3: USDC + USDT (stablecoins)
            row3 = []
            if 'usdc' in settings.CRYPTO_DISPLAY_INFO:
                row3.append(InlineKeyboardButton(
                    " USDC",
                    callback_data=f'pay_crypto_usdc_{product_id}'
                ))
            if 'usdt' in settings.CRYPTO_DISPLAY_INFO:
                row3.append(InlineKeyboardButton(
                    "₮ USDT",
                    callback_data=f'pay_crypto_usdt_{product_id}'
                ))
            if row3:
                keyboard.append(row3)

            # Row 4: Back button
            # V2: Return to carousel (short) if context available, otherwise to details
            if category_key and index is not None:
                back_callback = f'collapse_{product_id}_{category_key}_{index}'
            else:
                back_callback = f'product_{product_id}'

            keyboard.append([InlineKeyboardButton(
                "Retour" if lang == 'fr' else "Back",
                callback_data=back_callback
            )])

            # Gérer transition depuis carousel (message avec photo) - HTML pour bold
            await safe_transition_to_text(query, text, InlineKeyboardMarkup(keyboard), parse_mode='HTML')

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error buying product: {e}")
            keyboard_error = InlineKeyboardMarkup([[
                InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='back_main')
            ]])
            await safe_transition_to_text(query, i18n(lang, 'err_purchase_error'), keyboard_error)

    async def process_crypto_payment(self, bot, query, crypto_code: str, product_id: str, lang: str):
        """Create payment with selected crypto using NowPayments"""
        try:
            # Get product details
            product = bot.get_product_by_id(product_id)
            if not product:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='back_main')
                ]])
                await safe_transition_to_text(query, i18n(lang, 'err_product_not_found'), keyboard)
                return

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # LOADING STATE (création paiement NowPayments peut prendre 2-3s)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                await safe_transition_to_text(
                    query,
                    "🔄 Création du paiement en cours..." if lang == 'fr' else "🔄 Creating payment..."
                )
            except:
                pass

            user_id = query.from_user.id
            title = product.get('title', 'Produit')
            price_usd = product.get('price_usd', 0)

            # Calculate total with platform fees (2.78%)
            platform_fee = round(price_usd * 0.0278, 2)
            total_amount = round(price_usd + platform_fee, 2)

            # Create order in database
            order_id = f"TBO-{user_id}-{int(time.time())}"

            # Create NowPayments payment with enhanced data (buyer pays total with fees)
            payment_data = self.payment_service.create_payment(
                amount_usd=total_amount,
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
            from app.core.database_init import get_postgresql_connection

            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                INSERT INTO orders (order_id, buyer_user_id, seller_user_id, product_id,
                                  product_title, product_price_usd, payment_id, payment_currency,
                                  payment_status, created_at, nowpayments_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            ''', (order_id, user_id, product.get('seller_user_id'), product_id, title,
                  price_usd, payment_data.get('payment_id'), crypto_code, 'waiting',
                  payment_data.get('payment_id')))
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
                    amount_eur=price_usd,
                    crypto_code=crypto_code
                )
                logger.info(f"✅ New purchase notification sent to seller for order {order_id}")
            except Exception as notif_error:
                logger.error(f"❌ Failed to send new purchase notification: {notif_error}")
                # Don't fail the purchase if notification fails

            # Display comprehensive payment info with QR code
            await self._display_payment_details(query, payment_data, title, price_usd, order_id, product_id, crypto_code, lang)

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error processing crypto payment: {e}")
            await query.edit_message_text(
                i18n(lang, 'err_payment_creation'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data=f'buy_product_{product_id}')
                ]])
            )

    async def preview_product(self, query, product_id: str, lang: str, category_key: str = None, index: int = None):
        """
        Show product preview (PDF first page, video thumbnail, etc.)

        Args:
            category_key: Optional category for "Précédent" button context
            index: Optional product index for "Précédent" button context
        """
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

        safe_title = escape_markdown(str(product.get('title') or ''))

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

                                # Delete original message first
                                try:
                                    await query.delete_message()
                                except:
                                    pass

                                # Send PDF preview (no caption)
                                await query.message.reply_photo(photo=bio)
                                doc.close()
                                logger.info(f"[PDF Preview] Preview sent successfully!")
                                media_preview_sent = True
                            else:
                                logger.warning(f"[PDF Preview] PDF has no pages")
                        except (psycopg2.Error, Exception) as e:
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

                                # Delete original message
                                try:
                                    await query.delete_message()
                                except:
                                    pass

                                # Send thumbnail (no caption)
                                with open(thumbnail_path, 'rb') as thumb_file:
                                    await query.message.reply_photo(photo=thumb_file)

                                # Cleanup
                                os.remove(thumbnail_path)
                                logger.info(f"[Video Preview] Thumbnail sent successfully!")
                                media_preview_sent = True
                            else:
                                logger.warning(f"[Video Preview] Thumbnail not generated")
                        except (psycopg2.Error, Exception) as e:
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

                            # Delete original message
                            try:
                                await query.delete_message()
                            except:
                                pass

                            # Send archive preview (no text - archive previews will just show buttons)
                            logger.info(f"[Archive Preview] Preview sent successfully!")
                            media_preview_sent = True
                        except (psycopg2.Error, Exception) as e:
                            logger.error(f"[Archive Preview] Error: {e}")
                else:
                    logger.warning(f"[Preview] File does not exist: {full_path}")
        except (psycopg2.Error, Exception) as e:
            logger.error(f"[Preview] General error: {e}")

        # Delete message if no media preview was sent
        if not media_preview_sent:
            try:
                await query.delete_message()
            except:
                pass

        # Now send action buttons AFTER the preview content (at the bottom, easy to access)
        # V2: Include context for closed circuit Preview → Précédent → Details (with context) → Réduire → Carousel
        from app.core.i18n import t as i18n

        if category_key and index is not None:
            buy_callback = f'buy_product_{product_id}_{category_key}_{index}'
            back_callback = f'product_details_{product_id}_{category_key}_{index}'
        else:
            buy_callback = f'buy_product_{product_id}'
            back_callback = f'product_{product_id}'

        # Utiliser la fonction helper réutilisable
        buy_label = self._build_buy_button_label(product['price_usd'], lang)

        keyboard = [
            [InlineKeyboardButton(buy_label, callback_data=buy_callback)],
            [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data=back_callback)]
        ]

        # Send buttons without text
        await query.message.reply_text(
            ".",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def mark_as_paid(self, bot, query, product_id: str, lang: str):
        """Mark order as paid (test functionality)"""
        try:
            user_id = query.from_user.id

            # Create mock order in database
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Insert order
            order_id = f"ord_{user_id}_{product_id}_{int(datetime.now().timestamp())}"
            cursor.execute('''
                INSERT INTO orders
                (order_id, buyer_user_id, product_id, payment_status, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
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
                    [back_to_main_button(lang)]
                ]),
                parse_mode='Markdown'
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error marking as paid: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de la confirmation du paiement." if lang == 'fr' else "❌ Payment confirmation error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back", callback_data='back_main')
                ]])
            )

    async def _display_payment_details(self, query, payment_data, title, price_usd, order_id, product_id, crypto_code, lang):
        """Display comprehensive payment details with QR code and exact amounts"""
        try:
            # Get payment details
            payment_details = payment_data.get('payment_details', {})
            payment_address = payment_details.get('address') or payment_data.get('pay_address', '')
            exact_amount = payment_details.get('amount') or payment_data.get('exact_crypto_amount')
            formatted_amount = payment_data.get('formatted_amount', f"{exact_amount:.8f}" if exact_amount else "N/A")
            network = payment_details.get('network', crypto_code.upper())
            qr_code = payment_data.get('qr_code')

            # Utiliser la fonction centralisée de génération de texte
            text = self._build_payment_confirmation_text(
                title=title,
                price_usd=price_usd,
                exact_amount=formatted_amount,
                crypto_code=crypto_code,
                payment_address=payment_address,
                order_id=order_id,
                network=network,
                lang=lang
            )

            # Boutons bilingues
            refresh_label = "🔄 Actualiser statut" if lang == 'fr' else "🔄 Refresh status"
            preview_label = "👁️ Aperçu" if lang == 'fr' else "👁️ Preview"
            back_label = "🔙 Retour" if lang == 'fr' else "🔙 Back"

            keyboard = [
                [InlineKeyboardButton(refresh_label, callback_data=f'refresh_payment_{order_id}')],
                [InlineKeyboardButton(preview_label, callback_data=f'preview_product_{product_id}')],
                [InlineKeyboardButton(back_label, callback_data=f'buy_product_{product_id}')]
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
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )

                    return

                except (psycopg2.Error, Exception) as e:
                    logger.error(f"Error sending QR code: {e}")
                    # Fall back to text-only message

            # Fallback: send text-only message
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error displaying payment details: {e}")
            # Basic fallback message
            await query.edit_message_text(
                f"💳 Payment created for order `{order_id}`\n\nAddress: `{payment_address}`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Retour / Back", callback_data=f'buy_product_{product_id}')
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
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in _safe_edit_message: {e}")
            # Fallback: send new message
            try:
                await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as fallback_error:
                logger.error(f"Fallback message failed: {fallback_error}")

    async def show_seller_shop(self, bot, query, seller_user_id: int, lang: str = 'fr') -> None:
        """
        Show all products from a specific seller in a carousel view

        Args:
            bot: Bot instance
            query: CallbackQuery
            seller_user_id: Seller's user ID
            lang: Language code
        """
        from app.domain.repositories.user_repo import UserRepository

        # Get seller info
        user_repo = UserRepository()
        seller = user_repo.get_user(seller_user_id)

        if not seller:
            await query.edit_message_text(
                "❌ Vendeur introuvable" if lang == 'fr' else "❌ Seller not found",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back", callback_data='back_main')
                ]])
            )
            return

        # Get all products from this seller
        products = self.product_repo.get_products_by_seller(seller_user_id)
        active_products = [p for p in products if p.get('status') == 'active']

        if not active_products:
            seller_name = seller.get('seller_name', 'Ce vendeur')
            await query.edit_message_text(
                f"🏪 **{seller_name}**\n\n❌ Aucun produit disponible actuellement" if lang == 'fr'
                else f"🏪 **{seller_name}**\n\n❌ No products available currently",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Retour" if lang == 'fr' else "Back", callback_data='back_main')
                ]]),
                parse_mode='Markdown'
            )
            return

        # Show first product in seller's shop using carousel
        # Create a pseudo-category for the seller's shop
        seller_category = f"seller_{seller_user_id}"

        # Add seller bio to caption if available
        seller_bio = seller.get('seller_bio')
        if seller_bio:
            # Prepend seller bio to the first product
            active_products[0]['seller_bio_display'] = seller_bio

        # Display seller's products in carousel
        await self.show_product_carousel(
            bot=bot,
            query=query,
            category_key=seller_category,
            products=active_products,
            index=0,
            lang=lang
        )