"""
Callback Router - Routage centralisé des callbacks Telegram
"""
from typing import Dict, Any, Callable
from telegram import CallbackQuery
import logging

logger = logging.getLogger(__name__)

class CallbackRouter:
    """Routeur centralisé pour les callbacks Telegram"""

    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.routes: Dict[str, Callable] = {}
        self._setup_routes()

    def _setup_routes(self):
        """Configure les routes de callbacks"""
        # Navigation principale
        self.routes.update({
            'buy_menu': lambda query, lang: self.bot.buy_handlers.buy_menu(self.bot, query, lang),
            'sell_menu': lambda query, lang: self.bot.sell_handlers.sell_menu(self.bot, query, lang),
            'seller_login_menu': lambda query, lang: self.bot.sell_handlers.seller_login_menu(self.bot, query, lang),
            'seller_dashboard': lambda query, lang: self.bot.sell_handlers.seller_dashboard(self.bot, query, lang),
            'back_main': lambda query, lang: self.bot.core_handlers.back_to_main_with_bot(self.bot, query, lang),
        })

        # Routes admin - signatures corrigées
        admin_routes = {
            'admin_menu': lambda query, lang: self.bot.admin_handlers.admin_menu(self.bot, query, lang),
            'admin_users_menu': lambda query, lang: self.bot.admin_handlers.admin_users_menu(query, lang),
            'admin_products_menu': lambda query, lang: self.bot.admin_handlers.admin_products_menu(query, lang),
            'admin_users': lambda query, lang: self.bot.admin_handlers.admin_users(query, lang),
            'admin_products': lambda query, lang: self.bot.admin_handlers.admin_products(query, lang),
            'admin_payouts': lambda query, lang: self.bot.admin_handlers.admin_payouts(query, lang),
            'admin_marketplace_stats': lambda query, lang: self.bot.admin_handlers.admin_marketplace_stats(query, lang),
            'admin_search_user': lambda query, lang: self.bot.admin_handlers.admin_search_user_prompt(query, lang),
            'admin_search_product': lambda query, lang: self.bot.admin_handlers.admin_search_product_prompt(query, lang),
            'admin_suspend_product': lambda query, lang: self.bot.admin_handlers.admin_suspend_product_prompt(query, lang),
            'admin_suspend_user': lambda query, lang: self.bot.admin_handlers.admin_suspend_user_prompt(self.bot, query, lang),
            'admin_restore_user': lambda query, lang: self.bot.admin_handlers.admin_restore_user_prompt(self.bot, query, lang),
            'admin_mark_all_payouts_paid': lambda query, lang: self.bot.admin_handlers.admin_mark_all_payouts_paid(query, lang),
            'admin_export_users': lambda query, lang: self.bot.admin_handlers.admin_export_users(query, lang),
            'admin_export_payouts': lambda query, lang: self.bot.admin_handlers.admin_export_payouts(query, lang),
            'admin_export_products': lambda query, lang: self.bot.admin_handlers.export_products(query, lang),
            'admin_export_products_csv': lambda query, lang: self.bot.admin_handlers.admin_export_products_csv(query, lang),
        }
        self.routes.update(admin_routes)

        # Routes vente
        sell_routes = {
            'create_seller': lambda query, lang: self.bot.sell_handlers.create_seller_prompt(self.bot, query, lang),
            'add_product': lambda query, lang: self.bot.sell_handlers.add_product_prompt(self.bot, query, lang),
            'my_products': lambda query, lang: self.bot.sell_handlers.show_my_products(self.bot, query, lang),
            'my_wallet': lambda query, lang: self.bot.sell_handlers.show_wallet(self.bot, query, lang),
            'seller_logout': lambda query, lang: self.bot.sell_handlers.seller_logout(self.bot, query),
            'delete_seller': lambda query, lang: self.bot.sell_handlers.delete_seller_prompt(self.bot, query),
            'delete_seller_confirm': lambda query, lang: self.bot.sell_handlers.delete_seller_confirm(self.bot, query),
            'seller_analytics': lambda query, lang: self.bot.sell_handlers.seller_analytics(self.bot, query, lang),
            'seller_analytics_visual': lambda query, lang: self.bot.sell_handlers.seller_analytics_visual(self.bot, query, lang),
            'seller_settings': lambda query, lang: self.bot.sell_handlers.seller_settings(self.bot, query, lang),
            'seller_info': self._handle_seller_info,
            'sell_payout_history': lambda query, lang: self.bot.sell_handlers.payout_history(self.bot, query, lang),
            'sell_copy_address': lambda query, lang: self.bot.sell_handlers.copy_address(self.bot, query, lang),
            'edit_seller_name': lambda query, lang: self.bot.sell_handlers.edit_seller_name(self.bot, query, lang),
            'edit_seller_bio': lambda query, lang: self.bot.sell_handlers.edit_seller_bio(self.bot, query, lang),
        }
        self.routes.update(sell_routes)

        # Routes Analytics (Advanced)
        analytics_routes = {
            'analytics_dashboard': self._handle_analytics_dashboard,
            'analytics_refresh': self._handle_analytics_refresh,
            'analytics_products': self._handle_analytics_products,
            'analytics_recommendations': self._handle_analytics_recommendations,
            'analytics_charts': lambda query, lang: self.bot.sell_handlers.seller_analytics_visual(self.bot, query, lang),
        }
        self.routes.update(analytics_routes)

        # Routes achat
        buy_routes = {
            'search_product': lambda query, lang: self.bot.buy_handlers.search_product_prompt(self.bot, query, lang),
            'browse_categories': lambda query, lang: self.bot.buy_handlers.browse_categories(self.bot, query, lang),
        }
        self.routes.update(buy_routes)

        # Routes bibliothèque
        library_routes = {
            'library_menu': lambda query, lang: self.bot.library_handlers.show_library(self.bot, query, lang),
            'library': lambda query, lang: self.bot.library_handlers.show_library(self.bot, query, lang),
        }
        self.routes.update(library_routes)

        # Routes support - signatures corrigées
        support_routes = {
            'support_menu': lambda query, lang: self.bot.support_handlers.support_menu(query, lang),
            'create_ticket': lambda query, lang: self.bot.support_handlers.create_ticket_prompt(self.bot, query, lang),
            'my_tickets': lambda query, lang: self.bot.support_handlers.my_tickets(query, lang),
        }
        self.routes.update(support_routes)

        # Routes auth/recovery - signatures corrigées
        auth_routes = {
            'account_recovery': lambda query, lang: self.bot.auth_handlers.account_recovery_menu(self.bot, query, lang),
            'recovery_by_email': lambda query, lang: self.bot.auth_handlers.recovery_by_email_prompt(self.bot, query, lang),
            'seller_login': lambda query, lang: self.bot.sell_handlers.seller_login_prompt(self.bot, query, lang),
        }
        self.routes.update(auth_routes)

        # Routes langues
        lang_routes = {
            'lang_fr': lambda query, lang: self.bot.core_handlers.change_language(self.bot, query, 'fr'),
            'lang_en': lambda query, lang: self.bot.core_handlers.change_language(self.bot, query, 'en'),
        }
        self.routes.update(lang_routes)

    async def route(self, query: CallbackQuery) -> bool:
        """
        Route un callback vers le handler approprié

        Returns:
            bool: True si le callback a été routé, False sinon
        """
        callback_data = query.data
        user_id = query.from_user.id
        lang = self.bot.get_user_language(user_id)

        logger.info(f"DEBUG: Routing callback: {callback_data} for user {user_id}")
        logger.debug(f"Routing callback: {callback_data} for user {user_id}")

        # Handle state-setting admin routes
        if callback_data == 'admin_search_user':
            self.bot.reset_conflicting_states(user_id, keep={'admin_search_user'})
            self.bot.update_user_state(user_id, admin_search_user=True)
        elif callback_data == 'admin_search_product':
            self.bot.reset_conflicting_states(user_id, keep={'admin_search_product'})
            self.bot.update_user_state(user_id, admin_search_product=True)
        elif callback_data == 'admin_suspend_product':
            self.bot.reset_conflicting_states(user_id, keep={'admin_suspend_product'})
            self.bot.update_user_state(user_id, admin_suspend_product=True)
        # admin_suspend_user is handled by the route above

        # Noop handler (boutons espaceurs non-cliquables)
        if callback_data == 'noop':
            await query.answer()  # Juste acknowledge, ne fait rien
            return True

        # Route directe
        if callback_data in self.routes:
            try:
                await self.routes[callback_data](query, lang)
                return True
            except Exception as e:
                logger.error(f"Error routing {callback_data}: {e}")
                await self._handle_error(query, callback_data, e)
                return True

        # Routes avec patterns
        if await self._route_patterns(query, callback_data, lang):
            return True

        # Routes avec préfixes
        if await self._route_prefixes(query, callback_data, lang):
            return True

        logger.warning(f"No route found for callback: {callback_data}")
        return False

    async def _route_patterns(self, query: CallbackQuery, callback_data: str, lang: str) -> bool:
        """Route les callbacks avec patterns spécifiques"""

        # 🎠 Phase 2: Carousel navigation (carousel_{category}_{index})
        if callback_data.startswith('carousel_'):
            try:
                # Parse: carousel_FinanceCrypto_2
                parts = callback_data.replace('carousel_', '').rsplit('_', 1)
                category = parts[0]
                index = int(parts[1])

                # Get products for category
                products = self.bot.buy_handlers.product_repo.get_products_by_category(category, limit=100, offset=0)

                if products:
                    await self.bot.buy_handlers.show_product_carousel(
                        self.bot, query, category, products, index, lang
                    )
                else:
                    await query.answer("No products found" if lang == 'en' else "Aucun produit trouvé")

                return True
            except Exception as e:
                logger.error(f"Error in carousel navigation: {e}")
                await query.answer("Error" if lang == 'en' else "Erreur")
                return True

        # 🎠 Seller product carousel navigation (seller_carousel_{index})
        if callback_data.startswith('seller_carousel_'):
            try:
                index = int(callback_data.replace('seller_carousel_', ''))
                seller_id = self.bot.get_seller_id(query.from_user.id)
                products = self.bot.sell_handlers.product_repo.get_products_by_seller(seller_id, limit=100, offset=0)

                if products:
                    await self.bot.sell_handlers.show_seller_product_carousel(
                        self.bot, query, products, index, lang
                    )
                else:
                    await query.answer("No products found" if lang == 'en' else "Aucun produit trouvé")

                return True
            except Exception as e:
                logger.error(f"Error in seller carousel navigation: {e}")
                await query.answer("Error" if lang == 'en' else "Erreur")
                return True

        # 🎠 Library carousel navigation (library_carousel_{index})
        if callback_data.startswith('library_carousel_'):
            try:
                index = int(callback_data.replace('library_carousel_', ''))
                user_id = query.from_user.id

                # Get all purchases for this user
                conn = self.bot.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                   SELECT
                        p.product_id,
                        p.title,
                        p.description,
                        p.price_eur,
                        p.thumbnail_path,
                        p.category,
                        p.file_size_mb,
                        COALESCE(u.seller_name, u.first_name) as seller_name,
                        MAX(o.completed_at) as completed_at,
                        o.download_count
                    FROM orders o
                    JOIN products p ON o.product_id = p.product_id
                    JOIN users u ON p.seller_user_id = u.user_id
                    WHERE o.buyer_user_id = ? AND o.payment_status = 'completed'
                    GROUP BY p.product_id, p.title, p.description, p.price_eur, p.thumbnail_path, p.category, p.file_size_mb, u.seller_name
                    ORDER BY MAX(o.completed_at) DESC
                ''', (user_id,))
                purchases_raw = cursor.fetchall()
                conn.close()

                # Convert to dict
                purchases = []
                for row in purchases_raw:
                    purchases.append({
                        'product_id': row[0],
                        'title': row[1],
                        'description': row[2],
                        'price_eur': row[3],
                        'thumbnail_path': row[4],
                        'category': row[5],
                        'file_size_mb': row[6],
                        'seller_name': row[7],
                        'completed_at': row[8],
                        'download_count': row[9]
                    })

                if purchases:
                    await self.bot.library_handlers.show_library_carousel(
                        self.bot, query, purchases, index, lang
                    )
                else:
                    await query.answer("No products found" if lang == 'en' else "Aucun produit trouvé")

                return True
            except Exception as e:
                logger.error(f"Error in library carousel navigation: {e}")
                await query.answer("Error" if lang == 'en' else "Erreur")
                return True

        # Categories with pagination
        if callback_data.startswith('category_'):
            # Check if it's a pagination callback
            if '_page_' in callback_data:
                parts = callback_data.split('_page_')
                category = parts[0].replace('category_', '')
                page = int(parts[1])
                await self.bot.buy_handlers.show_category_products(self.bot, query, category, lang, page)
            else:
                category = callback_data.replace('category_', '')
                await self.bot.buy_handlers.show_category_products(self.bot, query, category, lang)
            return True

        # Product details (product_details_{product_id})
        if callback_data.startswith('product_details_'):
            product_id = callback_data.replace('product_details_', '')
            await self.bot.buy_handlers.show_product_details(self.bot, query, product_id, lang)
            return True

        # Product preview (product_preview_{product_id})
        if callback_data.startswith('product_preview_'):
            product_id = callback_data.replace('product_preview_', '')
            await self.bot.buy_handlers.preview_product(query, product_id, lang)
            return True

        # Products (legacy route)
        if callback_data.startswith('product_'):
            product_id = callback_data.replace('product_', '')
            await self.bot.buy_handlers.show_product_details(self.bot, query, product_id, lang)
            return True

        # Downloads - redirect to library handler for purchased products
        if callback_data.startswith('download_product_'):
            product_id = callback_data.replace('download_product_', '')
            await self.bot.library_handlers.download_product(self.bot, query, None, product_id, lang)
            return True

        # Buy product
        if callback_data.startswith('buy_product_'):
            product_id = callback_data.replace('buy_product_', '')
            await self.bot.buy_handlers.buy_product(self.bot, query, product_id, lang)
            return True

        # Preview product
        if callback_data.startswith('preview_product_'):
            product_id = callback_data.replace('preview_product_', '')
            await self.bot.buy_handlers.preview_product(query, product_id, lang)
            return True

        # Mark payment as paid (test feature)
        if callback_data.startswith('mark_paid_'):
            product_id = callback_data.replace('mark_paid_', '')
            await self.bot.buy_handlers.mark_as_paid(self.bot, query, product_id, lang)
            return True

        # Seller products pagination
        if callback_data.startswith('my_products_page_'):
            page = int(callback_data.replace('my_products_page_', ''))
            await self.bot.sell_handlers.show_my_products(self.bot, query, lang, page)
            return True

        # Edit product fields
        if callback_data.startswith('edit_field_'):
            await self._handle_edit_field(query, callback_data, lang)
            return True

        # Product actions
        if callback_data.startswith(('confirm_delete_', 'delete_product_', 'edit_product_')):
            await self._handle_product_action(query, callback_data, lang)
            return True

        # Support/messaging (contact_seller removed - handled by library_handlers)
        if callback_data.startswith(('view_ticket_', 'reply_ticket_', 'escalate_ticket_')):
            await self._handle_support_action(query, callback_data, lang)
            return True

        # Product category selection during creation
        if callback_data.startswith('add_product_category_'):
            category_index = int(callback_data.replace('add_product_category_', ''))
            await self.bot.sell_handlers.handle_category_selection(self.bot, query, category_index, lang)
            return True

        # Skip cover image during product creation
        if callback_data == 'skip_cover_image':
            await self.bot.sell_handlers.handle_skip_cover_image(self.bot, query)
            return True

        # Product creation - Cancel
        if callback_data == 'product_cancel':
            await self.bot.sell_handlers.handle_product_cancel(self.bot, query, lang)
            return True

        # Product creation - Back to previous step
        if callback_data.startswith('product_back_'):
            step = callback_data.replace('product_back_', '')
            await self.bot.sell_handlers.handle_product_back(self.bot, query, step, lang)
            return True

        # Crypto payment selection
        if callback_data.startswith('pay_crypto_'):
            parts = callback_data.replace('pay_crypto_', '').split('_')
            if len(parts) >= 2:
                crypto_code = parts[0]
                product_id = '_'.join(parts[1:])
                await self.bot.buy_handlers.process_crypto_payment(self.bot, query, crypto_code, product_id, lang)
                return True

        # Payment status check
        if callback_data.startswith('check_payment_'):
            order_id = callback_data.replace('check_payment_', '')
            await self.bot.buy_handlers.check_payment_handler(self.bot, query, order_id, lang)
            return True

        # Payment refresh
        if callback_data.startswith('refresh_payment_'):
            order_id = callback_data.replace('refresh_payment_', '')
            await self.bot.buy_handlers.check_payment_handler(self.bot, query, order_id, lang)
            return True

        # Admin reply to ticket
        if callback_data.startswith('admin_reply_ticket_'):
            ticket_id = callback_data.replace('admin_reply_ticket_', '')
            await self.bot.support_handlers.admin_reply_ticket_prompt(query, ticket_id)
            return True

        # Library item view
        if callback_data.startswith('library_item_'):
            product_id = callback_data.replace('library_item_', '')
            await self.bot.library_handlers.show_library_item(self.bot, query, product_id, lang)
            return True

        # Review product
        if callback_data.startswith('review_product_'):
            product_id = callback_data.replace('review_product_', '')
            await self.bot.library_handlers.write_review_prompt(self.bot, query, product_id, lang)
            return True

        # ════════════════════════════════════════════════════════════════
        # ANALYTICS ROUTES (AI-Powered Features)
        # ════════════════════════════════════════════════════════════════

        # Main analytics dashboard
        if callback_data == 'analytics_dashboard':
            user_id = query.from_user.id
            await self.bot.analytics_handlers.show_analytics_dashboard(self.bot, query, user_id, lang)
            return True

        # Products with performance scores
        if callback_data == 'analytics_products':
            user_id = query.from_user.id
            await self.bot.analytics_handlers.show_products_with_scores(self.bot, query, user_id, lang)
            return True

        # Recommendations view
        if callback_data == 'analytics_recommendations':
            user_id = query.from_user.id
            await self.bot.analytics_handlers.show_recommendations(self.bot, query, user_id, lang)
            return True

        # Charts view
        if callback_data == 'analytics_charts':
            user_id = query.from_user.id
            await self.bot.analytics_handlers.show_charts(self.bot, query, user_id, lang)
            return True

        # Refresh analytics (re-show dashboard)
        if callback_data == 'analytics_refresh':
            user_id = query.from_user.id
            await self.bot.analytics_handlers.show_analytics_dashboard(self.bot, query, user_id, lang)
            return True

        # Product performance detail
        if callback_data.startswith('perf_'):
            product_id = callback_data.replace('perf_', '')
            await self.bot.analytics_handlers.show_product_performance(self.bot, query, product_id, lang)
            return True

        # Apply AI-suggested price (one-click optimization)
        if callback_data.startswith('apply_price_'):
            # Format: apply_price_{product_id}_{new_price}
            parts = callback_data.split('_')
            if len(parts) >= 4:
                product_id = '_'.join(parts[2:-1])  # Handle TBF-XXXX-XXXXXX format
                new_price = float(parts[-1])
                user_id = query.from_user.id
                await self.bot.analytics_handlers.apply_smart_price(self.bot, query, product_id, new_price, user_id)
                return True

        # Library pagination
        if callback_data.startswith('library_page_'):
            page = int(callback_data.replace('library_page_', ''))
            await self.bot.library_handlers.show_library(self.bot, query, lang, page)
            return True

        # Rate product
        if callback_data.startswith('rate_product_'):
            product_id = callback_data.replace('rate_product_', '')
            await self.bot.library_handlers.rate_product_prompt(self.bot, query, product_id, lang)
            return True

        # Set rating
        if callback_data.startswith('set_rating_'):
            parts = callback_data.replace('set_rating_', '').split('_')
            if len(parts) >= 2:
                product_id = '_'.join(parts[:-1])
                rating = int(parts[-1])
                await self.bot.library_handlers.set_rating(self.bot, query, product_id, rating, lang)
            return True

        # Write review
        if callback_data.startswith('write_review_'):
            product_id = callback_data.replace('write_review_', '')
            await self.bot.library_handlers.write_review_prompt(self.bot, query, product_id, lang)
            return True

        # Contact seller from library
        if callback_data.startswith('contact_seller_'):
            product_id = callback_data.replace('contact_seller_', '')
            await self.bot.library_handlers.contact_seller(self.bot, query, product_id, lang)
            return True

        # Message seller (creates support ticket)
        if callback_data.startswith('message_seller_'):
            parts = callback_data.replace('message_seller_', '').split('_')
            if len(parts) >= 2:
                seller_user_id = int(parts[0])
                product_id = '_'.join(parts[1:])
                await self.bot.library_handlers.message_seller(self.bot, query, seller_user_id, product_id, lang)
            return True

        return False

    async def _route_prefixes(self, query: CallbackQuery, callback_data: str, lang: str) -> bool:
        """Route les callbacks avec préfixes"""

        # Routes buy_*
        if callback_data.startswith('buy_'):
            return await self._route_to_handler(self.bot.buy_handlers, query, callback_data, lang)

        # Routes sell_*
        if callback_data.startswith('sell_'):
            return await self._route_to_handler(self.bot.sell_handlers, query, callback_data, lang)

        # Routes admin_*
        if callback_data.startswith('admin_'):
            return await self._route_to_handler(self.bot.admin_handlers, query, callback_data, lang)

        # Routes support_*
        if callback_data.startswith('support_'):
            return await self._route_to_handler(self.bot.support_handlers, query, callback_data, lang)

        return False

    async def _route_to_handler(self, handler, query: CallbackQuery, callback_data: str, lang: str) -> bool:
        """Route vers un handler spécifique"""
        method_name = callback_data.replace('_', '_', 1)  # Garde le premier underscore

        if hasattr(handler, method_name):
            try:
                method = getattr(handler, method_name)
                await method(self.bot, query, lang)
                return True
            except Exception as e:
                logger.error(f"Error calling {method_name}: {e}")
                await self._handle_error(query, callback_data, e)
                return True

        return False

    async def _handle_edit_field(self, query: CallbackQuery, callback_data: str, lang: str):
        """Gère l'édition des champs produit"""
        parts = callback_data.split('_')
        if len(parts) >= 4:
            field_type = parts[2]  # title, price, toggle
            product_id = '_'.join(parts[3:])

            if field_type == 'title':
                await self.bot.sell_handlers.edit_product_title_prompt(self.bot, query, product_id, lang)
            elif field_type == 'price':
                await self.bot.sell_handlers.edit_product_price_prompt(self.bot, query, product_id, lang)
            elif field_type == 'toggle':
                await self.bot.sell_handlers.toggle_product_status(self.bot, query, product_id, lang)

    async def _handle_product_action(self, query: CallbackQuery, callback_data: str, lang: str):
        """Gère les actions sur les produits"""
        if callback_data.startswith('confirm_delete_'):
            product_id = callback_data.replace('confirm_delete_', '')
            await self.bot.sell_handlers.confirm_delete_product(self.bot, query, product_id, lang)
        elif callback_data.startswith('delete_product_'):
            product_id = callback_data.replace('delete_product_', '')
            await self.bot.sell_handlers.confirm_delete_product(self.bot, query, product_id, lang)
        elif callback_data.startswith('toggle_product_'):
            product_id = callback_data.replace('toggle_product_', '')
            await self.bot.sell_handlers.toggle_product_status(self.bot, query, product_id, lang)
        elif callback_data.startswith('edit_product_'):
            product_id = callback_data.replace('edit_product_', '')
            await self.bot.sell_handlers.edit_product_menu(self.bot, query, product_id, lang)

    async def _handle_support_action(self, query: CallbackQuery, callback_data: str, lang: str):
        """Gère les actions de support (contact_seller handled by library_handlers)"""
        if callback_data.startswith('view_ticket_'):
            ticket_id = callback_data.replace('view_ticket_', '')
            await self.bot.support_handlers.view_ticket(self.bot, query, ticket_id)
        elif callback_data.startswith('reply_ticket_'):
            ticket_id = callback_data.replace('reply_ticket_', '')
            await self.bot.support_handlers.reply_ticket_prepare(self.bot, query, ticket_id)
        elif callback_data.startswith('escalate_ticket_'):
            ticket_id = callback_data.replace('escalate_ticket_', '')
            await self.bot.support_handlers.escalate_ticket(self.bot, query, ticket_id)

    async def _handle_seller_info(self, query: CallbackQuery, lang: str):
        """Gère l'affichage des infos vendeur"""
        from app.core.i18n import t as i18n
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        await query.edit_message_text(
            "🏪 Informations vendeur bientôt disponibles...",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='sell_menu')
            ]])
        )

    async def _handle_error(self, query: CallbackQuery, callback_data: str, error: Exception):
        """Gère les erreurs de routage"""
        from app.core.i18n import t as i18n
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        logger.error(f"Callback error for {callback_data}: {error}")

        try:
            lang = self.bot.get_user_language(query.from_user.id)
            await query.edit_message_text(
                i18n(lang, 'err_temp'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')
                ]])
            )
        except Exception as e:
            logger.error(f"Error handling error: {e}")

    async def _handle_edit_field(self, query: CallbackQuery, callback_data: str, lang: str):
        """Handle edit field callbacks like edit_field_price_PRODUCT_ID"""
        try:
            # Parse callback: edit_field_FIELD_PRODUCT_ID
            parts = callback_data.split('_', 3)  # ['edit', 'field', 'price', 'TBF-2509-2B8BCC']
            if len(parts) >= 4:
                field = parts[2]  # 'price'
                product_id = parts[3]  # 'TBF-2509-2B8BCC'

                # Route to sell handlers for product editing
                await self.bot.sell_handlers.edit_product_field(self.bot, query, field, product_id, lang)
            else:
                logger.error(f"Invalid edit_field callback format: {callback_data}")
                await self._handle_error(query, callback_data, "Invalid callback format")
        except Exception as e:
            logger.error(f"Error handling edit field {callback_data}: {e}")
            await self._handle_error(query, callback_data, e)

    # Dynamic route management methods removed - never used (15 lines removed)
    # ═══════════════════════════════════════════════════════
    # ANALYTICS HANDLERS
    # ═══════════════════════════════════════════════════════

    async def _handle_analytics_dashboard(self, query: CallbackQuery, lang: str):
        """Affiche le dashboard analytics IA"""
        seller_id = self.bot.get_seller_id(query.from_user.id)
        await self.bot.analytics_handlers.show_analytics_dashboard(
            self.bot, query, seller_id, lang
        )

    async def _handle_analytics_refresh(self, query: CallbackQuery, lang: str):
        """Rafraîchit le dashboard analytics"""
        seller_id = self.bot.get_seller_id(query.from_user.id)
        await self.bot.analytics_handlers.show_analytics_dashboard(
            self.bot, query, seller_id, lang
        )

    async def _handle_analytics_products(self, query: CallbackQuery, lang: str):
        """Affiche la liste des produits avec scores de performance"""
        seller_id = self.bot.get_seller_id(query.from_user.id)
        await self.bot.analytics_handlers.show_products_with_scores(
            self.bot, query, seller_id, lang
        )

    async def _handle_analytics_recommendations(self, query: CallbackQuery, lang: str):
        """Affiche les recommandations IA pour améliorer les ventes"""
        seller_id = self.bot.get_seller_id(query.from_user.id)
        await self.bot.analytics_handlers.show_recommendations(
            self.bot, query, seller_id, lang
        )
