"""Sell Handlers - Modular class with dependency injection"""

import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.core.i18n import t as i18n
from app.integrations.telegram.keyboards import sell_menu_keyboard, back_to_main_button
from app.core.validation import validate_email, validate_solana_address

logger = logging.getLogger(__name__)

class SellHandlers:
    def __init__(self, user_repo, product_repo, payment_service):
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.payment_service = payment_service

    async def _safe_transition_to_text(self, query, text: str, keyboard=None, parse_mode='Markdown'):
        """
        Gère intelligemment la transition d'un message (photo ou texte) vers un message texte
        Identique à la fonction dans BuyHandlers
        """
        try:
            if query.message.photo:
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
            else:
                await query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"Error in _safe_transition_to_text: {e}")
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

    async def sell_menu(self, bot, query, lang: str):
        """Menu vendeur"""
        # Résoudre le mapping: telegram_id → seller_user_id
        seller_id = bot.get_seller_id(query.from_user.id)
        user_data = self.user_repo.get_user(seller_id)

        # Vérifier à la fois si l'utilisateur est vendeur ET s'il est connecté (avec le BON seller_id)
        if user_data and user_data['is_seller'] and bot.is_seller_logged_in(seller_id):
            await self.seller_dashboard(bot, query, lang)
            return

        # Si pas connecté, aller directement au prompt email (plus simple)
        await self.seller_login_prompt(bot, query, lang)

    async def create_seller_prompt(self, bot, query, lang: str):
        """Demande création compte vendeur"""
        bot.reset_conflicting_states(query.from_user.id, keep={'creating_seller'})
        bot.state_manager.update_state(query.from_user.id, creating_seller=True, step='name', lang=lang)
        await query.edit_message_text(
            f"{i18n(lang, 'seller_create_title')}\n\n{i18n(lang, 'seller_step1_prompt')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_cancel'), callback_data='sell_menu')]]),
            parse_mode='Markdown')

    async def seller_login_menu(self, bot, query, lang: str):
        """Menu connexion vendeur"""
        await query.edit_message_text(
            i18n(lang, 'login_title'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(i18n(lang, 'btn_email'), callback_data='seller_login'),
                InlineKeyboardButton(i18n(lang, 'btn_create_seller'), callback_data='create_seller')
            ], [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='back_main')]]),
            parse_mode='Markdown')

    async def seller_login_prompt(self, bot, query, lang: str):
        """Prompt pour connexion par email"""
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_seller_email'})
        bot.state_manager.update_state(query.from_user.id, waiting_seller_email=True, lang=lang)

        prompt_text = ("""📧 **SELLER LOGIN**

Enter your seller account email address:""" if lang == 'en' else """📧 **CONNEXION VENDEUR**

Entrez l'adresse email de votre compte vendeur :""")

        await query.edit_message_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    ("🚀 Create account" if lang == 'en' else "🚀 Créer un compte"),
                    callback_data='create_seller'
                )
            ], [
                InlineKeyboardButton(
                    ("🔙 Back" if lang == 'en' else "🔙 Retour"),
                    callback_data='back_main'
                )
            ]]),
            parse_mode='Markdown'
        )

    async def seller_dashboard(self, bot, query, lang: str):
        """Dashboard vendeur avec graphiques visuels"""
        from app.core import chart_generator
        from datetime import datetime, timedelta

        # Get actual seller_id (handles multi-account mapping)
        seller_id = bot.get_seller_id(query.from_user.id)
        user_data = self.user_repo.get_user(seller_id)
        if not user_data or not user_data['is_seller']:
            await self.seller_login_menu(bot, query, lang)
            return

        products = self.product_repo.get_products_by_seller(seller_id)
        total_revenue = sum(p.get('total_revenue', 0) for p in products)

        # Message texte simple
        dashboard_text = i18n(lang, 'dashboard_welcome').format(
            name=bot.escape_markdown(user_data.get('seller_name', 'Vendeur')),
            products_count=len(products),
            revenue=f"{total_revenue:.2f}€"
        )

        keyboard = [
            [InlineKeyboardButton("📊 Analytics IA", callback_data='analytics_dashboard'),
             InlineKeyboardButton("📈 Graphiques", callback_data='seller_analytics_visual')],
            [InlineKeyboardButton(i18n(lang, 'btn_add_product'), callback_data='add_product'),
             InlineKeyboardButton(i18n(lang, 'btn_my_products'), callback_data='my_products')],
            [InlineKeyboardButton(i18n(lang, 'btn_my_wallet'), callback_data='my_wallet'),
             InlineKeyboardButton(i18n(lang, 'btn_seller_settings'), callback_data='seller_settings')],
            [InlineKeyboardButton(i18n(lang, 'btn_library'), callback_data='library')],
            [InlineKeyboardButton(i18n(lang, 'btn_logout'), callback_data='seller_logout'),
             InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]
        ]

        try:
            await query.edit_message_text(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def seller_analytics_visual(self, bot, query, lang: str):
        """Affiche les analytics avec de vrais graphiques matplotlib"""
        from app.core import chart_generator
        from datetime import datetime, timedelta
        import logging

        logger = logging.getLogger(__name__)
        seller_id = bot.get_seller_id(query.from_user.id)

        try:
            # Notifier l'utilisateur
            await query.answer("📊 Génération des graphiques...")

            # Récupérer les données de ventes (7 derniers jours)
            orders = bot.order_repo.get_orders_by_seller(seller_id)

            # Préparer données revenus timeline
            sales_data = []
            product_sales_data = []

            for order in orders:
                if order.get('status') == 'completed':
                    sales_data.append({
                        'date': order.get('created_at', datetime.now()),
                        'revenue': float(order.get('price_eur', 0))
                    })

            # Données par produit
            products = self.product_repo.get_products_by_seller(seller_id)
            for product in products:
                product_orders = [o for o in orders if o.get('product_id') == product.get('product_id') and o.get('status') == 'completed']
                if product_orders:
                    product_sales_data.append({
                        'product_name': product.get('title', 'Sans nom'),
                        'sales_count': len(product_orders),
                        'revenue': sum(float(o.get('price_eur', 0)) for o in product_orders)
                    })

            # Générer graphique revenus (si données disponibles)
            if sales_data:
                try:
                    revenue_chart = chart_generator.generate_revenue_chart(sales_data, days=7)
                    await query.message.reply_photo(
                        photo=revenue_chart,
                        caption="📈 **Revenus des 7 derniers jours**",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Error generating revenue chart: {e}")

            # Générer graphique produits (si données disponibles)
            if product_sales_data:
                try:
                    products_chart = chart_generator.generate_products_chart(product_sales_data, top_n=5)
                    await query.message.reply_photo(
                        photo=products_chart,
                        caption="🏆 **Top 5 Produits par Revenus**",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Error generating products chart: {e}")

            # Si pas de données
            if not sales_data and not product_sales_data:
                await query.message.reply_text(
                    "📊 **Aucune donnée de vente disponible**\n\n"
                    "Les graphiques s'afficheront dès que vous aurez des ventes.",
                    parse_mode='Markdown'
                )

            # Bouton retour
            keyboard = [[InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')]]
            await query.message.reply_text(
                "✅ Analytics générées avec succès!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error in seller_analytics_visual: {e}")
            await query.message.reply_text(
                "❌ Erreur lors de la génération des graphiques.\n\n"
                f"Détails: {str(e)}",
                parse_mode='Markdown'
            )

    async def add_product_prompt(self, bot, query, lang: str):
        """Prompt ajout produit"""
        user_id = query.from_user.id

        # 🔍 DEBUG: État AVANT reset
        logger.info(f"🆕 ADD_PRODUCT_PROMPT - User {user_id}")
        logger.info(f"   State BEFORE reset: {bot.state_manager.get_state(user_id)}")

        bot.reset_conflicting_states(user_id, keep={'adding_product'})
        bot.state_manager.update_state(user_id, adding_product=True, step='title', product_data={}, lang=lang)

        # 🔍 DEBUG: État APRÈS initialisation
        final_state = bot.state_manager.get_state(user_id)
        logger.info(f"   State AFTER init: {final_state}")
        logger.info(f"   Memory cache entry: {bot.state_manager.user_states.get(user_id, 'NOT FOUND')}")

        await query.edit_message_text(
            f"{i18n(lang, 'product_add_title')}\n\n{i18n(lang, 'product_step1_prompt')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_cancel'), callback_data='seller_dashboard')]]),
            parse_mode='Markdown')

    def _get_product_creation_keyboard(self, current_step: str, lang: str = 'fr'):
        """Generate navigation keyboard for product creation steps"""
        keyboard = []

        # Map steps to their previous step
        step_flow = {
            'title': None,  # First step, no previous
            'description': 'title',
            'category': 'description',
            'price': 'category',
            'cover_image': 'price',
            'file': 'cover_image'
        }

        prev_step = step_flow.get(current_step)

        # Build navigation row
        nav_row = []

        if prev_step:
            prev_label = "← Étape précédente" if lang == 'fr' else "← Previous step"
            nav_row.append(InlineKeyboardButton(prev_label, callback_data=f'product_back_{prev_step}'))

        # Always show cancel button
        cancel_label = "❌ Annuler" if lang == 'fr' else "❌ Cancel"
        nav_row.append(InlineKeyboardButton(cancel_label, callback_data='product_cancel'))

        keyboard.append(nav_row)
        return InlineKeyboardMarkup(keyboard)

    async def show_seller_product_carousel(self, bot, query, products: list, index: int = 0, lang: str = 'fr') -> None:
        """Carousel visuel pour les produits du vendeur (avec boutons Éditer/Activer)"""
        try:
            from telegram import InputMediaPhoto
            from app.core.image_utils import ImageUtils
            import os

            if not products or index >= len(products):
                await query.edit_message_text("❌ No products found" if lang == 'en' else "❌ Aucun produit trouvé")
                return

            product = products[index]

            # Build caption - UX OPTIMIZED Dashboard Vendeur
            status_icon = "✅" if product['status'] == 'active' else "❌"
            status_text = "**ACTIF**" if product['status'] == 'active' else "_Inactif_"

            caption = ""

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 0. BREADCRUMB (Contexte vendeur)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            category = product.get('category', '')
            breadcrumb = f"📂 _Mes Produits" + (f" › {category}_" if category else "_")
            caption += f"{breadcrumb}\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. STATUT + TITRE (GRAS pour maximum visibilité)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"{status_icon} **{product['title']}**\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. PRIX + STATUT
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"💰 **{product['price_eur']:.2f} €**  •  {status_text}\n"
            caption += "─────────────────────\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 3. PERFORMANCE (Stats importantes pour vendeur)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += "📊 **PERFORMANCE**\n"
            caption += f"• **{product.get('sales_count', 0)}** ventes"

            # Calcul taux conversion si possible
            views = product.get('views_count', 0)
            sales = product.get('sales_count', 0)
            if views > 0 and sales > 0:
                conversion_rate = (sales / views) * 100
                caption += f" • Conversion: **{conversion_rate:.1f}%**"
            caption += f"\n• **{views}** vues"

            if product.get('rating', 0) > 0:
                rating_stars = "⭐" * int(product.get('rating', 0))
                caption += f"\n• {rating_stars} **{product.get('rating', 0):.1f}**/5"
                if product.get('reviews_count', 0) > 0:
                    caption += f" _({product.get('reviews_count', 0)} avis)_"
            caption += "\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 4. DESCRIPTION (Texte utilisateur - GARDER LE MARKDOWN)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            if product.get('description'):
                desc = product['description']
                if len(desc) > 160:
                    desc = desc[:160].rsplit(' ', 1)[0] + "..."
                caption += f"{desc}\n\n"

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 5. INFOS TECHNIQUES
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            caption += f"📂 _{product.get('category', 'N/A')}_  •  📁 {product.get('file_size_mb', 0):.1f} MB"

            # Get image or placeholder
            thumbnail_path = product.get('thumbnail_path')

            if not thumbnail_path or not os.path.exists(thumbnail_path):
                thumbnail_path = ImageUtils.create_or_get_placeholder(
                    product_title=product['title'],
                    category=product.get('category', 'General'),
                    product_id=product['product_id']
                )

            # Build keyboard - Actions vendeur
            keyboard = []

            # Row 1: Éditer (bouton principal)
            keyboard.append([
                InlineKeyboardButton(
                    "✏️ ÉDITER CE PRODUIT" if lang == 'fr' else "✏️ EDIT THIS PRODUCT",
                    callback_data=f'edit_product_{product["product_id"]}'
                )
            ])

            # Row 2: Navigation arrows
            nav_row = []
            if index > 0:
                nav_row.append(InlineKeyboardButton("⬅️", callback_data=f'seller_carousel_{index-1}'))
            else:
                nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))

            nav_row.append(InlineKeyboardButton(
                f"{index+1}/{len(products)}",
                callback_data='noop'
            ))

            if index < len(products) - 1:
                nav_row.append(InlineKeyboardButton("➡️", callback_data=f'seller_carousel_{index+1}'))
            else:
                nav_row.append(InlineKeyboardButton(" ", callback_data='noop'))

            keyboard.append(nav_row)

            # Row 3: Activer/Désactiver + Supprimer
            toggle_text = "❌ Désactiver" if product['status'] == 'active' else "✅ Activer"
            toggle_text_en = "❌ Deactivate" if product['status'] == 'active' else "✅ Activate"

            keyboard.append([
                InlineKeyboardButton(
                    toggle_text if lang == 'fr' else toggle_text_en,
                    callback_data=f'toggle_product_{product["product_id"]}'
                ),
                InlineKeyboardButton(
                    "🗑️ Supprimer" if lang == 'fr' else "🗑️ Delete",
                    callback_data=f'delete_product_{product["product_id"]}'
                )
            ])

            # Row 4: Back
            keyboard.append([
                InlineKeyboardButton(
                    "🔙 Dashboard" if lang == 'en' else "🔙 Dashboard",
                    callback_data='seller_dashboard'
                )
            ])

            # Send or edit message
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
                    await query.edit_message_text(
                        text=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
            except Exception as e:
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
            logger.error(f"Error in show_seller_product_carousel: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await query.edit_message_text(
                "❌ Error displaying product" if lang == 'en' else "❌ Erreur affichage produit"
            )

    async def show_my_products(self, bot, query, lang: str, page: int = 0):
        """Affiche produits vendeur avec carousel visuel"""
        # Get actual seller_id (handles multi-account mapping)
        seller_id = bot.get_seller_id(query.from_user.id)
        products = self.product_repo.get_products_by_seller(seller_id, limit=100, offset=0)

        if not products:
            await query.edit_message_text(
                i18n(lang, 'no_products_msg'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_add_product'), callback_data='add_product')],
                                                   [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='seller_dashboard')]]),
                parse_mode='Markdown')
            return

        # Launch carousel mode starting at index 0
        await self.show_seller_product_carousel(bot, query, products, index=0, lang=lang)

    async def show_wallet(self, bot, query, lang: str):
        """Affiche wallet vendeur"""
        user_data = self.user_repo.get_user(query.from_user.id)
        if not user_data:
            return

        wallet_text = i18n(lang, 'wallet_title').format(
            address=bot.escape_markdown(user_data.get('seller_solana_address', 'Non configurée')),
            balance=user_data.get('pending_balance', 0.0)
        )

        keyboard = [
            [InlineKeyboardButton(i18n(lang, 'btn_payout_history'), callback_data='sell_payout_history')],
            [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='seller_dashboard')]
        ]

        await query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def seller_analytics(self, bot, query, lang: str):
        """Analytics vendeur"""
        # Get actual seller_id (handles multi-account mapping)
        seller_id = bot.get_seller_id(query.from_user.id)
        products = self.product_repo.get_products_by_seller(seller_id)
        total_sales = sum(p.get('sales_count', 0) for p in products)
        total_revenue = sum(p.get('total_revenue', 0) for p in products)

        analytics_text = i18n(lang, 'analytics_title').format(
            products=len(products),
            sales=total_sales,
            revenue=f"{total_revenue:.2f}€"
        )

        await query.edit_message_text(
            analytics_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='seller_dashboard')]]),
            parse_mode='Markdown')

    async def seller_settings(self, bot, query, lang: str):
        """Paramètres vendeur"""
        user_data = self.user_repo.get_user(query.from_user.id)
        settings_text = i18n(lang, 'settings_title').format(
            name=bot.escape_markdown(user_data.get('seller_name', '')),
            email=bot.escape_markdown(user_data.get('email', ''))
        )

        keyboard = [
            [InlineKeyboardButton(i18n(lang, 'btn_edit_name'), callback_data='edit_seller_name'),
             InlineKeyboardButton(i18n(lang, 'btn_edit_bio'), callback_data='edit_seller_bio')],
            [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='seller_dashboard')]
        ]

        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def seller_logout(self, bot, query):
        """Déconnexion vendeur"""
        # Résoudre le mapping pour déconnecter le BON seller_id
        seller_id = bot.get_seller_id(query.from_user.id)
        bot.logout_seller(seller_id)
        await query.edit_message_text(
            "✅ **Déconnexion réussie**\n\nÀ bientôt !",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu principal", callback_data='back_main')]]),
            parse_mode='Markdown')

    async def delete_seller_prompt(self, bot, query):
        """Confirmation suppression compte vendeur"""
        await query.edit_message_text(
            "⚠️ **ATTENTION**\n\nVoulez-vous vraiment supprimer votre compte vendeur ?\n\n❌ Cette action est **irréversible**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirmer suppression", callback_data='delete_seller_confirm')],
                [InlineKeyboardButton("❌ Annuler", callback_data='seller_settings')]
            ]),
            parse_mode='Markdown')

    async def delete_seller_confirm(self, bot, query):
        """Suppression définitive compte vendeur"""
        user_id = query.from_user.id
        success = self.user_repo.delete_seller_account(user_id)
        if success:
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await query.edit_message_text(
                "✅ **Compte vendeur supprimé**\n\nVos données ont été effacées.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu principal", callback_data='back_main')]]),
                parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Erreur lors de la suppression")

    # Text processing methods
    async def process_seller_creation(self, bot, update, message_text: str):
        """Process création vendeur"""
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)
        step = user_state.get('step')

        if step == 'name':
            if len(message_text) < 2 or len(message_text) > 20:
                await update.message.reply_text("❌ Le nom doit contenir entre 2 et 30 caractères.")
                return
            user_state['seller_name'] = message_text
            user_state['step'] = 'bio'
            await update.message.reply_text(f"✅ **Nom :** {bot.escape_markdown(message_text)}\n\nÉtape 2: Entrez votre biographie (max 500 caractères)", parse_mode='Markdown')

        elif step == 'bio':
            user_state['seller_bio'] = message_text[:500]
            user_state['step'] = 'email'
            await update.message.reply_text("✅ **Bio sauvegardée**\n\nÉtape 3: Entrez votre email de récupération", parse_mode='Markdown')

        elif step == 'email':
            email = message_text.strip().lower()
            if not validate_email(email):
                await update.message.reply_text("❌ Email invalide")
                return
            user_state['email'] = email
            user_state['step'] = 'password'
            await update.message.reply_text("✅ **Email sauvegardé**\n\nÉtape 4: Créez un mot de passe sécurisé (min 8 caractères)", parse_mode='Markdown')

        elif step == 'password':
            password = message_text.strip()
            if len(password) < 8:
                await update.message.reply_text("❌ Le mot de passe doit contenir au moins 8 caractères")
                return

            user_state['password'] = password
            user_state['step'] = 'solana_address'
            await update.message.reply_text(
                "✅ **Mot de passe sauvegardé**\n\nÉtape 5: Entrez votre adresse Solana pour recevoir vos paiements\n\n💡 **Format attendu:** `1A2B3C...` (32-44 caractères)\n\n⚠️ **Important:** Vérifiez bien l'adresse, c'est là que vous recevrez vos gains !",
                parse_mode='Markdown'
            )

        elif step == 'solana_address':
            solana_address = message_text.strip()
            if not validate_solana_address(solana_address):
                await update.message.reply_text(
                    "❌ **Adresse Solana invalide**\n\nVérifiez le format depuis votre wallet\n\n💡 L'adresse doit contenir entre 32 et 44 caractères",
                    parse_mode='Markdown'
                )
                return

            # Create seller account with all collected data
            result = bot.seller_service.create_seller_account_with_recovery(
                user_id, user_state['seller_name'], user_state['seller_bio'],
                user_state['email'], user_state['password'], solana_address
            )

            bot.state_manager.reset_state(user_id, keep={'lang'})
            if result['success']:
                bot.login_seller(user_id)
                try:
                    await update.message.reply_text(
                        "✅ **Compte vendeur créé avec succès !**\n\n🎉 Bienvenue dans votre espace vendeur.\n\n💰 Votre adresse Solana est configurée, vous êtes prêt à vendre !",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Mon Dashboard Vendeur", callback_data='seller_dashboard')]]),
                        parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"❌ Timeout sending success message: {e}")
                    # Try simpler message without markup
                    try:
                        await update.message.reply_text("✅ Compte créé ! Tapez /start pour accéder au dashboard")
                    except:
                        pass  # Silent fail, user can restart bot
            else:
                error_msg = result.get('error', 'Erreur inconnue')
                try:
                    await update.message.reply_text(f"❌ Erreur création compte: {error_msg}")
                except Exception as e:
                    logger.error(f"❌ Timeout sending error message: {e}")

    async def process_seller_email(self, bot, update, message_text: str):
        """Process email pour connexion vendeur"""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        lang = bot.get_user_state(user_id).get('lang', 'fr')

        if not validate_email(email):
            error_msg = "❌ Invalid email format" if lang == 'en' else "❌ Format email invalide"
            await update.message.reply_text(error_msg)
            return

        # Chercher utilisateur par email
        user = self.user_repo.get_user_by_email(email)
        if not user or not user.get('is_seller'):
            error_msg = "❌ No seller account found with this email" if lang == 'en' else "❌ Aucun compte vendeur avec cet email"
            await update.message.reply_text(error_msg)
            bot.reset_user_state_preserve_login(user_id)
            return

        # Passer à l'étape password
        bot.state_manager.update_state(user_id,
            waiting_seller_email=False,
            waiting_seller_password=True,
            seller_email=email,
            target_seller_user_id=user['user_id'],
            lang=lang
        )

        prompt_text = ("""🔐 **PASSWORD**

Enter your password:""" if lang == 'en' else """🔐 **MOT DE PASSE**

Entrez votre mot de passe :""")

        await update.message.reply_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    ("🔐 Forgot password?" if lang == 'en' else "🔐 Mot de passe oublié?"),
                    callback_data='account_recovery'
                )
            ], [
                InlineKeyboardButton(
                    ("🔙 Cancel" if lang == 'en' else "🔙 Annuler"),
                    callback_data='back_main'
                )
            ]]),
            parse_mode='Markdown'
        )

    async def process_seller_password(self, bot, update, message_text: str):
        """Process password pour connexion vendeur"""
        user_id = update.effective_user.id
        user_state = bot.get_user_state(user_id)
        password = message_text.strip()
        email = user_state.get('seller_email')
        target_seller_user_id = user_state.get('target_seller_user_id')
        lang = user_state.get('lang', 'fr')

        if not target_seller_user_id:
            error_msg = "❌ Session expired" if lang == 'en' else "❌ Session expirée"
            await update.message.reply_text(error_msg)
            bot.reset_user_state_preserve_login(user_id)
            return

        if bot.authenticate_seller(target_seller_user_id, password):
            # Connexion réussie
            bot.reset_user_state_preserve_login(user_id)

            # IMPORTANT: Connecter le VRAI seller_id (pas le telegram_id)
            bot.login_seller(target_seller_user_id)

            # Créer le mapping si connexion depuis un autre Telegram ID
            if user_id != target_seller_user_id:
                bot.update_user_mapping(user_id, target_seller_user_id)

            success_msg = "✅ Login successful!" if lang == 'en' else "✅ Connexion réussie !"
            await update.message.reply_text(
                success_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🏪 Dashboard" if lang == 'en' else "🏪 Dashboard"),
                        callback_data='seller_dashboard'
                    )
                ]])
            )
        else:
            # Mauvais password - proposer recovery
            error_msg = "❌ Incorrect password" if lang == 'en' else "❌ Mot de passe incorrect"
            await update.message.reply_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔐 Forgot password?" if lang == 'en' else "🔐 Mot de passe oublié?"),
                        callback_data='account_recovery'
                    ),
                    InlineKeyboardButton(
                        ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                        callback_data='sell_menu'
                    )
                ], [
                    InlineKeyboardButton(
                        ("🔙 Cancel" if lang == 'en' else "🔙 Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )
            bot.reset_user_state_preserve_login(user_id)

    async def process_seller_login(self, bot, update, message_text: str):
        """Process connexion vendeur"""
        user_id = update.effective_user.id
        if bot.authenticate_seller(user_id, ""):
            await update.message.reply_text(
                "✅ **Connexion réussie !**\n\nBienvenue dans votre espace vendeur.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏪 Dashboard", callback_data='seller_dashboard'),
                    InlineKeyboardButton("💰 Wallet", callback_data='my_wallet')
                ]]))
        else:
            await update.message.reply_text(
                "❌ **Vous n'êtes pas encore vendeur**\n\nCréez votre compte en quelques étapes.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Créer compte", callback_data='create_seller'),
                    InlineKeyboardButton("🔙 Retour", callback_data='back_main')
                ]]))

    async def process_product_addition(self, bot, update, message_text: str):
        """Process ajout produit"""
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)
        step = user_state.get('step')
        product_data = user_state.get('product_data', {})

        if step == 'title':
            if len(message_text) < 5 or len(message_text) > 100:
                await update.message.reply_text(
                    "❌ Le titre doit contenir entre 5 et 100 caractères.",
                    reply_markup=self._get_product_creation_keyboard('title', user_state.get('lang', 'fr'))
                )
                return
            product_data['title'] = message_text
            user_state['product_data'] = product_data  # CRITICAL: Update product_data in state
            user_state['step'] = 'description'
            # IMPORTANT: Save state
            bot.state_manager.update_state(user_id, **user_state)
            await update.message.reply_text(
                f"✅ **Titre :** {bot.escape_markdown(message_text)}\n\n📝 **Étape 2/6 :** Description du produit",
                parse_mode='Markdown',
                reply_markup=self._get_product_creation_keyboard('description', user_state.get('lang', 'fr'))
            )

        elif step == 'description':
            product_data['description'] = message_text[:1000]
            user_state['product_data'] = product_data  # CRITICAL: Update product_data in state
            user_state['step'] = 'category'
            # IMPORTANT: Save state
            bot.state_manager.update_state(user_id, **user_state)
            # Afficher le menu de sélection de catégorie
            await self._show_category_selection(bot, update, user_state.get('lang', 'fr'))

        elif step == 'price':
            try:
                price = float(message_text.replace(',', '.'))
                if price < 1 or price > 5000:
                    raise ValueError()

                # 🔍 DEBUG: État AVANT modification
                logger.info(f"💰 PRICE STEP - User {user_id}")
                logger.info(f"   State BEFORE: {user_state}")

                product_data['price_eur'] = price
                product_data['price_usd'] = price * self.payment_service.get_exchange_rate()
                user_state['product_data'] = product_data  # CRITICAL: Update product_data in state
                user_state['step'] = 'cover_image'

                # 🔍 DEBUG: État APRÈS modification, AVANT save
                logger.info(f"   State AFTER modification: {user_state}")

                # IMPORTANT: Save state to StateManager
                bot.state_manager.update_state(update.effective_user.id, **user_state)

                # 🔍 DEBUG: État APRÈS save
                saved_state = bot.state_manager.get_state(user_id)
                logger.info(f"   State AFTER save: {saved_state}")
                logger.info(f"   Memory cache: {bot.state_manager.user_states.get(user_id, 'NOT FOUND')}")

                # Get navigation keyboard and add skip button
                keyboard = self._get_product_creation_keyboard('cover_image', user_state.get('lang', 'fr'))
                # Prepend skip button row - Create new list to avoid tuple mutation error
                skip_button_row = [InlineKeyboardButton("⏭️ Passer" if user_state.get('lang') == 'fr' else "⏭️ Skip", callback_data='skip_cover_image')]
                new_keyboard = [skip_button_row] + list(keyboard.inline_keyboard)
                keyboard = InlineKeyboardMarkup(new_keyboard)

                await update.message.reply_text(
                    f"✅ **Prix :** {price}€\n\n"
                    f"📸 **Étape 5/6 :** Envoyez une image de couverture (optionnel)\n\n"
                    f"• Format: JPG/PNG\n"
                    f"• Taille max: 5MB\n"
                    f"• Recommandé: 800x600px minimum",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            except (ValueError, TypeError):
                await update.message.reply_text("❌ Prix invalide. Entrez un nombre entre 1 et 5000.")

    async def _show_category_selection(self, bot, update, lang):
        """Affiche le menu de sélection de catégorie lors de l'ajout de produit"""
        from app.core.settings import settings

        text = i18n(lang, 'product_category_step') + "\n\n" + i18n(lang, 'categories_title')
        keyboard = []

        # Grouper les catégories par 2
        categories = settings.DEFAULT_CATEGORIES
        for i in range(0, len(categories), 2):
            row = []
            for j in range(i, min(i + 2, len(categories))):
                category, desc, emoji = categories[j]
                # Utiliser l'index pour éviter problèmes d'encoding/decoding
                row.append(InlineKeyboardButton(
                    f"{emoji} {category}",
                    callback_data=f'add_product_category_{j}'  # Index au lieu du nom
                ))
            keyboard.append(row)

        # Add navigation buttons
        nav_keyboard = self._get_product_creation_keyboard('category', lang)
        keyboard.extend(nav_keyboard.inline_keyboard)

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_category_selection(self, bot, query, category_index, lang):
        """Traite la sélection de catégorie lors de l'ajout de produit"""
        from app.core.settings import settings

        user_id = query.from_user.id
        user_state = bot.state_manager.get_state(user_id)
        product_data = user_state.get('product_data', {})

        # Récupérer le nom exact de la catégorie depuis les settings
        categories = settings.DEFAULT_CATEGORIES
        if 0 <= category_index < len(categories):
            category_name = categories[category_index][0]  # Premier élément du tuple
        else:
            category_name = "Uncategorized"

        product_data['category'] = category_name
        user_state['step'] = 'price'
        bot.state_manager.update_state(user_id, **user_state)

        await query.edit_message_text(
            f"✅ **Catégorie :** {category_name}\n\n💰 **Étape 4/6 :** Prix en EUR (ex: 29.99)",
            parse_mode='Markdown',
            reply_markup=self._get_product_creation_keyboard('price', lang)
        )

    async def handle_skip_cover_image(self, bot, query):
        """Skip cover image upload step"""
        user_id = query.from_user.id
        user_state = bot.state_manager.get_state(user_id)
        user_state['step'] = 'file'
        bot.state_manager.update_state(user_id, **user_state)

        await query.edit_message_text(
            f"⏭️ **Image de couverture ignorée**\n\n"
            f"📁 **Étape 6/6 :** Envoyez maintenant votre fichier produit\n\n"
            f"_Une image placeholder sera générée automatiquement_",
            parse_mode='Markdown',
            reply_markup=self._get_product_creation_keyboard('file', user_state.get('lang', 'fr'))
        )

    async def handle_product_cancel(self, bot, query, lang: str):
        """Cancel product creation and reset state"""
        user_id = query.from_user.id
        bot.state_manager.reset_state(user_id, keep={'lang'})

        await query.edit_message_text(
            "❌ Ajout de produit annulé" if lang == 'fr' else "❌ Product creation cancelled",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏪 Dashboard", callback_data='seller_dashboard')
            ]])
        )

    async def handle_product_back(self, bot, query, target_step: str, lang: str):
        """Go back to previous step in product creation"""
        user_id = query.from_user.id
        user_state = bot.state_manager.get_state(user_id)
        product_data = user_state.get('product_data', {})

        # Update step
        user_state['step'] = target_step
        bot.state_manager.update_state(user_id, **user_state)

        # Show appropriate message for target step
        step_messages = {
            'title': f"📝 **Étape 1/6 :** Titre du produit\n\n{i18n(lang, 'product_step1_prompt')}",
            'description': f"📋 **Étape 2/6 :** Description du produit\n\nTitre actuel: {product_data.get('title', 'N/A')}",
            'category': None,  # Will show category selection
            'price': f"💰 **Étape 4/6 :** Prix en EUR\n\nCatégorie actuelle: {product_data.get('category', 'N/A')}",
            'cover_image': (
                f"📸 **Étape 5/6 :** Image de couverture (optionnel)\n\n"
                f"Prix actuel: {product_data.get('price_eur', 'N/A')}€\n\n"
                f"• Format: JPG/PNG\n• Taille max: 5MB"
            ),
            'file': f"📁 **Étape 6/6 :** Fichier produit"
        }

        if target_step == 'category':
            # Show category selection menu - use query.message as update for compatibility
            from telegram import Update
            pseudo_update = type('obj', (object,), {'message': query.message, 'effective_user': query.from_user})()
            await self._show_category_selection(bot, pseudo_update, lang)
        else:
            message = step_messages.get(target_step, "Retour à l'étape précédente")
            keyboard = self._get_product_creation_keyboard(target_step, lang)

            # Add skip button for cover_image step
            if target_step == 'cover_image':
                skip_button_row = [InlineKeyboardButton("⏭️ Passer" if lang == 'fr' else "⏭️ Skip", callback_data='skip_cover_image')]
                new_keyboard = [skip_button_row] + list(keyboard.inline_keyboard)
                keyboard = InlineKeyboardMarkup(new_keyboard)

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

    async def process_cover_image_upload(self, bot, update, photo=None, photo_as_document=None):
        """Process cover image upload for product"""
        try:
            from app.core.image_utils import ImageUtils
            import tempfile

            telegram_id = update.effective_user.id
            seller_id = bot.get_seller_id(telegram_id)

            user_state = bot.get_user_state(telegram_id)
            product_data = user_state.get('product_data', {})

            # 🔧 Handle both photo array and document (image sent as file)
            if photo_as_document:
                logger.info(f"📸 Processing image sent as document")
                photo_file = photo_as_document
            elif photo:
                # Get largest photo size from photo array
                photo_file = photo[-1]
            else:
                await update.message.reply_text("❌ Aucune image reçue")
                return

            # Validation
            if photo_file.file_size > 5 * 1024 * 1024:  # 5MB max
                await update.message.reply_text("❌ Image trop volumineuse (max 5MB)")
                return

            # Download photo to temp file
            file_info = await photo_file.get_file()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                await file_info.download_to_drive(tmp_file.name)
                tmp_path = tmp_file.name

            # Generate temporary product_id for directory
            import uuid
            temp_product_id = f"TEMP_{uuid.uuid4().hex[:8]}"

            # Save cover and generate thumbnail
            cover_path, thumbnail_path = ImageUtils.save_telegram_photo(
                tmp_path, seller_id, temp_product_id
            )

            # Clean up temp file
            os.remove(tmp_path)

            if cover_path and thumbnail_path:
                product_data['cover_image_path'] = cover_path
                product_data['thumbnail_path'] = thumbnail_path
                product_data['temp_product_id'] = temp_product_id
                user_state['step'] = 'file'
                bot.state_manager.update_state(telegram_id, **user_state)

                # DEBUG LOG
                logger.info(f"📸 IMAGE STORED - Cover: {cover_path}, Thumbnail: {thumbnail_path}, Temp ID: {temp_product_id}")

                await update.message.reply_text(
                    f"✅ **Image de couverture enregistrée!**\n\n"
                    f"📁 **Étape 6/6 :** Envoyez maintenant votre fichier produit",
                    parse_mode='Markdown',
                    reply_markup=self._get_product_creation_keyboard('file', user_state.get('lang', 'fr'))
                )
            else:
                await update.message.reply_text("❌ Erreur lors du traitement de l'image")

        except Exception as e:
            logger.error(f"Error processing cover image: {e}")
            await update.message.reply_text("❌ Erreur lors du traitement de l'image")

    async def process_file_upload(self, bot, update, document):
        """Process file upload pour ajout produit"""
        try:
            telegram_id = update.effective_user.id
            # Get actual seller_id (handles multi-account mapping)
            seller_id = bot.get_seller_id(telegram_id)

            user_state = bot.get_user_state(telegram_id)
            product_data = user_state.get('product_data', {})
            lang = user_state.get('lang', 'fr')

            # Validation du fichier
            if document.file_size > 10 * 1024 * 1024:  # 10MB max
                await update.message.reply_text("❌ Fichier trop volumineux (max 10MB)")
                return

            # Télécharger et sauvegarder le fichier
            file_info = await document.get_file()
            filename = await bot.save_uploaded_file(file_info, document.file_name)

            if not filename:
                await update.message.reply_text("❌ Erreur lors de la sauvegarde du fichier")
                return

            # Ajouter le fichier aux données produit
            product_data['file_path'] = filename
            product_data['file_name'] = document.file_name
            product_data['file_size'] = document.file_size

            # Créer le produit avec le seller_id mappé
            product_data['seller_id'] = seller_id
            product_id = bot.create_product(product_data)

            if product_id:
                # If we had a temp product_id, rename the image directory
                if 'temp_product_id' in product_data:
                    self._rename_product_images(
                        seller_id,
                        product_data['temp_product_id'],
                        product_id,
                        product_data
                    )

                # Succès - réinitialiser l'état et rediriger
                bot.reset_user_state_preserve_login(telegram_id)

                success_msg = f"✅ **Produit créé avec succès!**\n\n**ID:** {product_id}\n**Titre:** {product_data['title']}\n**Prix:** {product_data['price_eur']}€"

                await update.message.reply_text(
                    success_msg,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏪 Dashboard" if lang == 'en' else "🏪 Dashboard", callback_data='seller_dashboard'),
                        InlineKeyboardButton("📦 Mes produits" if lang == 'en' else "📦 Mes produits", callback_data='my_products')
                    ]]),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Erreur lors de la création du produit")

        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            await update.message.reply_text("❌ Erreur lors du traitement du fichier")

    def _rename_product_images(self, seller_id, temp_product_id, final_product_id, product_data):
        """Rename product image directory from temp to final product_id and UPDATE DATABASE"""
        try:
            import shutil
            from app.core import get_sqlite_connection, settings as core_settings

            old_dir = os.path.join('data', 'product_images', str(seller_id), temp_product_id)
            new_dir = os.path.join('data', 'product_images', str(seller_id), final_product_id)

            if os.path.exists(old_dir):
                # Rename directory
                shutil.move(old_dir, new_dir)
                logger.info(f"📁 Renamed directory: {old_dir} -> {new_dir}")

                # Update paths in product_data (for logging)
                new_cover_path = None
                new_thumbnail_path = None

                if 'cover_image_path' in product_data:
                    new_cover_path = product_data['cover_image_path'].replace(
                        temp_product_id, final_product_id
                    )
                if 'thumbnail_path' in product_data:
                    new_thumbnail_path = product_data['thumbnail_path'].replace(
                        temp_product_id, final_product_id
                    )

                # 🔧 CRITICAL FIX: Update paths in DATABASE
                if new_cover_path or new_thumbnail_path:
                    conn = get_sqlite_connection(core_settings.DATABASE_PATH)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            '''
                            UPDATE products
                            SET cover_image_path = ?, thumbnail_path = ?
                            WHERE product_id = ?
                            ''',
                            (new_cover_path, new_thumbnail_path, final_product_id)
                        )
                        conn.commit()
                        logger.info(f"✅ Updated DB paths: cover={new_cover_path}, thumb={new_thumbnail_path}")
                    except Exception as db_error:
                        logger.error(f"❌ DB update failed: {db_error}")
                        conn.rollback()
                    finally:
                        conn.close()

                logger.info(f"✅ Renamed product images: {temp_product_id} -> {final_product_id}")
            else:
                logger.warning(f"⚠️ Old directory not found: {old_dir}")
        except Exception as e:
            logger.error(f"❌ Error renaming product images: {e}")

    async def process_seller_settings(self, bot, update, message_text: str):
        """Process paramètres vendeur"""
        user_id = update.effective_user.id
        state = bot.state_manager.get_state(user_id)
        step = state.get('step')

        if step == 'edit_name':
            new_name = message_text.strip()[:50]
            success = self.user_repo.update_seller_name(user_id, new_name)
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text("✅ Nom mis à jour." if success else "❌ Erreur mise à jour nom.")

        elif step == 'edit_bio':
            new_bio = message_text.strip()[:500]
            success = self.user_repo.update_seller_bio(user_id, new_bio)
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text("✅ Biographie mise à jour." if success else "❌ Erreur mise à jour bio.")

    # Missing methods from monolith - extracted from bot_mlt.py
    async def payout_history(self, bot, query, lang):
        """Historique payouts vendeur"""
        user_id = query.from_user.id
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT total_amount_sol, payout_status, created_at
                FROM seller_payouts
                WHERE seller_user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            ''', (user_id,))
            payouts = cursor.fetchall()
            conn.close()

            if not payouts:
                text = "💰 Aucun payout trouvé." if lang == 'fr' else "💰 No payouts found."
            else:
                text = "💰 **HISTORIQUE PAYOUTS**\n\n" if lang == 'fr' else "💰 **PAYOUT HISTORY**\n\n"
                for amount, status, date in payouts:
                    text += f"• {amount:.4f} SOL - {status} - {date[:10]}\n"

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    back_to_main_button(lang)
                ]]),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erreur payout history: {e}")
            await query.edit_message_text(
                "❌ Erreur chargement historique." if lang == 'fr' else "❌ Error loading history.",
                reply_markup=InlineKeyboardMarkup([[
                    back_to_main_button(lang)
                ]])
            )

    async def copy_address(self, bot, query, lang):
        """Copier adresse Solana vendeur"""
        user_id = query.from_user.id
        user_data = self.user_repo.get_user(user_id)

        if not user_data or not user_data.get('seller_solana_address'):
            await query.edit_message_text(
                "❌ Aucune adresse Solana configurée." if lang == 'fr' else "❌ No Solana address configured.",
                reply_markup=InlineKeyboardMarkup([[
                    back_to_main_button(lang)
                ]])
            )
            return

        address = user_data['seller_solana_address']
        await query.edit_message_text(
            f"📋 **Votre adresse Solana:**\n\n`{address}`\n\n💡 Copiez cette adresse pour recevoir vos paiements." if lang == 'fr' else f"📋 **Your Solana address:**\n\n`{address}`\n\n💡 Copy this address to receive payments.",
            reply_markup=InlineKeyboardMarkup([[
                back_to_main_button(lang)
            ]]),
            parse_mode='Markdown'
        )

    async def edit_product_menu(self, bot, query, product_id: str, lang: str):
        """Show product edit menu"""
        try:
            # Get product details
            product = self.product_repo.get_product_by_id(product_id)
            if not product:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
                await self._safe_transition_to_text(
                    query,
                    "❌ Produit introuvable." if lang == 'fr' else "❌ Product not found.",
                    keyboard
                )
                return

            title = product.get('title', 'Sans titre')
            price = product.get('price_eur', 0)
            status = product.get('status', 'active')

            menu_text = f"✏️ **Édition: {title}**\n\n💰 Prix: {price}€\n📊 Statut: {status}\n\nQue voulez-vous modifier ?"

            keyboard = [
                [InlineKeyboardButton("📝 Modifier titre" if lang == 'fr' else "📝 Edit title",
                                    callback_data=f'edit_field_title_{product_id}')],
                [InlineKeyboardButton("💰 Modifier prix" if lang == 'fr' else "💰 Edit price",
                                    callback_data=f'edit_field_price_{product_id}')],
                [InlineKeyboardButton("🔄 Changer statut" if lang == 'fr' else "🔄 Toggle status",
                                    callback_data=f'edit_field_toggle_{product_id}')],
                [InlineKeyboardButton("🗑️ Supprimer" if lang == 'fr' else "🗑️ Delete",
                                    callback_data=f'confirm_delete_{product_id}')],
                [InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')]
            ]

            await self._safe_transition_to_text(
                query,
                menu_text,
                InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error in edit_product_menu: {e}")
            keyboard_error = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
            ]])
            await self._safe_transition_to_text(
                query,
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                keyboard_error
            )

    async def confirm_delete_product(self, bot, query, product_id: str, lang: str):
        """Confirm product deletion"""
        try:
            # Get product details
            product = self.product_repo.get_product_by_id(product_id)
            if not product:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
                await self._safe_transition_to_text(
                    query,
                    "❌ Produit introuvable." if lang == 'fr' else "❌ Product not found.",
                    keyboard
                )
                return

            title = product.get('title', 'Sans titre')

            # Delete the product - Get actual seller_id (not telegram_id)
            telegram_id = query.from_user.id
            seller_user_id = bot.get_seller_id(telegram_id)

            if not seller_user_id:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
                await self._safe_transition_to_text(
                    query,
                    "❌ Vous devez être connecté en tant que vendeur." if lang == 'fr' else "❌ You must be logged in as a seller.",
                    keyboard
                )
                return

            success = self.product_repo.delete_product(product_id, seller_user_id)

            if success:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Mes produits" if lang == 'fr' else "🔙 My products", callback_data='my_products')
                ]])
                await self._safe_transition_to_text(
                    query,
                    f"✅ **Produit supprimé**\n\n📦 {title} a été supprimé avec succès." if lang == 'fr'
                    else f"✅ **Product deleted**\n\n📦 {title} has been deleted successfully.",
                    keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
                await self._safe_transition_to_text(
                    query,
                    "❌ Impossible de supprimer le produit." if lang == 'fr' else "❌ Could not delete product.",
                    keyboard
                )

        except Exception as e:
            logger.error(f"Error in confirm_delete_product: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de la suppression." if lang == 'fr' else "❌ Deletion error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
            )

    async def edit_product_field(self, bot, query, field: str, product_id: str, lang: str):
        """Handle product field editing"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = bot.get_seller_id(query.from_user.id)

            # Verify user owns this product
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await self._safe_transition_to_text(
                    query,
                    "❌ Produit non trouvé ou non autorisé." if lang == 'fr' else "❌ Product not found or unauthorized.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                    ]])
                )
                return

            # Set user state for editing
            bot.reset_conflicting_states(user_id, keep={f'editing_product_{field}'})
            bot.state_manager.update_state(user_id, **{f'editing_product_{field}': product_id})

            # Show appropriate prompt based on field
            if field == 'price':
                await self._safe_transition_to_text(
                    query,
                    f"💰 **Modifier le prix de:** {product.get('title', 'N/A')}\n\n"
                    f"Prix actuel: {product.get('price_eur', 0):.2f}€\n\n"
                    f"Entrez le nouveau prix en euros:" if lang == 'fr' else
                    f"💰 **Edit price for:** {product.get('title', 'N/A')}\n\n"
                    f"Current price: €{product.get('price_eur', 0):.2f}\n\n"
                    f"Enter new price in euros:",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                    ]])
                )
            elif field == 'title':
                await self._safe_transition_to_text(
                    query,
                    f"📝 **Modifier le titre de:** {product.get('title', 'N/A')}\n\n"
                    f"Entrez le nouveau titre:" if lang == 'fr' else
                    f"📝 **Edit title for:** {product.get('title', 'N/A')}\n\n"
                    f"Enter new title:",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                    ]])
                )
            elif field == 'description':
                await self._safe_transition_to_text(
                    query,
                    f"📄 **Modifier la description de:** {product.get('title', 'N/A')}\n\n"
                    f"Entrez la nouvelle description:" if lang == 'fr' else
                    f"📄 **Edit description for:** {product.get('title', 'N/A')}\n\n"
                    f"Enter new description:",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                    ]])
                )
            else:
                await self._safe_transition_to_text(
                    query,
                    "❌ Champ non éditable." if lang == 'fr' else "❌ Field not editable.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data=f'edit_product_{product_id}')
                    ]])
                )

        except Exception as e:
            logger.error(f"Error in edit_product_field: {e}")
            await self._safe_transition_to_text(
                query,
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
            )

    async def edit_seller_name(self, bot, query, lang):
        """Edit seller name"""
        try:
            user_id = query.from_user.id

            # Check if user is a seller
            user_data = self.user_repo.get_user(user_id)
            if not user_data or not user_data.get('is_seller'):
                await query.edit_message_text(
                    "❌ Vous devez être vendeur pour modifier ces informations." if lang == 'fr' else "❌ You must be a seller to edit this information.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')
                    ]])
                )
                return

            # Set editing state
            bot.reset_conflicting_states(user_id, keep={'editing_seller_name'})
            bot.state_manager.update_state(user_id, editing_seller_name=True)

            current_name = user_data.get('seller_name', 'Non défini')
            await query.edit_message_text(
                f"📝 **Modifier le nom de vendeur**\n\n"
                f"Nom actuel: {current_name}\n\n"
                f"Entrez votre nouveau nom de vendeur:" if lang == 'fr' else
                f"📝 **Edit seller name**\n\n"
                f"Current name: {current_name}\n\n"
                f"Enter your new seller name:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='seller_settings')
                ]])
            )

        except Exception as e:
            logger.error(f"Error in edit_seller_name: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')
                ]])
            )

    async def edit_seller_bio(self, bot, query, lang):
        """Edit seller bio"""
        try:
            user_id = query.from_user.id

            # Check if user is a seller
            user_data = self.user_repo.get_user(user_id)
            if not user_data or not user_data.get('is_seller'):
                await query.edit_message_text(
                    "❌ Vous devez être vendeur pour modifier ces informations." if lang == 'fr' else "❌ You must be a seller to edit this information.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')
                    ]])
                )
                return

            # Set editing state
            bot.reset_conflicting_states(user_id, keep={'editing_seller_bio'})
            bot.state_manager.update_state(user_id, editing_seller_bio=True)

            current_bio = user_data.get('seller_bio', 'Non défini')
            await query.edit_message_text(
                f"📄 **Modifier la biographie vendeur**\n\n"
                f"Bio actuelle: {current_bio}\n\n"
                f"Entrez votre nouvelle biographie:" if lang == 'fr' else
                f"📄 **Edit seller bio**\n\n"
                f"Current bio: {current_bio}\n\n"
                f"Enter your new biography:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='seller_settings')
                ]])
            )

        except Exception as e:
            logger.error(f"Error in edit_seller_bio: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')
                ]])
            )

    async def edit_product_price_prompt(self, bot, query, product_id, lang):
        """Prompt for editing product price"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = bot.get_seller_id(query.from_user.id)

            # Get product and verify ownership
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await self._safe_transition_to_text(
                    query,
                    "❌ Produit non trouvé ou non autorisé." if lang == 'fr' else "❌ Product not found or unauthorized.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                    ]])
                )
                return

            # Set editing state
            bot.reset_conflicting_states(user_id, keep={'editing_product_price'})
            bot.state_manager.update_state(user_id, editing_product_price=product_id)

            await self._safe_transition_to_text(
                query,
                f"💰 **Modifier le prix de:** {product.get('title', 'N/A')}\n\n"
                f"Prix actuel: {product.get('price_eur', 0):.2f}€\n\n"
                f"Entrez le nouveau prix en euros (1-5000€):" if lang == 'fr' else
                f"💰 **Edit price for:** {product.get('title', 'N/A')}\n\n"
                f"Current price: €{product.get('price_eur', 0):.2f}\n\n"
                f"Enter new price in euros (€1-5000):",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                ]])
            )

        except Exception as e:
            logger.error(f"Error in edit_product_price_prompt: {e}")
            await self._safe_transition_to_text(
                query,
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
            )

    async def edit_product_title_prompt(self, bot, query, product_id, lang):
        """Prompt for editing product title"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = bot.get_seller_id(query.from_user.id)

            # Get product and verify ownership
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await self._safe_transition_to_text(
                    query,
                    "❌ Produit non trouvé ou non autorisé." if lang == 'fr' else "❌ Product not found or unauthorized.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                    ]])
                )
                return

            # Set editing state
            bot.reset_conflicting_states(user_id, keep={'editing_product_title'})
            bot.state_manager.update_state(user_id, editing_product_title=product_id)

            await self._safe_transition_to_text(
                query,
                f"📝 **Modifier le titre de:** {product.get('title', 'N/A')}\n\n"
                f"Entrez le nouveau titre:" if lang == 'fr' else
                f"📝 **Edit title for:** {product.get('title', 'N/A')}\n\n"
                f"Enter new title:",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                ]])
            )

        except Exception as e:
            logger.error(f"Error in edit_product_title_prompt: {e}")
            await self._safe_transition_to_text(
                query,
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
            )

    async def toggle_product_status(self, bot, query, product_id, lang):
        """Toggle product active/inactive status"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = bot.get_seller_id(query.from_user.id)

            # Get product and verify ownership
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await self._safe_transition_to_text(
                    query,
                    "❌ Produit non trouvé ou non autorisé." if lang == 'fr' else "❌ Product not found or unauthorized.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                    ]])
                )
                return

            # Toggle status
            current_status = product.get('status', 'active')
            new_status = 'inactive' if current_status == 'active' else 'active'

            success = self.product_repo.update_status(product_id, new_status)

            if success:
                status_text = "activé" if new_status == 'active' else "désactivé"
                status_text_en = "activated" if new_status == 'active' else "deactivated"
                await self._safe_transition_to_text(
                    query,
                    f"✅ Produit {status_text} avec succès." if lang == 'fr' else f"✅ Product {status_text_en} successfully.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data=f'edit_product_{product_id}')
                    ]])
                )
            else:
                await self._safe_transition_to_text(
                    query,
                    "❌ Erreur lors de la mise à jour." if lang == 'fr' else "❌ Update error.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data=f'edit_product_{product_id}')
                    ]])
                )

        except Exception as e:
            logger.error(f"Error in toggle_product_status: {e}")
            await self._safe_transition_to_text(
                query,
                "❌ Erreur lors de la mise à jour." if lang == 'fr' else "❌ Update error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
            )
    async def process_product_title_update(self, bot, update, product_id: str, new_title: str, lang: str = 'fr') -> bool:
        """Process product title update"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = bot.get_seller_id(update.effective_user.id)

            # Validate ownership
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await update.message.reply_text(i18n(lang, 'err_product_not_found'))
                return False

            # Validate title - CORRECTION: 3 caractères minimum comme dans le message d'erreur
            if len(new_title) < 3 or len(new_title) > 100:
                await update.message.reply_text("❌ Le titre doit contenir entre 3 et 100 caractères.")
                return False

            # CORRECTION: Réinitialiser l'état AVANT la mise à jour
            bot.state_manager.reset_state(user_id, keep={'lang'})

            # Update title
            success = self.product_repo.update_title(product_id, user_id, new_title)

            if success:
                await update.message.reply_text(
                    i18n(lang, 'seller_name_updated'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_back_dashboard'), callback_data='seller_dashboard')
                    ]])
                )
                return True
            else:
                await update.message.reply_text(
                    i18n(lang, 'err_update_error'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_back_dashboard'), callback_data='seller_dashboard')
                    ]])
                )
                return False

        except Exception as e:
            logger.error(f"Erreur maj titre produit: {e}")
            # CORRECTION: Réinitialiser l'état même en cas d'erreur
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text(i18n(lang, 'err_update_error'))
            return False
    
    async def process_product_price_update(self, bot, update, product_id: str, price_text: str, lang: str = 'fr') -> bool:
        """Process product price update with consolidated logic"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = bot.get_seller_id(update.effective_user.id)

            # Validate ownership
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await update.message.reply_text(i18n(lang, 'err_product_not_found'))
                return False

            # Parse and validate price
            price = float(price_text.replace(',', '.'))
            if price < 1 or price > 5000:
                raise ValueError("Prix hors limites")

            # Calculate USD price
            price_usd = price * bot.payment_service.get_exchange_rate()

            # Update price
            success = self.product_repo.update_price(product_id, user_id, price, price_usd)

            if success:
                await update.message.reply_text(
                    i18n(lang, 'success_price_updated'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_back_dashboard'), callback_data='seller_dashboard')
                    ]])
                )
                return True
            else:
                await update.message.reply_text(
                    i18n(lang, 'err_update_error'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_back_dashboard'), callback_data='seller_dashboard')
                    ]])
                )
                return False

        except ValueError as e:
            await update.message.reply_text(i18n(lang, 'err_invalid_price'))
            return False
        except Exception as e:
            logger.error(f"Erreur maj prix produit: {e}")
            await update.message.reply_text(i18n(lang, 'err_price_update_error'))
            return False