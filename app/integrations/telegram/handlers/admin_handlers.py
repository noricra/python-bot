"""Admin Handlers - Administration functions with dependency injection"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.core.i18n import t as i18n
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
from app.core.settings import settings
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

class AdminHandlers:
    def __init__(self, user_repo, product_repo, order_repo, payout_service):
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.payout_service = payout_service

    async def admin_menu(self, bot, query, lang):
        """Menu principal admin"""
        # 🔧 FIX: Réinitialiser TOUS les états quand on entre dans l'admin
        user_id = query.from_user.id
        bot.reset_user_state(user_id, keep={'lang'})

        admin_keyboard = [
            [InlineKeyboardButton(" Users", callback_data='admin_users_menu'),
             InlineKeyboardButton(" Products", callback_data='admin_products_menu')],
            [InlineKeyboardButton(i18n(lang, 'admin_payouts'), callback_data='admin_payouts'),
             InlineKeyboardButton(i18n(lang, 'admin_stats'), callback_data='admin_marketplace_stats')],
            [InlineKeyboardButton(i18n(lang, 'admin_back'), callback_data='back_main')]
        ]

        await query.edit_message_text(
            "🔧 **ADMINISTRATION**\n\nChoisissez une section :",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown')

    async def admin_users_menu(self, query, lang):
        """Menu gestion utilisateurs"""
        # 🔧 FIX: Réinitialiser les états admin users
        from bot_mlt import MarketplaceBot
        # On ne peut pas accéder à bot ici, mais ce menu est déjà safe car appelé depuis admin_menu
        users_keyboard = [
            [InlineKeyboardButton(" Gérer utilisateurs", callback_data='admin_users')],
            [InlineKeyboardButton(" Suspendre user", callback_data='admin_suspend_user'),
             InlineKeyboardButton(" Rétablir user", callback_data='admin_restore_user')],
            [InlineKeyboardButton(" Export users", callback_data='admin_export_users')],
            [InlineKeyboardButton(" Retour admin", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            "👥 **GESTION UTILISATEURS**\n\nChoisissez une action :",
            reply_markup=InlineKeyboardMarkup(users_keyboard),
            parse_mode='Markdown')

    async def admin_products_menu(self, query, lang):
        """Menu gestion produits"""
        products_keyboard = [
            [InlineKeyboardButton(" Voir produits", callback_data='admin_products'),
             InlineKeyboardButton(" Rechercher produit", callback_data='admin_search_product')],
            [InlineKeyboardButton(" Suspendre produit", callback_data='admin_suspend_product'),
             InlineKeyboardButton(" Rétablir produit", callback_data='admin_restore_product')],
            [InlineKeyboardButton(" Export produits", callback_data='admin_export_products_csv')],
            [InlineKeyboardButton(" Retour admin", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            " **GESTION PRODUITS**\n\nChoisissez une action :",
            reply_markup=InlineKeyboardMarkup(products_keyboard),
            parse_mode='Markdown')

    async def admin_users(self, query, lang):
        """Gestion utilisateurs - Liste et recherche unifiées"""
        try:
            users = self.user_repo.get_all_users(limit=50)  # Increased limit
            text = "👥 **GESTION DES UTILISATEURS**\n\n" if lang == 'fr' else "👥 **USER MANAGEMENT**\n\n"

            if not users:
                text += "Aucun utilisateur trouvé." if lang == 'fr' else "No users found."
            else:
                text += f"📊 Total: {len(users)} utilisateurs\n\n" if lang == 'fr' else f"📊 Total: {len(users)} users\n\n"

                for i, user in enumerate(users[:30], 1):  # Show first 30 for readability
                    status = "🟢 Vendeur" if user.get('is_seller') else "🔵 Acheteur"
                    status_en = "🟢 Seller" if user.get('is_seller') else "🔵 Buyer"
                    display_status = status if lang == 'fr' else status_en

                    username = user.get('username', 'N/A')
                    first_name = user.get('first_name', 'N/A')

                    # Fix datetime subscriptable error
                    reg_date = user.get('registration_date')
                    if reg_date:
                        registration_date = str(reg_date)[:10] if isinstance(reg_date, str) else reg_date.strftime('%Y-%m-%d')
                    else:
                        registration_date = 'N/A'

                    # Additional stats
                    total_sales = user.get('total_sales', 0)
                    total_revenue = user.get('total_revenue', 0.0)
                    is_suspended = user.get('is_suspended', False)
                    suspended_icon = " 🚫" if is_suspended else ""

                    text += f"**{i}.** {display_status}{suspended_icon}\n"
                    text += f"   • ID: `{user['user_id']}`\n"
                    text += f"   • Nom: {first_name}\n" if lang == 'fr' else f"   • Name: {first_name}\n"
                    text += f"   • Username: @{username}\n" if username != 'N/A' else ""

                    if user.get('is_seller'):
                        text += f"   • Ventes: {total_sales} | Revenus: {total_revenue:.2f}$\n" if lang == 'fr' else f"   • Sales: {total_sales} | Revenue: {total_revenue:.2f}$\n"

                    text += f"   • Inscrit: {registration_date}\n\n" if lang == 'fr' else f"   • Registered: {registration_date}\n\n"

                if len(users) > 30:
                    text += f"... et {len(users) - 30} autres utilisateurs\n" if lang == 'fr' else f"... and {len(users) - 30} more users\n"

            # Add action buttons
            text += "\n💡 Cliquez sur un utilisateur pour voir les actions" if lang == 'fr' else "\n💡 Click on a user to see actions"

            # Create user buttons (show first 8 users as buttons)
            keyboard = []
            for i, user in enumerate(users[:8], 1):
                user_id = user['user_id']
                username = user.get('username', user.get('first_name', f'User_{user_id}'))
                is_suspended = user.get('is_suspended', False)
                emoji = "🚫" if is_suspended else ("🟢" if user.get('is_seller') else "🔵")

                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {username[:20]}",
                        callback_data=f'admin_user_detail_{user_id}'
                    )
                ])

            # Navigation buttons
            keyboard.append([
                InlineKeyboardButton("🔍 Rechercher ID" if lang == 'fr' else "🔍 Search ID", callback_data='admin_search_user'),
                InlineKeyboardButton("📊 Export CSV", callback_data='admin_export_users')
            ])
            keyboard.append([
                InlineKeyboardButton("🔙 Menu Users" if lang == 'fr' else "🔙 Users Menu", callback_data='admin_users_menu')
            ])

            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in admin_users: {e}")
            await query.edit_message_text(
                f"❌ Erreur lors du chargement des utilisateurs: {str(e)}" if lang == 'fr' else f"❌ Error loading users: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )

    async def admin_user_detail(self, query, lang, user_id: int):
        """Détails et actions pour un utilisateur spécifique"""
        try:
            user = self.user_repo.get_user(user_id)

            if not user:
                await query.edit_message_text(
                    f"❌ Utilisateur {user_id} introuvable." if lang == 'fr' else f"❌ User {user_id} not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='admin_users')
                    ]])
                )
                return

            # Format dates
            reg_date = user.get('registration_date')
            registration_date = reg_date.strftime('%Y-%m-%d') if reg_date else 'N/A'

            suspended_at = user.get('suspended_at')
            suspended_date = suspended_at.strftime('%Y-%m-%d') if suspended_at else 'N/A'

            # Build user info
            is_seller = user.get('is_seller', False)
            is_suspended = user.get('is_suspended', False)
            status_icon = "🚫 SUSPENDU" if is_suspended else ("🟢 Vendeur" if is_seller else "🔵 Acheteur")

            text = f"👤 **DÉTAILS UTILISATEUR**\n\n"
            text += f"**Statut:** {status_icon}\n"
            text += f"**ID:** `{user_id}`\n"
            text += f"**Nom:** {user.get('first_name', 'N/A')}\n"
            text += f"**Username:** @{user.get('username', 'N/A')}\n"
            text += f"**Email:** {user.get('email', 'Non défini')}\n"
            text += f"**Inscrit le:** {registration_date}\n"

            if is_seller:
                text += f"\n**📊 STATS VENDEUR:**\n"
                text += f"• Nom vendeur: {user.get('seller_name', 'N/A')}\n"
                text += f"• Ventes totales: {user.get('total_sales', 0)}\n"
                text += f"• Revenus: ${user.get('total_revenue', 0):.2f}\n"
                text += f"• Note: {user.get('seller_rating', 0):.1f}/5\n"
                storage_used_mb = user.get('storage_used_mb', 0)
                storage_limit_gb = 10
                text += f"• Stockage: {storage_used_mb:.1f} MB / {storage_limit_gb} GB\n"

            if is_suspended:
                text += f"\n**⚠️ SUSPENSION:**\n"
                text += f"• Raison: {user.get('suspension_reason', 'Non spécifiée')}\n"
                text += f"• Date: {suspended_date}\n"
                until = user.get('suspended_until')
                if until:
                    until_str = until.strftime('%Y-%m-%d') if hasattr(until, 'strftime') else str(until)
                    text += f"• Jusqu'au: {until_str}\n"

            # Action buttons
            keyboard = []

            if is_suspended:
                keyboard.append([
                    InlineKeyboardButton("✅ Rétablir utilisateur", callback_data=f'admin_restore_user_confirm_{user_id}')
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton("🚫 Suspendre utilisateur", callback_data=f'admin_suspend_user_prompt_{user_id}')
                ])

            keyboard.append([
                InlineKeyboardButton("📧 Voir email complet", callback_data=f'admin_show_email_{user_id}'),
                InlineKeyboardButton("📊 Voir produits", callback_data=f'admin_user_products_{user_id}')
            ])

            keyboard.append([
                InlineKeyboardButton("🔙 Liste utilisateurs" if lang == 'fr' else "🔙 Users List", callback_data='admin_users')
            ])

            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in admin_user_detail: {e}")
            await query.edit_message_text(
                f"❌ Erreur: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data='admin_users')
                ]])
            )

    async def admin_suspend_user_prompt(self, query, lang, user_id: int):
        """Demander confirmation avant suspension"""
        user = self.user_repo.get_user(user_id)

        if not user:
            await query.answer("❌ Utilisateur introuvable", show_alert=True)
            return

        username = user.get('username') or user.get('first_name') or f"ID {user_id}"

        text = f"⚠️ **SUSPENDRE UTILISATEUR**\n\n"
        text += f"Utilisateur: {username}\n"
        text += f"ID: `{user_id}`\n\n"
        text += f"Entrez la raison de suspension puis la durée (en jours).\n\n"
        text += f"💡 Pour annuler, utilisez le bouton ci-dessous."

        keyboard = [
            [InlineKeyboardButton("❌ Annuler", callback_data=f'admin_user_detail_{user_id}')]
        ]

        # Set state for text input
        from bot_mlt import MarketplaceBot
        if hasattr(query, 'from_user'):
            admin_id = query.from_user.id
            # Use bot's state manager
            self.bot = MarketplaceBot() if not hasattr(self, 'bot') else self.bot
            # Note: This is a simplified approach - ideally should be handled via state
            await query.edit_message_text(
                f"🚫 **SUSPENSION EN DÉVELOPPEMENT**\n\n"
                f"Cette fonctionnalité nécessite l'input admin.\n"
                f"Pour l'instant, utilisez:\n\n"
                f"`/admin_suspend {user_id} <raison> <jours>`\n\n"
                f"Exemple: `/admin_suspend {user_id} spam 7`",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

    async def admin_restore_user_confirm(self, query, lang, user_id: int):
        """Rétablir un utilisateur suspendu"""
        try:
            user = self.user_repo.get_user(user_id)

            if not user:
                await query.answer("❌ Utilisateur introuvable", show_alert=True)
                return

            if not user.get('is_suspended'):
                await query.answer("ℹ️ Utilisateur non suspendu", show_alert=True)
                return

            # Restore user
            success = self.user_repo.restore_user(user_id)

            if success:
                username = user.get('username') or user.get('first_name') or f"ID {user_id}"

                await query.edit_message_text(
                    f"✅ **UTILISATEUR RÉTABLI**\n\n"
                    f"Utilisateur: {username}\n"
                    f"ID: `{user_id}`\n\n"
                    f"Le compte a été réactivé.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("👤 Détails user", callback_data=f'admin_user_detail_{user_id}'),
                        InlineKeyboardButton("🔙 Liste", callback_data='admin_users')
                    ]]),
                    parse_mode='Markdown'
                )

                # Notify user (optional)
                try:
                    await self.bot.bot.send_message(
                        chat_id=user_id,
                        text="✅ Votre compte a été rétabli. Vous pouvez à nouveau utiliser la plateforme."
                    )
                except Exception:
                    pass  # User might have blocked bot

            else:
                await query.answer("❌ Erreur lors du rétablissement", show_alert=True)

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in admin_restore_user_confirm: {e}")
            await query.answer("❌ Erreur système", show_alert=True)

    async def admin_products(self, query, lang):
        """Gestion produits"""
        try:
            products = self.product_repo.get_all_products(limit=20)
            text = i18n(lang, 'admin_products_title') + "\n\n"

            for product in products:
                status = "✅" if product['status'] == 'active' else "❌"
                text += f"{status} {product['product_id']} - {product['title'][:20]}...\n"

            keyboard = [[InlineKeyboardButton("🔙 Products Menu", callback_data='admin_products_menu')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except (psycopg2.Error, Exception) as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")

    async def admin_payouts(self, query, lang, page: int = 1):
        """Liste paginée des vendeurs à payer"""
        try:
            from app.services.seller_payout_service import SellerPayoutService
            seller_payout_service = SellerPayoutService()
            payouts = seller_payout_service.get_all_pending_payouts_admin()

            if not payouts:
                text = "PAYOUTS EN ATTENTE\n\nAucun payout en attente"
                keyboard = [[InlineKeyboardButton("Retour Admin", callback_data='admin_menu')]]
            else:
                # Pagination setup
                per_page = 10
                total_pages = (len(payouts) + per_page - 1) // per_page
                page = max(1, min(page, total_pages))
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                page_payouts = payouts[start_idx:end_idx]

                total_pending = sum(p.get('amount', 0) for p in payouts)

                text = f"PAYOUTS EN ATTENTE ({len(payouts)} vendeurs)\n\n"
                text += f"Total: ${total_pending:.2f} USDT\n"
                text += f"Page {page}/{total_pages}\n\n"
                text += "Cliquez sur un vendeur pour voir les details:"

                # Boutons vendeurs (un par ligne)
                keyboard = []
                for payout in page_payouts:
                    seller_name = payout.get('seller_name', 'Unknown')
                    amount = payout.get('amount', 0)
                    payout_id = payout.get('id')

                    # Un bouton par vendeur
                    keyboard.append([InlineKeyboardButton(
                        f"{seller_name} - ${amount:.2f}",
                        callback_data=f'admin_payout_details:{payout_id}'
                    )])

                # Pagination buttons
                nav_buttons = []
                if page > 1:
                    nav_buttons.append(InlineKeyboardButton("< Page prec", callback_data=f'admin_payouts_page:{page-1}'))
                if page < total_pages:
                    nav_buttons.append(InlineKeyboardButton("Page suiv >", callback_data=f'admin_payouts_page:{page+1}'))
                if nav_buttons:
                    keyboard.append(nav_buttons)

                # Action buttons
                keyboard.append([InlineKeyboardButton("Tout Payer", callback_data='admin_mark_all_payouts_paid')])
                keyboard.append([InlineKeyboardButton("Export CSV", callback_data='admin_export_payouts_csv')])
                keyboard.append([InlineKeyboardButton("Retour Admin", callback_data='admin_menu')])

            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except (psycopg2.Error, Exception) as e:
            await query.edit_message_text(f"Erreur: {str(e)}")

    async def admin_payout_details(self, query, lang, payout_id: int):
        """Afficher les détails complets d'un payout"""
        try:
            from app.services.seller_payout_service import SellerPayoutService
            seller_payout_service = SellerPayoutService()
            details = seller_payout_service.get_payout_details(payout_id)

            if not details:
                await query.answer("Payout introuvable", show_alert=True)
                return

            # Build text
            seller_name = details['seller_name']
            seller_username = details['seller_username']
            wallet = details['seller_wallet_address']
            total = details['total_amount_usdt']
            currency = details['payment_currency']
            orders = details['orders']

            text = f"DETAILS PAYOUT #{payout_id}\n\n"
            text += f"Vendeur: {seller_name}"
            if seller_username:
                text += f" (@{seller_username})"
            text += f"\nID: {details['seller_user_id']}\n\n"

            text += "COMMANDES:\n"
            for i, order in enumerate(orders, 1):
                product_title = order['product_title']
                price = order['product_price_usd']
                revenue = order['seller_revenue_usd']
                order_id = order['order_id']

                text += f"{i}. {product_title}\n"
                text += f"   Prix: ${price:.2f}\n"
                text += f"   Revenu vendeur: ${revenue:.2f}\n"
                text += f"   Order: {order_id}\n\n"

            text += f"TOTAL A PAYER: ${total:.2f} {currency}\n\n"
            text += f"ADRESSE WALLET:\n`{wallet}`\n\n"
            text += "(Cliquer sur l'adresse pour copier)"

            # Keyboard
            keyboard = [
                [InlineKeyboardButton("Marquer comme paye", callback_data=f'admin_mark_payout_paid:{payout_id}')],
                [InlineKeyboardButton("Retour liste", callback_data='admin_payouts')]
            ]

            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"Erreur: {str(e)}")

    async def admin_marketplace_stats(self, query, lang):
        """Stats marketplace"""
        try:
            total_users = self.user_repo.count_users()
            total_sellers = self.user_repo.count_sellers()
            total_products = self.product_repo.count_products()
            total_orders = self.order_repo.count_orders()

            stats_text = f"""📊 **MARKETPLACE STATS**

 Total Users: {total_users}
 Sellers: {total_sellers}
 Products: {total_products}
 Orders: {total_orders}

 Total Revenue: {self.order_repo.get_total_revenue():.2f}$"""

            await query.edit_message_text(
                stats_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]]),
                parse_mode='Markdown')
        except (psycopg2.Error, Exception) as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")

    async def admin_search_user_prompt(self, query, lang):
        """Prompt recherche utilisateur"""
        # Set searching state for this user
        user_id = query.from_user.id

        await query.edit_message_text(
            "🔍 **Recherche Utilisateur**\n\nEntrez l'ID utilisateur à rechercher :" if lang == 'fr' else "🔍 **User Search**\n\nEnter user ID to search:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def admin_search_product_prompt(self, query, lang):
        """Prompt recherche produit"""
        # Set searching state for this user
        user_id = query.from_user.id

        await query.edit_message_text(
            "🔍 **Recherche Produit**\n\nEntrez l'ID produit à rechercher :" if lang == 'fr' else "🔍 **Product Search**\n\nEnter product ID to search:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def admin_suspend_product_prompt(self, query, lang):
        """Prompt suspension produit - étape 1: choisir la raison"""
        user_id = query.from_user.id

        # Liste des raisons prédéfinies
        reasons_keyboard = [
            [InlineKeyboardButton("🚫 Contenu inapproprié", callback_data='suspend_reason_inappropriate')],
            [InlineKeyboardButton("⚠️ Arnaque / Spam", callback_data='suspend_reason_scam')],
            [InlineKeyboardButton("📋 Violation des conditions", callback_data='suspend_reason_tos')],
            [InlineKeyboardButton("💰 Prix abusif", callback_data='suspend_reason_price')],
            [InlineKeyboardButton("📄 Contenu protégé / Piratage", callback_data='suspend_reason_copyright')],
            [InlineKeyboardButton("⚖️ Illégal", callback_data='suspend_reason_illegal')],
            [InlineKeyboardButton("🔍 Autre raison", callback_data='suspend_reason_other')],
            [InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            "❌ **Suspendre Produit**\n\nChoisissez la raison de la suspension :" if lang == 'fr'
            else "❌ **Suspend Product**\n\nChoose suspension reason:",
            reply_markup=InlineKeyboardMarkup(reasons_keyboard),
            parse_mode='Markdown')

    async def admin_suspend_product_id_prompt(self, bot, query, reason_key, lang):
        """Prompt suspension produit - étape 2: demander l'ID après sélection raison"""
        user_id = query.from_user.id

        # Mapping des raisons
        reason_map = {
            'inappropriate': "Contenu inapproprié ou offensant",
            'scam': "Arnaque, spam ou tentative de fraude",
            'tos': "Violation des conditions d'utilisation de la marketplace",
            'price': "Prix abusif ou pratiques commerciales déloyales",
            'copyright': "Contenu protégé par des droits d'auteur ou piratage",
            'illegal': "Contenu illégal ou activité frauduleuse",
            'other': "Autre raison (non spécifiée)"
        }

        reason_text = reason_map.get(reason_key, "Raison non spécifiée")

        # Stocker la raison dans l'état
        bot.state_manager.update_state(user_id, admin_suspend_product=True, suspend_reason=reason_text, lang=lang)

        await query.edit_message_text(
            f"❌ **Suspendre Produit**\n\n📋 Raison: {reason_text}\n\nEntrez l'ID du produit à suspendre :" if lang == 'fr'
            else f"❌ **Suspend Product**\n\n📋 Reason: {reason_text}\n\nEnter product ID to suspend:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def admin_restore_product_prompt(self, bot, query, lang):
        """Prompt rétablissement produit"""
        user_id = query.from_user.id
        bot.state_manager.update_state(user_id, restoring_product=True, lang=lang)

        await query.edit_message_text(
            "✅ **Rétablir Produit**\n\nEntrez l'ID du produit à rétablir :" if lang == 'fr' else "✅ **Restore Product**\n\nEnter product ID to restore:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def admin_suspend_user_prompt(self, bot, query, lang):
        """Prompt suspension utilisateur"""
        user_id = query.from_user.id
        bot.state_manager.update_state(user_id, suspending_user=True, lang=lang)

        await query.edit_message_text(
            "❌ **Suspendre Utilisateur**\n\nEntrez l'ID utilisateur à suspendre :" if lang == 'fr' else "❌ **Suspend User**\n\nEnter user ID to suspend:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_menu')]]),
            parse_mode='Markdown')

    async def process_admin_suspend_user(self, update, message_text: str):
        """Process suspension d'utilisateur"""
        try:
            user_id = int(message_text.strip())

            # Check if user exists
            user_data = self.user_repo.get_user(user_id)
            if not user_data:
                await update.message.reply_text(f"❌ Utilisateur {user_id} introuvable")
                return

            # Comprehensive user suspension
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Store original seller status and suspend
            was_seller = user_data.get('is_seller', False)

            # Mark as suspended by setting seller_name to special suspend marker
            # and removing seller status
            suspend_marker = f"[SUSPENDED]{user_data.get('seller_name', '')}"
            cursor.execute('''
                UPDATE users SET
                    is_seller = FALSE,
                    seller_name = %s
                WHERE user_id = %s
            ''', (suspend_marker, user_id))

            # Suspend all their products
            cursor.execute('UPDATE products SET status = "suspended" WHERE seller_user_id = %s', (user_id,))

            conn.commit()
            put_connection(conn)

            # Send suspension notification email if email exists
            user_email = user_data.get('email')
            if user_email:
                try:
                    from app.core.email_service import EmailService
                    email_service = EmailService()

                    success = email_service.send_account_suspended_notification(
                        to_email=user_email,
                        user_name=first_name or 'Utilisateur',
                        reason="Violation des règles de la plateforme",
                        duration="indéterminée",
                        is_permanent=False
                    )
                    email_status = "✅ Email de suspension envoyé" if success else "❌ Échec envoi email"
                except (psycopg2.Error, Exception) as e:
                    email_status = f"❌ Erreur email: {str(e)}"
            else:
                email_status = "⚠️ Pas d'email - notification non envoyée"

            username = user_data.get('username', 'N/A')
            first_name = user_data.get('first_name', 'N/A')

            await update.message.reply_text(
                f"✅ **Utilisateur suspendu**\n\n👤 **ID:** `{user_id}`\n📝 **Nom:** {first_name}\n📝 **Username:** @{username}\n\n🚫 **Actions prises:**\n• Statut vendeur retiré\n• Produits suspendus\n• Accès marketplace restreint\n\n📧 **Notification:** {email_status}\n\nℹ️ Utilisez /admin pour le rétablir",
                parse_mode='Markdown'
            )

        except ValueError:
            await update.message.reply_text("❌ ID utilisateur invalide. Entrez un nombre.")
        except (psycopg2.Error, Exception) as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def admin_restore_user_prompt(self, bot, query, lang):
        """Prompt rétablissement utilisateur"""
        user_id = query.from_user.id
        bot.state_manager.update_state(user_id, restoring_user=True, lang=lang)

        # Get list of suspended users
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT user_id, seller_name, email, first_name
                FROM users
                WHERE seller_name LIKE '[SUSPENDED]%'
                LIMIT 20
            ''')
            suspended_users = cursor.fetchall()
            put_connection(conn)

            text = "✅ **Rétablir Utilisateur**\n\n" if lang == 'fr' else "✅ **Restore User**\n\n"

            if suspended_users:
                text += "👥 **Utilisateurs suspendus:**\n\n" if lang == 'fr' else "👥 **Suspended users:**\n\n"
                for user in suspended_users[:10]:  # Show first 10
                    u_id, seller_name, email, first_name = user
                    clean_name = seller_name.replace('[SUSPENDED]', '').strip() or first_name or 'N/A'
                    text += f"• ID: `{u_id}` - {clean_name[:20]}\n"
                text += f"\n📝 **Entrez l'ID ou email à rétablir:**" if lang == 'fr' else f"\n📝 **Enter ID or email to restore:**"
            else:
                text += "✅ Aucun utilisateur suspendu" if lang == 'fr' else "✅ No suspended users"

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_users_menu')]]),
                parse_mode='Markdown')
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error showing suspended users: {e}")
            await query.edit_message_text(
                "✅ **Rétablir Utilisateur**\n\nEntrez l'ID utilisateur OU email à rétablir :" if lang == 'fr' else "✅ **Restore User**\n\nEnter user ID OR email to restore:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='admin_users_menu')]]),
                parse_mode='Markdown')

    async def process_admin_restore_user(self, update, message_text: str):
        """Process rétablissement d'utilisateur"""
        try:
            input_text = message_text.strip()

            # Determine if input is email or user ID
            if '@' in input_text:
                # Search by email
                user_data = self.user_repo.get_user_by_email(input_text.lower())
                search_type = "email"
                search_value = input_text.lower()
            else:
                # Search by user ID
                try:
                    user_id = int(input_text)
                    user_data = self.user_repo.get_user(user_id)
                    search_type = "user_id"
                    search_value = user_id
                except ValueError:
                    await update.message.reply_text("❌ Entrée invalide. Utilisez un ID numérique ou un email valide.")
                    return

            if not user_data:
                await update.message.reply_text(f"❌ Utilisateur introuvable avec {search_type}: {search_value}")
                return

            user_id = user_data['user_id']

            # Check suspension more comprehensively:
            # 1. Check seller_name for [SUSPENDED] marker
            # 2. Check if there are suspended products for this user
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Check for suspended products
            cursor.execute('SELECT COUNT(*) as count FROM products WHERE seller_user_id = %s AND status = %s', (user_id, 'suspended'))
            suspended_products_count = cursor.fetchone()['count']

            seller_name = user_data.get('seller_name', '')
            is_marked_suspended = seller_name.startswith('[SUSPENDED]')

            if not is_marked_suspended and suspended_products_count == 0:
                put_connection(conn)
                await update.message.reply_text(f"❌ L'utilisateur {user_id} n'est pas suspendu")
                return

            # Restore original seller name and status
            original_name = seller_name.replace('[SUSPENDED]', '') if seller_name.startswith('[SUSPENDED]') else seller_name
            if not original_name:
                # If no seller name, create a default one
                original_name = f"Vendeur{user_id}"

            cursor.execute('''
                UPDATE users SET
                    is_seller = TRUE,
                    seller_name = %s
                WHERE user_id = %s
            ''', (original_name, user_id))

            # Restore all their products (set back to active)
            cursor.execute('UPDATE products SET status = "active" WHERE seller_user_id = %s AND status = "suspended"', (user_id,))

            conn.commit()
            put_connection(conn)

            username = user_data.get('username', 'N/A')
            first_name = user_data.get('first_name', 'N/A')

            await update.message.reply_text(
                f"✅ **Utilisateur rétabli**\n\n **ID:** `{user_id}`\n **Nom:** {first_name}\n **Username:** @{username}\n\n🔄 **Actions prises:**\n• Statut vendeur rétabli ({suspended_products_count} produits réactivés)\n• Accès marketplace restauré",
                parse_mode='Markdown'
            )

        except (psycopg2.Error, Exception) as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def admin_mark_payout_paid(self, query, lang, payout_id: int):
        """Marquer un payout spécifique comme payé"""
        try:
            from app.services.seller_payout_service import SellerPayoutService
            seller_payout_service = SellerPayoutService()

            admin_user_id = query.from_user.id
            success = seller_payout_service.mark_payout_as_completed(payout_id, admin_user_id)

            if success:
                await query.answer(f"✅ Payout #{payout_id} marqué comme payé", show_alert=True)
                # Refresh the payout list
                await self.admin_payouts(query, lang)
            else:
                await query.answer(f"❌ Erreur lors du marquage du payout #{payout_id}", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ Erreur: {str(e)}", show_alert=True)

    async def admin_mark_all_payouts_paid(self, query, lang):
        """Marquer tous payouts comme payés"""
        try:
            count = self.payout_service.mark_all_payouts_paid()
            await query.answer(f"✅ {count} payouts marqués comme payés", show_alert=True)
            # Refresh the payout list
            await self.admin_payouts(query, lang)
        except (psycopg2.Error, Exception) as e:
            await query.answer(f"❌ Erreur: {str(e)}", show_alert=True)

    async def admin_export_users(self, query, lang):
        """Export utilisateurs en CSV"""
        try:
            import io
            import csv
            from datetime import datetime

            users = self.user_repo.get_all_users()

            if not users:
                await query.edit_message_text(
                    " Aucun utilisateur à exporter." if lang == 'fr' else " No users to export.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
                )
                return

            # Create CSV content
            csv_content = io.StringIO()
            writer = csv.writer(csv_content)

            # Write header
            writer.writerow([
                'user_id', 'username', 'first_name', 'language_code',
                'registration_date', 'last_activity', 'is_seller',
                'seller_name', 'email', 'total_sales', 'total_revenue'
            ])

            # Write user data
            for user in users:
                writer.writerow([
                    user.get('user_id', ''),
                    user.get('username', ''),
                    user.get('first_name', ''),
                    user.get('language_code', ''),
                    user.get('registration_date', ''),
                    user.get('last_activity', ''),
                    user.get('is_seller', False),
                    user.get('seller_name', ''),
                    user.get('email', ''),
                    user.get('total_sales', 0),
                    user.get('total_revenue', 0.0)
                ])

            # Create file
            csv_bytes = csv_content.getvalue().encode('utf-8')
            file_name = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            # Send CSV file
            await query.message.reply_document(
                document=io.BytesIO(csv_bytes),
                filename=file_name,
                caption=f" Export CSV: {len(users)} utilisateurs" if lang == 'fr' else f" CSV Export: {len(users)} users"
            )

            await query.edit_message_text(
                "✅ Fichier CSV généré avec succès!" if lang == 'fr' else "✅ CSV file generated successfully!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in admin_export_users: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de la génération du CSV." if lang == 'fr' else "❌ Error generating CSV.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )

    async def admin_export_payouts_csv(self, query, lang):
        """Export payouts en CSV avec tous les détails"""
        try:
            from app.services.seller_payout_service import SellerPayoutService
            from app.domain.repositories.user_repo import UserRepository
            import io
            import csv
            from datetime import datetime

            seller_payout_service = SellerPayoutService()
            user_repo = UserRepository()

            # Get all payouts (not just pending)
            conn = self.bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            try:
                cursor.execute('''
                    SELECT id, seller_user_id, total_amount_usdt, seller_wallet_address,
                           payment_currency, payout_status, order_ids, created_at, processed_at
                    FROM seller_payouts
                    ORDER BY created_at DESC
                    LIMIT 100
                ''')
                payouts = cursor.fetchall()
            finally:
                from app.core.db_pool import put_connection
                put_connection(conn)

            if not payouts:
                await query.edit_message_text(
                    "📄 Aucun payout à exporter",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
                )
                return

            # Create CSV in memory
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer)

            # Header
            csv_writer.writerow(['Payout ID', 'Seller ID', 'Seller Name', 'Amount (USDT)', 'Wallet Address',
                                'Currency', 'Status', 'Order IDs', 'Created At', 'Processed At'])

            # Data
            for payout in payouts:
                seller = user_repo.get_user_by_id(payout['seller_user_id'])
                seller_name = seller.get('seller_name', 'Unknown') if seller else 'Unknown'

                created_at = payout['created_at'].strftime('%Y-%m-%d %H:%M') if payout.get('created_at') else 'N/A'
                processed_at = payout['processed_at'].strftime('%Y-%m-%d %H:%M') if payout.get('processed_at') else 'N/A'

                csv_writer.writerow([
                    payout['id'],
                    payout['seller_user_id'],
                    seller_name,
                    f"${payout['total_amount_usdt']:.2f}",
                    payout['seller_wallet_address'],
                    payout['payment_currency'],
                    payout['payout_status'],
                    payout['order_ids'],
                    created_at,
                    processed_at
                ])

            # Send CSV as file
            csv_content = csv_buffer.getvalue().encode('utf-8')
            csv_file = io.BytesIO(csv_content)
            csv_file.name = f"payouts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            await query.message.reply_document(
                document=csv_file,
                filename=csv_file.name,
                caption=f"📊 Export de {len(payouts)} payouts"
            )

            await query.answer("✅ CSV généré", show_alert=False)

        except Exception as e:
            logger.error(f"Error exporting payouts CSV: {e}")
            await query.answer(f"❌ Erreur: {str(e)}", show_alert=True)

    async def admin_export_payouts(self, query, lang):
        """Export payouts (legacy text format)"""
        try:
            payouts = self.payout_service.get_all_payouts()
            export_text = "📄 **EXPORT PAYOUTS**\n\n"
            for payout in payouts[:50]:  # Limit for Telegram
                export_text += f"{payout['user_id']},{payout['amount']},{payout['status']}\n"

            await query.edit_message_text(
                export_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]]))
        except (psycopg2.Error, Exception) as e:
            await query.edit_message_text(f"❌ Erreur: {str(e)}")



    async def export_products(self, query, lang):
        """Export products to text format"""
        try:
            products = self.product_repo.get_all_products(limit=100)

            if not products:
                await query.edit_message_text(
                    "📦 Aucun produit à exporter." if lang == 'fr' else "📦 No products to export.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
                )
                return

            # Create export text
            export_text = "📊 **Export Produits**\n\n" if lang == 'fr' else "📊 **Products Export**\n\n"
            export_text += f"Total: {len(products)} produits\n\n" if lang == 'fr' else f"Total: {len(products)} products\n\n"

            for i, product in enumerate(products[:20], 1):  # Limit to first 20 for readability
                export_text += f"**{i}. {product.get('title', 'N/A')}**\n"
                export_text += f"• ID: `{product.get('product_id', 'N/A')}`\n"
                export_text += f"• Prix: ${product.get('price_usd', 0):.2f}\n" if lang == 'fr' else f"• Price: ${product.get('price_usd', 0):.2f}\n"
                export_text += f"• Catégorie: {product.get('category', 'N/A')}\n" if lang == 'fr' else f"• Category: {product.get('category', 'N/A')}\n"
                export_text += f"• Statut: {product.get('status', 'N/A')}\n" if lang == 'fr' else f"• Status: {product.get('status', 'N/A')}\n"
                export_text += f"• Vendeur ID: {product.get('seller_user_id', 'N/A')}\n\n"

            if len(products) > 20:
                export_text += f"... et {len(products) - 20} autres produits\n" if lang == 'fr' else f"... and {len(products) - 20} more products\n"

            # Split message if too long
            if len(export_text) > 4000:
                export_text = export_text[:4000] + "..."

            keyboard = [
                [InlineKeyboardButton(" Stats détaillées" if lang == 'fr' else " Detailed stats", callback_data='admin_marketplace_stats')],
                [InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]
            ]

            await query.edit_message_text(
                export_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in export_products: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de l'export des produits." if lang == 'fr' else "❌ Error exporting products.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )

    # Text processing methods compatible with compact architecture
    async def handle_user_search_message(self, bot, update, user_state):
        """Process recherche utilisateur"""
        message_text = update.message.text.strip()
        try:
            if message_text.isdigit():
                user = self.user_repo.get_user(int(message_text))
            else:
                user = None  # Partner code search removed

            if user:
                text = f"👤 **User Found**\n\nID: {user['user_id']}\nName: {user.get('first_name', 'N/A')}\nSeller: {user.get('is_seller', False)}"
            else:
                text = "❌ Utilisateur non trouvé"

            await update.message.reply_text(text)
            bot.reset_user_state(update.effective_user.id)
        except (psycopg2.Error, Exception) as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def handle_product_search_message(self, bot, update, user_state):
        """Process recherche produit"""
        message_text = update.message.text.strip()
        try:
            product = self.product_repo.get_product_by_id(message_text.strip())
            if product:
                text = f" **Product Found**\n\nID: {product['product_id']}\nTitle: {product['title']}\nStatus: {product['status']}"
            else:
                text = "❌ Produit non trouvé"

            await update.message.reply_text(text)
            bot.reset_user_state(update.effective_user.id)
        except (psycopg2.Error, Exception) as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")

    async def handle_product_suspend_message(self, bot, update, user_state):
        """Process suspension produit"""
        message_text = update.message.text.strip()
        product_id = message_text.strip()

        # Récupérer la raison stockée dans l'état
        reason = user_state.get('suspend_reason', "Votre produit ne respecte pas les règles de la marketplace.")

        try:
            success = self.product_repo.update_status(product_id, 'banned')

            # Send email notification to seller if product suspended
            if success:
                try:
                    product = self.product_repo.get_product(product_id)
                    if product:
                        seller = self.user_repo.get_user(product['seller_user_id'])
                        if seller and seller.get('email'):
                            from app.core.email_service import EmailService
                            email_service = EmailService()
                            email_service.send_product_suspended_notification(
                                to_email=seller['email'],
                                seller_name=seller.get('seller_name', seller.get('username', 'Vendeur')),
                                product_title=product['title'],
                                reason=reason,
                                can_appeal=True
                            )
                except Exception as email_error:
                    logger.error(f"Erreur envoi email suspension produit: {email_error}")

            # Message de confirmation avec la raison
            if success:
                text = f"✅ **Produit suspendu**\n\n Raison: {reason}\n Produit: {product_id}"
            else:
                text = "❌ Erreur suspension"

            await update.message.reply_text(text, parse_mode='Markdown')
            bot.reset_user_state(update.effective_user.id)
        except (psycopg2.Error, Exception) as e:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")
            bot.reset_user_state(update.effective_user.id)

    async def process_admin_restore_product(self, bot, update, user_state):
        """Process restoration produit"""
        product_id = update.message.text.strip()
        lang = user_state.get('lang', 'fr')

        try:
            # Vérifier que le produit existe
            product = self.product_repo.get_product(product_id)
            if not product:
                await update.message.reply_text(
                    "❌ Produit introuvable." if lang == 'fr' else "❌ Product not found."
                )
                bot.reset_user_state(update.effective_user.id)
                return

            # Vérifier que le produit est suspendu
            if product.get('status') != 'banned':
                await update.message.reply_text(
                    f"⚠️ Ce produit n'est pas suspendu (statut actuel: {product.get('status')})." if lang == 'fr'
                    else f"⚠️ This product is not suspended (current status: {product.get('status')})."
                )
                bot.reset_user_state(update.effective_user.id)
                return

            # Rétablir le produit
            success = self.product_repo.update_status(product_id, 'active')

            if success:
                text = (
                    f"✅ **Produit rétabli avec succès!**\n\n"
                    f" **{product['title']}**\n"
                    f" {product_id}\n"
                    f" ${product['price_usd']:.2f}\n\n"
                    f"Le produit est maintenant visible sur la marketplace."
                ) if lang == 'fr' else (
                    f"✅ **Product restored successfully!**\n\n"
                    f" **{product['title']}**\n"
                    f" {product_id}\n"
                    f" ${product['price_usd']:.2f}\n\n"
                    f"The product is now visible on the marketplace."
                )

                # Optionnel: Envoyer email au vendeur (notification de rétablissement)
                try:
                    seller = self.user_repo.get_user(product['seller_user_id'])
                    if seller and seller.get('email'):
                        # TODO: Créer email de notification de rétablissement si souhaité
                        pass
                except Exception as email_error:
                    logger.error(f"Erreur notification vendeur restoration: {email_error}")
            else:
                text = "❌ Erreur lors du rétablissement." if lang == 'fr' else "❌ Error restoring product."

            await update.message.reply_text(text, parse_mode='Markdown')
            bot.reset_user_state(update.effective_user.id)

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in process_admin_restore_product: {e}")
            await update.message.reply_text(
                f"❌ Erreur: {str(e)}" if lang == 'fr' else f"❌ Error: {str(e)}"
            )
            bot.reset_user_state(update.effective_user.id)

    async def admin_export_products_csv(self, query, lang):
        """Export products to CSV file"""
        try:
            import csv
            import io
            from datetime import datetime

            products = self.product_repo.get_all_products()

            if not products:
                await query.edit_message_text(
                    " Aucun produit à exporter." if lang == 'fr' else " No products to export.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
                )
                return

            # Create CSV content
            csv_content = io.StringIO()
            writer = csv.writer(csv_content)

            # Headers
            headers = ['ID Produit', 'Titre', 'Prix EUR', 'Catégorie', 'Statut', 'Vendeur ID', 'Date Création'] if lang == 'fr' else \
                     ['Product ID', 'Title', 'Price EUR', 'Category', 'Status', 'Seller ID', 'Created Date']
            writer.writerow(headers)

            # Data rows
            for product in products:
                writer.writerow([
                    product.get('product_id', ''),
                    product.get('title', ''),
                    product.get('price_usd', 0),
                    product.get('category', ''),
                    product.get('status', ''),
                    product.get('seller_user_id', ''),
                    product.get('created_at', '')
                ])

            csv_data = csv_content.getvalue()
            csv_content.close()

            # Send as document
            filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

            await query.message.reply_document(
                document=io.BytesIO(csv_data.encode('utf-8')),
                filename=filename,
                caption=f"📊 Export CSV: {len(products)} produits" if lang == 'fr' else f"📊 CSV Export: {len(products)} products"
            )

            await query.edit_message_text(
                "✅ Fichier CSV généré avec succès!" if lang == 'fr' else "✅ CSV file generated successfully!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu Admin" if lang == 'fr' else "🔙 Admin Menu", callback_data='admin_menu')]])
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in admin_export_products_csv: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de la génération du CSV." if lang == 'fr' else "❌ Error generating CSV.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Menu", callback_data='admin_menu')]])
            )
