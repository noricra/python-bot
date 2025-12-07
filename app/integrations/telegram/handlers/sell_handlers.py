"""Sell Handlers - Modular class with dependency injection"""

import os
import logging
import asyncio  # <--- AJOUT CRITIQUE
import psycopg2
import psycopg2.extras
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.core.db_pool import put_connection
from app.core.i18n import t as i18n
from app.integrations.telegram.keyboards import sell_menu_keyboard, back_to_main_button
from app.core.validation import validate_email, validate_solana_address
from app.integrations.telegram.utils import safe_transition_to_text
from app.services.chart_service import ChartService
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)

class SellHandlers:
    def __init__(self, user_repo, product_repo, payment_service):
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.payment_service = payment_service
        self.chart_service = ChartService()
        self.export_service = ExportService()

    # ==================== HELPER FUNCTIONS ====================

    async def _verify_product_ownership(self, bot, query, product_id: str):
        """
        Verify product ownership and return product if owned by current seller
        """
        # Get actual seller_id (handles multi-account mapping)
        user_id = query.from_user.id

        # Get product and verify ownership
        product = self.product_repo.get_product_by_id(product_id)
        if not product or product.get('seller_user_id') != user_id:
            await safe_transition_to_text(
                query,
                "❌ Produit introuvable ou vous n'êtes pas le propriétaire",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')
                ]])
            )
            return None

        return product

    def _set_editing_state(self, bot, user_id: int, field: str, value=True):
        """
        Set editing state for a specific field
        """
        # Map field names to step names for seller settings
        seller_field_to_step = {
            'seller_name': 'edit_name',
            'seller_bio': 'edit_bio',
            'seller_email': 'edit_email',
            'solana_address': 'edit_solana_address'
        }

        bot.reset_conflicting_states(user_id, keep={f'editing_{field}'})

        # If editing seller settings, also set editing_settings=True and step
        if field in seller_field_to_step:
            bot.state_manager.update_state(
                user_id,
                editing_settings=True,
                step=seller_field_to_step[field],
                **{f'editing_{field}': value}
            )
        else:
            bot.state_manager.update_state(user_id, **{f'editing_{field}': value})

    # ==================== PUBLIC METHODS ====================

    async def sell_menu(self, bot, query, lang: str):
        """Menu vendeur - Connexion par email requise"""
        user_id = query.from_user.id

        # 🔧 FIX: Réinitialiser TOUS les états quand on entre dans le menu Vendre
        bot.reset_user_state(user_id, keep={'lang'})

        user_data = self.user_repo.get_user(user_id)

        # Si déjà vendeur → Dashboard direct (aligné sur /stats)
        if user_data and user_data['is_seller']:
            await self.seller_dashboard(bot, query, lang)
            return

        # Sinon → Proposer création compte
        await query.edit_message_text(
            (
                "🏪 **DEVENIR VENDEUR**\n\n"
                "Vous n'avez pas encore de compte vendeur.\n\n"
                "Créez votre compte en 2 minutes et commencez à vendre !"
            ) if lang == 'fr' else (
                "🏪 **BECOME A SELLER**\n\n"
                "You don't have a seller account yet.\n\n"
                "Create your account in 2 minutes and start selling!"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🚀 Créer mon compte vendeur" if lang == 'fr' else "🚀 Create seller account",
                    callback_data='create_seller'
                )
            ], [
                InlineKeyboardButton(
                    "🔙 Retour" if lang == 'fr' else "🔙 Back",
                    callback_data='back_main'
                )
            ]]),
            parse_mode='Markdown'
        )

    async def seller_login_menu(self, bot, query, lang: str):
        """Menu de reconnexion vendeur"""
        user_id = query.from_user.id

        # Reset conflicting states
        bot.reset_conflicting_states(user_id, keep={'lang'})

        # Set state to expect email
        bot.state_manager.update_state(user_id, waiting_seller_login_email=True, lang=lang)

        login_text = (
            "**RECONNEXION VENDEUR**\n\n"
            "Pour accéder à votre compte vendeur, veuillez entrer votre **adresse email**.\n\n"
            "Email enregistré : Celui que vous avez utilisé lors de la création de votre compte"
        ) if lang == 'fr' else (
            "**SELLER LOGIN**\n\n"
            "To access your seller account, please enter your **email address**.\n\n"
            "Registered email: The one you used when creating your account"
        )

        await query.edit_message_text(
            login_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🔙 Retour" if lang == 'fr' else "🔙 Back",
                    callback_data='back_main'
                )
            ]]),
            parse_mode='Markdown'
        )

    async def create_seller_prompt(self, bot, query, lang: str):
        """Demande création compte vendeur - SIMPLIFIÉ (email + Solana uniquement)"""
        bot.reset_conflicting_states(query.from_user.id, keep={'creating_seller'})
        bot.state_manager.update_state(query.from_user.id, creating_seller=True, step='email', lang=lang)

        prompt_text = (
            "📧 **CRÉER COMPTE VENDEUR**\n\n"
            "Étape 1/2: Entrez votre **email** (pour recevoir les notifications de ventes)\n\n"
            "💡 Vous pourrez configurer votre bio et nom dans les paramètres après."
        ) if lang == 'fr' else (
            "📧 **CREATE SELLER ACCOUNT**\n\n"
            "Step 1/2: Enter your **email** (to receive sales notifications)\n\n"
            "💡 You can configure your bio and name in settings later."
        )

        await query.edit_message_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(i18n(lang, 'btn_cancel'), callback_data='sell_menu')
            ]]),
            parse_mode='Markdown'
        )


    async def seller_dashboard(self, bot, query, lang: str):
        """Dashboard vendeur avec graphiques visuels"""
        from datetime import datetime, timedelta

        # Get actual seller_id (handles multi-account mapping)
        seller_id = query.from_user.id

        # 🔧 FIX: Réinitialiser TOUS les états quand on retourne au dashboard
        bot.reset_user_state(seller_id, keep={'lang', 'requires_relogin'})

        user_data = self.user_repo.get_user(seller_id)

        # Check if user is seller
        if not user_data or not user_data['is_seller']:
            await self.seller_login_menu(bot, query, lang)
            return

        # If seller logged out voluntarily, require re-login
        if bot.get_user_state(seller_id).get('requires_relogin'):
            await self.seller_login_menu(bot, query, lang)
            return

        products = self.product_repo.get_products_by_seller(seller_id)

        # Calculer revenu réel depuis la table orders (source de vérité)
        from app.core.database_init import get_postgresql_connection
        from app.core.db_pool import put_connection
        from app.core import settings as core_settings
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT COALESCE(SUM(product_price_usd), 0) as total_revenue
            FROM orders
            WHERE seller_user_id = %s AND payment_status = 'completed'
        """, (seller_id,))
        total_revenue = cursor.fetchone()['total_revenue']

        # Calculate total storage used (in MB)
        cursor.execute("""
            SELECT COALESCE(SUM(file_size_mb), 0) as storage_used
            FROM products
            WHERE seller_user_id = %s
        """, (seller_id,))
        storage_used_mb = cursor.fetchone()['storage_used']
        put_connection(conn)

        # Storage limit: 100MB
        storage_limit_mb = 100
        storage_text = f"\n\nStockage: {storage_used_mb:.1f}/100MB"

        # Message texte simple
        dashboard_text = i18n(lang, 'dashboard_welcome').format(
            name=bot.escape_markdown(user_data.get('seller_name', 'Vendeur')),
            products_count=len(products),
            revenue=f"${total_revenue:.2f}"
        )
        dashboard_text += storage_text

        # Simplified layout: 6 lignes → 4 lignes (SELLER_WORKFLOW_SPEC)
        keyboard = [
            [InlineKeyboardButton(i18n(lang, 'btn_my_products'), callback_data='my_products'),
             InlineKeyboardButton("📊 Analytics", callback_data='seller_analytics_enhanced')],
            [InlineKeyboardButton(i18n(lang, 'btn_add_product'), callback_data='add_product'),
             InlineKeyboardButton("🔗 Lien Boutique" if lang == 'fr' else "🔗 Shop Link", callback_data='generate_shop_link')],
            [InlineKeyboardButton(i18n(lang, 'btn_logout'), callback_data='seller_logout'),
             InlineKeyboardButton(i18n(lang, 'btn_seller_settings'), callback_data='seller_settings')],
            [InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]
        ]

        try:
            await query.edit_message_text(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(dashboard_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def seller_analytics_visual(self, bot, query, lang: str):
        """Affiche les analytics avec statistiques textuelles"""
        from datetime import datetime, timedelta
        from app.core.database_init import get_postgresql_connection
        from app.core.db_pool import put_connection

        seller_id = query.from_user.id

        try:
            # Notifier l'utilisateur
            await query.answer("📊 Chargement des statistiques...")

            # Récupérer les données de ventes
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Total revenus
            cursor.execute("""
                SELECT COALESCE(SUM(product_price_usd), 0) as total_revenue,
                       COUNT(*) as total_sales
                FROM orders
                WHERE seller_user_id = %s AND payment_status = 'completed'
            """, (seller_id,))
            stats = cursor.fetchone()

            # Top 5 produits
            cursor.execute("""
                SELECT p.title, COUNT(o.order_id) as sales, COALESCE(SUM(o.product_price_usd), 0) as revenue
                FROM products p
                LEFT JOIN orders o ON p.product_id = o.product_id AND o.payment_status = 'completed'
                WHERE p.seller_user_id = %s
                GROUP BY p.product_id, p.title
                ORDER BY revenue DESC
                LIMIT 5
            """, (seller_id,))
            top_products = cursor.fetchall()
            put_connection(conn)

            # Construire le message
            text = f"""📊 **Statistiques de vente**

 **Revenus totaux:** ${stats['total_revenue']:.2f}
 **Ventes totales:** {stats['total_sales']}

🏆 **Top 5 Produits:**
"""
            for i, p in enumerate(top_products, 1):
                text += f"{i}. {p['title'][:30]}... - ${p['revenue']:.2f} ({p['sales']} ventes)\n"

            # Bouton retour
            keyboard = [[InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')]]
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in seller_analytics_visual: {e}")
            await query.message.reply_text(
                "❌ Erreur lors de la génération des statistiques.\n\n"
                f"Détails: {str(e)}",
                parse_mode='Markdown'
            )

    async def seller_analytics_enhanced(self, bot, query, lang: str = 'fr'):
        """
        Affiche les analytics vendeur avec graphiques visuels (Optimisé Async)
        """
        from datetime import datetime, timedelta
        from app.core.database_init import get_postgresql_connection
        from app.core.db_pool import put_connection

        seller_id = query.from_user.id

        try:
            # Notifier l'utilisateur
            await query.answer("📊 Génération des graphiques...")

            # ═══════════════════════════════════════════════════════
            # RÉCUPÉRER LES DONNÉES (Database Call)
            # ═══════════════════════════════════════════════════════
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Stats globales
            cursor.execute("""
                SELECT
                    COALESCE(SUM(product_price_usd), 0) as total_revenue,
                    COALESCE(SUM(seller_revenue_usd), 0) as net_revenue,
                    COALESCE(SUM(platform_commission_usd), 0) as total_commission,
                    COUNT(*) as total_sales
                FROM orders
                WHERE seller_user_id = %s AND payment_status = 'completed'
            """, (seller_id,))
            global_stats = cursor.fetchone()

            # Données 30 derniers jours pour graphiques
            cursor.execute("""
                SELECT
                    DATE(completed_at) as date,
                    COALESCE(SUM(product_price_usd), 0) as revenue,
                    COUNT(*) as sales
                FROM orders
                WHERE seller_user_id = %s
                  AND payment_status = 'completed'
                  AND completed_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(completed_at)
                ORDER BY date ASC
            """, (seller_id,))
            daily_stats = cursor.fetchall()

            # Top 5 produits
            cursor.execute("""
                SELECT
                    p.title,
                    p.price_usd,
                    COUNT(o.order_id) as sales,
                    COALESCE(SUM(o.seller_revenue_usd), 0) as revenue
                FROM products p
                LEFT JOIN orders o ON p.product_id = o.product_id
                  AND o.payment_status = 'completed'
                WHERE p.seller_user_id = %s
                GROUP BY p.product_id, p.title, p.price_usd
                ORDER BY revenue DESC
                LIMIT 5
            """, (seller_id,))
            top_products = cursor.fetchall()

            # Nombre de produits
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE status = 'active') as active
                FROM products
                WHERE seller_user_id = %s
            """, (seller_id,))
            product_count = cursor.fetchone()

            put_connection(conn)

            # ═══════════════════════════════════════════════════════
            # PRÉPARER LES DONNÉES
            # ═══════════════════════════════════════════════════════

            dates_dict = {row['date'].strftime('%m-%d'): row for row in daily_stats}
            dates_labels = []
            revenues_data = []
            sales_data = []

            for i in range(29, -1, -1):
                date = datetime.now().date() - timedelta(days=i)
                date_label = date.strftime('%m-%d')
                dates_labels.append(date_label)

                if date_label in dates_dict:
                    revenues_data.append(float(dates_dict[date_label]['revenue']))
                    sales_data.append(int(dates_dict[date_label]['sales']))
                else:
                    revenues_data.append(0)
                    sales_data.append(0)

            # ═══════════════════════════════════════════════════════
            # GÉNÉRER LE GRAPHIQUE (NON-BLOQUANT VIA EXECUTOR)
            # ═══════════════════════════════════════════════════════

            chart_data = None
            if sum(revenues_data) > 0:
                # Utiliser run_in_executor car matplotlib est bloquant
                loop = asyncio.get_running_loop()
                chart_data = await loop.run_in_executor(
                    None,
                    self.chart_service.generate_combined_dashboard_chart,
                    dates_labels,
                    revenues_data,
                    sales_data,
                    800, # width
                    400  # height
                )

            # ═══════════════════════════════════════════════════════
            # CONSTRUIRE LE MESSAGE TEXTE
            # ═══════════════════════════════════════════════════════

            text = f"""📊 **{i18n(lang, 'analytics_dashboard_title')}**

 **{i18n(lang, 'analytics_net_revenue')}**
└─ ${global_stats['net_revenue']:.2f}

 **{i18n(lang, 'analytics_products_sales')}**
├─ {i18n(lang, 'analytics_products_active').format(active=product_count['active'], total=product_count['total'])}
└─ {i18n(lang, 'analytics_orders').format(sales=global_stats['total_sales'])}

🏆 **{i18n(lang, 'analytics_top5')}**"""

            if top_products:
                for i, p in enumerate(top_products, 1):
                    title_truncated = p['title'][:25] + '...' if len(p['title']) > 25 else p['title']
                    text += f"\n{i}. {title_truncated}"
                    text += f"\n    ${p['revenue']:.2f} •  {p['sales']} {i18n(lang, 'analytics_sales_count')}"
            else:
                text += f"\n\n_{i18n(lang, 'analytics_no_products')}_"

            text += f"\n\n{i18n(lang, 'analytics_chart_30days')}"

            # ═══════════════════════════════════════════════════════
            # KEYBOARD
            # ═══════════════════════════════════════════════════════

            keyboard = [
                [
                    InlineKeyboardButton(i18n(lang, 'analytics_btn_detailed'), callback_data='analytics_detailed_charts'),
                    InlineKeyboardButton(i18n(lang, 'analytics_btn_export'), callback_data='analytics_export_csv')
                ],
                [
                    InlineKeyboardButton(i18n(lang, 'analytics_btn_refresh'), callback_data='seller_analytics_enhanced'),
                    InlineKeyboardButton(i18n(lang, 'btn_dashboard'), callback_data='seller_dashboard')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # ═══════════════════════════════════════════════════════
            # ENVOYER LE MESSAGE
            # ═══════════════════════════════════════════════════════

            try:
                await query.message.delete()
            except:
                pass

            if chart_data:
                try:
                    # chart_data est maintenant (url, json_payload)
                    url, json_payload = chart_data

                    # Envoyer POST à QuickChart avec le JSON dans le body
                    import httpx
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(url, json=json_payload)
                        response.raise_for_status()
                        image_bytes = response.content

                    await query.message.reply_photo(
                        photo=image_bytes,
                        caption=text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                except Exception as chart_error:
                    logger.error(f"Failed to download/send chart: {chart_error}")
                    # Fallback: envoyer le texte sans image
                    await query.message.reply_text(
                        text=text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
            else:
                await query.message.reply_text(
                    text=text + f"\n\n_{i18n(lang, 'analytics_no_data')}_",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error(f"Error in seller_analytics_enhanced: {e}", exc_info=True)
            await query.message.reply_text(
                "❌ Erreur lors de la génération des statistiques.\n\n"
                "Veuillez réessayer dans quelques instants.",
                parse_mode='Markdown'
            )

    async def analytics_detailed_charts(self, bot, query, lang: str = 'fr'):
        """
        Affiche plusieurs graphiques détaillés (Optimisé Async)
        """
        from datetime import datetime, timedelta
        from app.core.database_init import get_postgresql_connection
        from app.core.db_pool import put_connection

        seller_id = query.from_user.id

        try:
            await query.answer("📊 Génération des graphiques détaillés...")

            # ═══════════════════════════════════════════════════════
            # RÉCUPÉRER LES DONNÉES
            # ═══════════════════════════════════════════════════════
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Données 30 derniers jours
            cursor.execute("""
                SELECT
                    DATE(completed_at) as date,
                    COALESCE(SUM(product_price_usd), 0) as revenue,
                    COUNT(*) as sales
                FROM orders
                WHERE seller_user_id = %s
                  AND payment_status = 'completed'
                  AND completed_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(completed_at)
                ORDER BY date ASC
            """, (seller_id,))
            daily_stats = cursor.fetchall()

            # Performance par produit (top 10)
            cursor.execute("""
                SELECT
                    p.title,
                    COUNT(o.order_id) as sales,
                    COALESCE(SUM(o.seller_revenue_usd), 0) as revenue
                FROM products p
                LEFT JOIN orders o ON p.product_id = o.product_id
                  AND o.payment_status = 'completed'
                WHERE p.seller_user_id = %s
                GROUP BY p.product_id, p.title
                ORDER BY revenue DESC
                LIMIT 10
            """, (seller_id,))
            product_performance = cursor.fetchall()

            put_connection(conn)

            # ═══════════════════════════════════════════════════════
            # PRÉPARER LES DONNÉES
            # ═══════════════════════════════════════════════════════

            dates_dict = {row['date'].strftime('%m-%d'): row for row in daily_stats}
            dates_labels = []
            revenues_data = []
            sales_data = []

            for i in range(29, -1, -1):
                date = datetime.now().date() - timedelta(days=i)
                date_label = date.strftime('%m-%d')
                dates_labels.append(date_label)

                if date_label in dates_dict:
                    revenues_data.append(float(dates_dict[date_label]['revenue']))
                    sales_data.append(int(dates_dict[date_label]['sales']))
                else:
                    revenues_data.append(0)
                    sales_data.append(0)

            # ═══════════════════════════════════════════════════════
            # GÉNÉRER LES GRAPHIQUES (NON-BLOQUANT)
            # ═══════════════════════════════════════════════════════

            loop = asyncio.get_running_loop()
            charts_to_send = []

            # Graphique 1 : Revenus
            revenue_chart_data = await loop.run_in_executor(
                None,
                self.chart_service.generate_revenue_chart,
                dates_labels,
                revenues_data
            )
            charts_to_send.append(('Revenus (30 jours)', revenue_chart_data))

            # Graphique 2 : Ventes
            sales_chart_data = await loop.run_in_executor(
                None,
                self.chart_service.generate_sales_chart,
                dates_labels,
                sales_data
            )
            charts_to_send.append(('Ventes (30 jours)', sales_chart_data))

            # Graphique 3 : Performance produits
            if product_performance and len(product_performance) > 0:
                product_titles = [p['title'][:20] for p in product_performance]
                product_sales = [int(p['sales']) for p in product_performance]
                product_revenues = [float(p['revenue']) for p in product_performance]

                product_chart_data = await loop.run_in_executor(
                    None,
                    self.chart_service.generate_product_performance_chart,
                    product_titles,
                    product_sales,
                    product_revenues
                )
                charts_to_send.append(('Performance Produits (Top 10)', product_chart_data))

            # ═══════════════════════════════════════════════════════
            # ENVOYER LES GRAPHIQUES
            # ═══════════════════════════════════════════════════════

            if charts_to_send:
                await query.message.reply_text(i18n(lang, 'analytics_detailed_title'))

                import httpx
                for title, chart_data in charts_to_send:
                    try:
                        # chart_data est maintenant (url, json_payload)
                        url, json_payload = chart_data

                        # Envoyer POST à QuickChart avec le JSON dans le body
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(url, json=json_payload)
                            response.raise_for_status()
                            image_bytes = response.content

                        # Envoyer l'image comme fichier
                        await query.message.reply_photo(
                            photo=image_bytes,
                            caption=f"**{title}**",
                            parse_mode='Markdown'
                        )
                    except Exception as chart_error:
                        logger.error(f"Failed to send chart '{title}': {chart_error}")
                        await query.message.reply_text(f"⚠️ Impossible de générer: {title}")

                # Bouton retour
                keyboard = [[InlineKeyboardButton("🔙 Retour Analytics", callback_data='seller_analytics_enhanced')]]
                await query.message.reply_text(
                    text="✅ Tous les graphiques ont été générés",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.message.reply_text(
                    "ℹ️ Pas encore de données suffisantes pour générer des graphiques détaillés.\n\n"
                    "Créez des produits et attendez vos premières ventes !",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Error in analytics_detailed_charts: {e}", exc_info=True)
            await query.message.reply_text(
                "❌ Erreur lors de la génération des graphiques.",
                parse_mode='Markdown'
            )

    async def analytics_export_csv(self, bot, query, lang: str = 'fr'):
        """
        Exporte les statistiques vendeur en CSV (Optimisé Async)
        """
        from datetime import datetime
        from app.core.database_init import get_postgresql_connection
        from app.core.db_pool import put_connection

        seller_id = query.from_user.id

        try:
            await query.answer("📥 Génération du fichier CSV...")

            # ═══════════════════════════════════════════════════════
            # RÉCUPÉRER LES DONNÉES
            # ═══════════════════════════════════════════════════════
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Infos vendeur
            cursor.execute("SELECT seller_name, email FROM users WHERE user_id = %s", (seller_id,))
            seller_info = cursor.fetchone()
            seller_name = seller_info['seller_name'] if seller_info else f"Seller_{seller_id}"

            # Tous les produits
            cursor.execute("SELECT * FROM products WHERE seller_user_id = %s ORDER BY created_at DESC", (seller_id,))
            products = cursor.fetchall()

            # Toutes les commandes
            cursor.execute("SELECT * FROM orders WHERE seller_user_id = %s ORDER BY created_at DESC", (seller_id,))
            orders = cursor.fetchall()

            put_connection(conn)

            # ═══════════════════════════════════════════════════════
            # GÉNÉRER LE CSV (NON-BLOQUANT via Executor)
            # ═══════════════════════════════════════════════════════
            
            loop = asyncio.get_running_loop()
            
            # On exécute l'écriture fichier dans un thread séparé
            csv_file = await loop.run_in_executor(
                None,
                self.export_service.export_seller_stats_to_csv,
                seller_id,
                seller_name,
                products,
                orders
            )

            # Nom du fichier
            filename = self.export_service.generate_filename('seller_stats', str(seller_id))

            # ═══════════════════════════════════════════════════════
            # ENVOYER LE FICHIER
            # ═══════════════════════════════════════════════════════

            await query.message.reply_document(
                document=csv_file,
                filename=filename,
                caption=f"📊 **Export de vos statistiques**\n\n"
                        f"Fichier : `{filename}`\n"
                        f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                        f"Le fichier contient :\n"
                        f"• Résumé global\n"
                        f"• Détail de tous vos produits\n"
                        f"• Historique complet des ventes\n"
                        f"• Performance par catégorie\n"
                        f"• Top 10 produits",
                parse_mode='Markdown'
            )

            # Message de confirmation
            keyboard = [[InlineKeyboardButton(i18n(lang, 'analytics_btn_back'), callback_data='seller_analytics_enhanced')]]
            await query.message.reply_text(
                text=i18n(lang, 'analytics_export_success'),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error in analytics_export_csv: {e}", exc_info=True)
            await query.message.reply_text(
                "❌ Erreur lors de l'export CSV.\n\n"
                "Veuillez réessayer dans quelques instants.",
                parse_mode='Markdown'
            )

    async def add_product_prompt(self, bot, query, lang: str):
        """Prompt ajout produit"""
        user_id = query.from_user.id

        # 🔍 DEBUG: État AVANT reset
        logger.info(f"🆕 ADD_PRODUCT_PROMPT - User {user_id}")
        logger.info(f"   State BEFORE reset: {bot.state_manager.get_state(user_id)}")

        # 🔧 FIX: Réinitialiser TOUS les états avant de commencer l'ajout produit
        bot.reset_user_state(user_id, keep={'lang', 'requires_relogin'})
        bot.state_manager.update_state(user_id, adding_product=True, step='title', product_data={}, lang=lang)

        # 🔍 DEBUG: État APRÈS initialisation
        final_state = bot.state_manager.get_state(user_id)
        logger.info(f"   State AFTER init: {final_state}")
        logger.info(f"   Memory cache entry: {bot.state_manager.user_states.get(user_id, 'NOT FOUND')}")

        await query.edit_message_text(
            f"{i18n(lang, 'product_add_title')}\n\n{i18n(lang, 'product_step1_prompt')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_cancel'), callback_data='seller_dashboard')]]),
            parse_mode='Markdown')

    async def continue_after_miniapp_upload(self, bot, query, lang: str):
        """Continue product creation after miniapp file upload"""
        user_id = query.from_user.id

        logger.info(f"📱 CONTINUE_AFTER_MINIAPP_UPLOAD - User {user_id}")

        # Get existing product_data with file info from miniapp upload
        user_state = bot.get_user_state(user_id)
        product_data = user_state.get('product_data', {})

        # Verify file was uploaded
        if not product_data.get('main_file_url'):
            await query.edit_message_text(
                "❌ Erreur: Fichier non trouvé. Veuillez réessayer l'upload.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data='seller_dashboard')
                ]])
            )
            return

        logger.info(f"   File uploaded via miniapp: {product_data.get('file_name')}")

        # Initialize product creation state (title is first step)
        bot.state_manager.update_state(
            user_id,
            adding_product=True,
            step='title',
            product_data=product_data,
            lang=lang
        )

        # Ask for product title
        await query.edit_message_text(
            f"✅ Fichier reçu !\n\n{i18n(lang, 'product_add_title')}\n\n{i18n(lang, 'product_step1_prompt')}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(i18n(lang, 'btn_cancel'), callback_data='seller_dashboard')
            ]]),
            parse_mode='Markdown'
        )

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

        # Add Mini App button for file upload step
        if current_step == 'file':
            webapp_url = os.getenv('WEBAPP_URL')
            if webapp_url and webapp_url.startswith('https://'):
                from telegram import WebAppInfo
                keyboard.append([
                    InlineKeyboardButton(
                        "📤 Upload via Mini App",
                        web_app=WebAppInfo(url=f"{webapp_url}/static/upload.html")
                    )
                ])

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
        from app.integrations.telegram.utils.carousel_helper import CarouselHelper
        from telegram import InlineKeyboardButton

        # Caption builder for seller carousel
        def build_caption(product, lang):
            status_icon = "✅" if product['status'] == 'active' else "❌"
            status_text = "**ACTIF**" if product['status'] == 'active' else "_Inactif_"

            caption = ""
            category = product.get('category', '')
            breadcrumb = f"📂 _Mes Produits" + (f" › {category}_" if category else "_")
            caption += f"{breadcrumb}\n\n"
            caption += f"{status_icon} **{product['title']}**\n\n"
            caption += f" **${product['price_usd']:.2f}** •  {status_text}\n"
            caption += "────────────────\n\n"
            caption += "📊 **PERFORMANCE**\n"
            caption += f"• **{product.get('sales_count', 0)}** ventes"

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

            if product.get('description'):
                desc = product['description']
                if len(desc) > 160:
                    desc = desc[:160].rsplit(' ', 1)[0] + "..."
                caption += f"{desc}\n\n"

            caption += f"📂 _{product.get('category', 'N/A')}_  •  📁 {product.get('file_size_mb', 0):.1f} MB"
            return caption

        # Keyboard builder for seller carousel
        def build_keyboard(product, index, total, lang):
            keyboard = []

            # Row 1: Edit button
            keyboard.append([
                InlineKeyboardButton(
                    "✏️ ÉDITER CE PRODUIT" if lang == 'fr' else "✏️ EDIT THIS PRODUCT",
                    callback_data=f'edit_product_{product["product_id"]}'
                )
            ])

            # Row 2: Navigation with carousel helper
            nav_row = CarouselHelper.build_navigation_row(
                index=index,
                total=total,
                callback_prefix='seller_carousel_',
                show_empty_buttons=True
            )
            keyboard.append(nav_row)

            # Row 3: Share button
            keyboard.append([
                InlineKeyboardButton(
                    "🔗 Partager ce produit" if lang == 'fr' else "🔗 Share this product",
                    callback_data=f'share_product_{product["product_id"]}'
                )
            ])

            # Row 4: Toggle + Delete
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

            # Row 5: Back
            keyboard.append([
                InlineKeyboardButton(
                    "🔙 Dashboard",
                    callback_data='seller_dashboard'
                )
            ])

            return keyboard

        # Use carousel helper (eliminates duplication)
        await CarouselHelper.show_carousel(
            query=query,
            bot=bot,
            products=products,
            index=index,
            caption_builder=build_caption,
            keyboard_builder=build_keyboard,
            lang=lang,
            parse_mode='Markdown'
        )

    async def show_my_products(self, bot, query, lang: str, page: int = 0):
        """Affiche produits vendeur avec carousel visuel"""
        # Get actual seller_id (handles multi-account mapping)
        seller_id = query.from_user.id
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
        seller_id = query.from_user.id
        products = self.product_repo.get_products_by_seller(seller_id)

        # Calculer ventes et revenu réels depuis la table orders (source de vérité)
        from app.core.database_init import get_postgresql_connection
        from app.core.db_pool import put_connection
        from app.core import settings as core_settings
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(product_price_usd), 0)
            FROM orders
            WHERE seller_user_id = %s AND payment_status = 'completed'
        """, (seller_id,))
        total_sales, total_revenue = cursor.fetchone()
        put_connection(conn)

        analytics_text = i18n(lang, 'analytics_title').format(
            products=len(products),
            sales=total_sales,
            revenue=f"${total_revenue:.2f}"
        )

        await query.edit_message_text(
            analytics_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='seller_dashboard')]]),
            parse_mode='Markdown')

    async def seller_settings(self, bot, query, lang: str):
        """Paramètres vendeur - Enhanced avec tous les boutons (SELLER_WORKFLOW_SPEC)"""
        user_id = query.from_user.id

        # 🔧 FIX: Réinitialiser les états d'édition quand on entre dans Settings
        bot.reset_user_state(user_id, keep={'lang', 'requires_relogin'})

        user_data = self.user_repo.get_user(user_id)

        # Afficher informations récapitulatives
        solana_addr = user_data.get('seller_solana_address', '')
        solana_display = f"{solana_addr[:8]}..." if solana_addr and len(solana_addr) > 8 else solana_addr or "Non configurée"

        email_display = user_data.get('email', 'Non défini')

        settings_text = (
            "⚙️ **PARAMÈTRES VENDEUR**\n\n"
            f" **Nom:** {bot.escape_markdown(user_data.get('seller_name', 'Non défini'))}\n"
            f" **Bio:** {bot.escape_markdown(user_data.get('seller_bio', 'Non définie')[:50] + '...' if user_data.get('seller_bio') and len(user_data.get('seller_bio', '')) > 50 else user_data.get('seller_bio', 'Non définie'))}\n"
            f" **Email:** `{email_display}`\n"
            f" **Adresse Solana:** `{solana_display}`"
        )

        # Layout selon SELLER_WORKFLOW_SPEC (sans Mdp)
        keyboard = [
            [InlineKeyboardButton(" Bio", callback_data='edit_seller_bio'),
             InlineKeyboardButton(" Nom", callback_data='edit_seller_name'),
             InlineKeyboardButton(" Mail", callback_data='edit_seller_email')],
            [InlineKeyboardButton(" Désactiver", callback_data='disable_seller_account'),
             InlineKeyboardButton(" Supprimer", callback_data='delete_seller_prompt'),
             InlineKeyboardButton(" Adresse", callback_data='edit_solana_address')],
            [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='seller_dashboard')]
        ]

        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def seller_logout(self, bot, query):
        """Déconnexion vendeur"""
        user_id = query.from_user.id
        lang = bot.get_user_state(user_id).get('lang', 'fr')

        # 🔧 FIX: Réinitialiser TOUS les états vendeur lors de la déconnexion
        bot.reset_user_state(user_id, keep={'lang'})

        # Set flag requiring re-login (temporary until next successful login)
        bot.state_manager.update_state(user_id, requires_relogin=True)
        bot.logout_seller(user_id)

        logout_text = (
            "✅ **Déconnexion réussie**\n\n"
            "Vous avez été déconnecté de votre compte vendeur.\n\n"
            "Pour vous reconnecter, vous devrez fournir :\n"
            "• Votre adresse email\n"
            "• Votre adresse Solana\n\n"
            "À bientôt !"
        ) if lang == 'fr' else (
            "✅ **Logout successful**\n\n"
            "You have been logged out from your seller account.\n\n"
            "To reconnect, you will need to provide:\n"
            "• Your email address\n"
            "• Your Solana address\n\n"
            "See you soon!"
        )

        await query.edit_message_text(
            logout_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Se reconnecter" if lang == 'fr' else "Login", callback_data='seller_login_menu'),
                InlineKeyboardButton("Retour" if lang == 'fr' else "Back", callback_data='back_main')
            ]]),
            parse_mode='Markdown'
        )

    async def delete_seller_prompt(self, bot, query):
        """Confirmation suppression compte vendeur"""
        await query.edit_message_text(
            "⚠️ **ATTENTION**\n\nVoulez-vous vraiment supprimer votre compte vendeur ?\n\n❌ Cette action est **irréversible**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirmer suppression", callback_data='delete_seller_confirm')],
                [InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='seller_settings')]
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
        """Process création vendeur - SIMPLIFIÉ (email + Solana uniquement)"""
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)
        step = user_state.get('step')
        lang = user_state.get('lang', 'fr')

        if step == 'email':
            # Étape 1/2: Email
            email = message_text.strip().lower()
            if not validate_email(email):
                error_msg = "❌ Email invalide" if lang == 'fr' else "❌ Invalid email"
                await update.message.reply_text(error_msg)
                return

            user_state['email'] = email
            user_state['step'] = 'solana_address'

            prompt_text = (
                "✅ **Email enregistré**\n\n"
                "Étape 2/2: Entrez votre **adresse Solana** (pour recevoir vos paiements)\n\n"
                "💡 **Format:** `1A2B3C...` (32-44 caractères)\n"
                "⚠️ **Important:** Vérifiez bien, c'est là que vous recevrez vos gains !"
            ) if lang == 'fr' else (
                "✅ **Email registered**\n\n"
                "Step 2/2: Enter your **Solana address** (to receive payments)\n\n"
                "💡 **Format:** `1A2B3C...` (32-44 characters)\n"
                "⚠️ **Important:** Double-check, this is where you'll receive your earnings!"
            )

            await update.message.reply_text(prompt_text, parse_mode='Markdown')

        elif step == 'solana_address':
            # Étape 2/2: Adresse Solana
            solana_address = message_text.strip()
            if not validate_solana_address(solana_address):
                error_msg = (
                    "❌ **Adresse Solana invalide**\n\n"
                    "Vérifiez le format depuis votre wallet\n"
                    "💡 L'adresse doit contenir entre 32 et 44 caractères"
                ) if lang == 'fr' else (
                    "❌ **Invalid Solana address**\n\n"
                    "Check the format from your wallet\n"
                    "💡 Address must be 32-44 characters"
                )
                await update.message.reply_text(error_msg, parse_mode='Markdown')
                return

            # Récupérer nom depuis Telegram
            telegram_user = update.effective_user
            seller_name = telegram_user.first_name or telegram_user.username or f"User{user_id}"

            # Créer compte vendeur SIMPLIFIÉ
            # Pas de password, pas de bio au début
            result = bot.seller_service.create_seller_account_simple(
                user_id=user_id,
                seller_name=seller_name,
                email=user_state['email'],
                solana_address=solana_address
            )

            bot.state_manager.reset_state(user_id, keep={'lang'})

            if result['success']:
                # Removed: bot.login_seller(user_id) - mapping removed

                # Envoyer email de bienvenue avec le style site2.html
                try:
                    from app.core.email_service import EmailService
                    email_service = EmailService()
                    # AWAIT AJOUTÉ ICI
                    await email_service.send_seller_welcome_email(
                        to_email=user_state['email'],
                        seller_name=seller_name,
                        solana_address=solana_address
                    )
                    logger.info(f"📧 Email de bienvenue envoyé à {user_state['email']}")
                except (psycopg2.Error, Exception) as e:
                    logger.error(f"Erreur envoi email bienvenue: {e}")
                    # Continue même si l'email échoue

                success_msg = (
                    "✅ **Compte vendeur créé !**\n\n"
                    f" Nom: **{seller_name}**\n"
                    f" Email: `{user_state['email']}`\n"
                    f" Solana: `{solana_address[:8]}...`\n\n"
                    " Vous êtes prêt à vendre !\n\n"
                    " Configurez votre bio et nom dans **Paramètres**"
                ) if lang == 'fr' else (
                    "✅ **Seller account created!**\n\n"
                    f" Name: **{seller_name}**\n"
                    f" Email: `{user_state['email']}`\n"
                    f" Solana: `{solana_address[:8]}...`\n\n"
                    " You're ready to sell!\n\n"
                    " Configure your bio and name in **Settings**"
                )

                try:
                    await update.message.reply_text(
                        success_msg,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "🏪 Dashboard" if lang == 'en' else "🏪 Dashboard",
                                callback_data='seller_dashboard'
                            )
                        ]]),
                        parse_mode='Markdown'
                    )
                except (psycopg2.Error, Exception) as e:
                    logger.error(f"Timeout sending success message: {e}")
                    await update.message.reply_text("✅ Compte créé ! /start")
            else:
                error_msg = result.get('error', 'Erreur inconnue')
                error_text = (
                    f"❌ **Erreur**\n\n{error_msg}"
                ) if lang == 'fr' else (
                    f"❌ **Error**\n\n{error_msg}"
                )

                await update.message.reply_text(
                    error_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔄 Réessayer" if lang == 'fr' else "🔄 Try again",
                            callback_data='create_seller'
                        ),
                        InlineKeyboardButton(
                            "🔙 Retour" if lang == 'fr' else "🔙 Back",
                            callback_data='back_main'
                        )
                    ]]),
                    parse_mode='Markdown'
                )

    async def process_seller_login_email(self, bot, update, message_text: str):
        """Process email de connexion vendeur"""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        lang = bot.get_user_state(user_id).get('lang', 'fr')

        # Valider format email
        from app.core.validation import validate_email
        if not validate_email(email):
            error_msg = "❌ Format email invalide" if lang == 'fr' else "❌ Invalid email format"
            await update.message.reply_text(error_msg)
            return

        # Vérifier que l'email correspond bien au vendeur
        user_data = self.user_repo.get_user(user_id)
        if not user_data or not user_data.get('is_seller'):
            error_msg = "❌ Vous n'avez pas de compte vendeur" if lang == 'fr' else "❌ You don't have a seller account"
            await update.message.reply_text(error_msg)
            bot.state_manager.reset_state(user_id, keep={'lang'})
            return

        if user_data.get('email') != email:
            error_msg = (
                "❌ **Email incorrect**\n\n"
                "Cet email ne correspond pas à votre compte vendeur."
            ) if lang == 'fr' else (
                "❌ **Incorrect email**\n\n"
                "This email doesn't match your seller account."
            )
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return

        # Connexion réussie
        bot.login_seller(user_id)
        bot.state_manager.update_state(user_id, requires_relogin=False)  # Remove re-login flag
        bot.state_manager.reset_state(user_id, keep={'lang'})

        # Envoyer email de notification de connexion
        try:
            from app.core.email_service import EmailService
            import datetime
            email_service = EmailService()

            # Récupérer infos pour l'email
            seller_name = user_data.get('seller_name', 'Vendeur')
            login_time = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")

            # AWAIT AJOUTÉ ICI
            await email_service.send_seller_login_notification(
                to_email=email,
                seller_name=seller_name,
                login_time=login_time
            )
            logger.info(f"📧 Email de connexion envoyé à {email}")
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Erreur envoi email connexion: {e}")
            # Continue même si l'email échoue

        success_msg = (
            "✅ **Connexion réussie !**\n\n"
            f"Bienvenue **{user_data.get('seller_name')}** 👋\n\n"
            "📧 Un email de confirmation vous a été envoyé."
        ) if lang == 'fr' else (
            "✅ **Login successful!**\n\n"
            f"Welcome **{user_data.get('seller_name')}** 👋\n\n"
            "📧 A confirmation email has been sent to you."
        )

        await update.message.reply_text(
            success_msg,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🏪 Dashboard" if lang == 'en' else "🏪 Dashboard",
                    callback_data='seller_dashboard'
                )
            ]]),
            parse_mode='Markdown'
        )

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
                # Remove $ symbol if present, then parse
                price_text_clean = message_text.replace('$', '').replace(',', '.').strip()
                price = float(price_text_clean)
                if price < 10 or price > 5000:
                    raise ValueError()

                # 🔍 DEBUG: État AVANT modification
                logger.info(f" PRICE STEP - User {user_id}")
                logger.info(f"   State BEFORE: {user_state}")

                product_data['price_usd'] = price
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
                    f"✅ **Prix :** ${price:.2f}\n\n"
                    f"📸 **Étape 5/6 :** Envoyez une image de couverture (optionnel)\n\n"
                    f"• Format: JPG/PNG\n"
                    f"• Taille max: 5MB\n"
                    f"• Recommandé: 800x600px minimum",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            except (ValueError, TypeError):
                await update.message.reply_text("❌ Prix invalide. Entrez un nombre entre $10 et $5000.")

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
            f"✅ **Catégorie :** {category_name}\n\n💰 **Étape 4/6 :** Prix en $ (ex: 29.99)",
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
            'price': f" **Étape 4/6 :** Prix en $ (minimum $10)\n\nCatégorie actuelle: {product_data.get('category', 'N/A')}",
            'cover_image': (
                f"📸 **Étape 5/6 :** Image de couverture (optionnel)\n\n"
                f"Prix actuel: ${product_data.get('price_usd', 0):.2f}\n\n"
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
            seller_id = telegram_id

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
            # 1. Size
            if photo_file.file_size > 5 * 1024 * 1024:  # 5MB max
                await update.message.reply_text("❌ Image trop volumineuse (max 5MB)")
                return

            # 2. Extension (for documents sent as images)
            if photo_as_document:
                from app.core.file_validation import validate_file_extension, get_file_category
                filename = getattr(photo_as_document, 'file_name', 'image.jpg')
                is_valid, error_msg = validate_file_extension(filename)
                if not is_valid:
                    await update.message.reply_text(f"❌ {error_msg}")
                    return
                # Ensure it's actually an image
                if get_file_category(filename) != 'image':
                    await update.message.reply_text("❌ Le fichier doit être une image (JPG, PNG, etc.)")
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
            cover_path, thumbnail_url = ImageUtils.save_telegram_photo(
                tmp_path, seller_id, temp_product_id
            )

            # Clean up temp file
            os.remove(tmp_path)

            if cover_path and thumbnail_url:
                product_data['cover_image_url'] = cover_path
                product_data['thumbnail_url'] = thumbnail_url
                product_data['temp_product_id'] = temp_product_id
                user_state['step'] = 'file'
                bot.state_manager.update_state(telegram_id, **user_state)

                # DEBUG LOG
                logger.info(f"📸 IMAGE STORED - Cover: {cover_path}, Thumbnail: {thumbnail_url}, Temp ID: {temp_product_id}")

                # Message clair pour encourager l'utilisation de la mini app
                lang = user_state.get('lang', 'fr')

                file_upload_message = (
                    f"✅ **Image de couverture enregistrée!**\n\n"
                    f"📁 **Étape 6/6 : Fichier de formation**\n\n"
                    f"⚠️ **FICHIERS VOLUMINEUX (>20 MB):**\n"
                    f"👉 Cliquez sur le bouton **\"📤 Upload via Mini App\"** ci-dessous\n"
                    f"   _(Permet upload jusqu'à 10 GB avec barre de progression)_\n\n"
                    f"📎 **Petits fichiers (<20 MB):**\n"
                    f"   Vous pouvez aussi envoyer directement ici"
                ) if lang == 'fr' else (
                    f"✅ **Cover image saved!**\n\n"
                    f"📁 **Step 6/6: Training file**\n\n"
                    f"⚠️ **LARGE FILES (>20 MB):**\n"
                    f"👉 Click the **\"📤 Upload via Mini App\"** button below\n"
                    f"   _(Allows upload up to 10 GB with progress bar)_\n\n"
                    f"📎 **Small files (<20 MB):**\n"
                    f"   You can also send directly here"
                )

                await update.message.reply_text(
                    file_upload_message,
                    parse_mode='Markdown',
                    reply_markup=self._get_product_creation_keyboard('file', lang)
                )
            else:
                await update.message.reply_text("❌ Erreur lors du traitement de l'image")

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error processing cover image: {e}")
            await update.message.reply_text("❌ Erreur lors du traitement de l'image")

    async def process_file_upload(self, bot, update, document):
        """Process file upload pour ajout produit"""
        try:
            telegram_id = update.effective_user.id
            # Get actual seller_id (handles multi-account mapping)
            seller_id = telegram_id

            user_state = bot.get_user_state(telegram_id)
            product_data = user_state.get('product_data', {})
            lang = user_state.get('lang', 'fr')

            # Validation du fichier
            # 1. Taille (100MB max - cohérent avec FAQ)
            if document.file_size > 100 * 1024 * 1024:  # 100MB max
                await update.message.reply_text("❌ Fichier trop volumineux (max 100MB)" if lang == 'fr' else "❌ File too large (max 100MB)")
                return

            # 2. Extension de fichier (sécurité critique)
            from app.core.file_validation import validate_file_extension
            is_valid, error_msg = validate_file_extension(document.file_name)
            if not is_valid:
                await update.message.reply_text(f"❌ {error_msg}")
                return

            # Télécharger et sauvegarder le fichier TEMPORAIREMENT
            file_info = await document.get_file()
            filename = await bot.save_uploaded_file(file_info, document.file_name)

            if not filename:
                await update.message.reply_text("❌ Erreur lors de la sauvegarde du fichier")
                return

            # Ajouter le fichier aux données produit (temporaire, sera uploadé sur B2)
            product_data['file_name'] = document.file_name
            product_data['file_size'] = document.file_size
            product_data['file_path'] = filename  # FIX: Set file_path for product creation

            # Créer le produit avec le seller_id mappé
            product_data['seller_id'] = seller_id
            product_id = bot.create_product(product_data)

            if product_id:
                # If we had a temp product_id, rename the image directory
                if 'temp_product_id' in product_data:
                    await self._rename_product_images(
                        seller_id,
                        product_data['temp_product_id'],
                        product_id,
                        product_data
                    )

                # --- CORRECTIF UPLOAD B2 (Thread non-bloquant) ---
                from app.core.file_utils import get_product_file_path
                from app.services.b2_storage_service import B2StorageService
                
                local_file_path = get_product_file_path(filename)
                
                # 1. On utilise le service directement (pas via helper obscure)
                b2_service = B2StorageService()
                
                # 2. On exécute l'upload dans un thread séparé (Executor)
                # Cela empêche le blocage du bot pendant les 20s de timeout ou l'upload
                loop = asyncio.get_running_loop()
                
                # Note: b2_service.upload_file est synchrone (bloquant) de base
                # On l'envoie dans un thread pool
                b2_url = await b2_service.upload_file(local_file_path, product_id)

                if b2_url:
                    # Update product with B2 URL
                    from app.domain.repositories.product_repo import ProductRepository
                    product_repo = ProductRepository()
                    product_repo.update_product_file_url(product_id, b2_url)
                    logger.info(f"✅ Product file uploaded to B2: {product_id}")

                    # Delete local file after successful upload
                    try:
                        if os.path.exists(local_file_path):
                            os.remove(local_file_path)
                            logger.info(f"🗑️ Local file deleted after B2 upload: {local_file_path}")
                    except Exception as e:
                        logger.error(f"⚠️ Failed to delete local file {local_file_path}: {e}")
                else:
                    logger.warning(f"⚠️ Failed to upload to B2, file kept locally: {product_id}")

                # Succès - réinitialiser l'état et rediriger
                bot.reset_user_state_preserve_login(telegram_id)

                # Envoyer emails de notification
                try:
                    from app.core.email_service import EmailService
                    email_service = EmailService()
                    user_data = self.user_repo.get_user(telegram_id)

                    if user_data and user_data.get('email'):
                        # Email pour tous les produits ajoutés
                        # AWAIT AJOUTÉ
                        await email_service.send_product_added_email(
                            to_email=user_data['email'],
                            seller_name=user_data.get('seller_name', 'Vendeur'),
                            product_title=product_data['title'],
                            product_price=f"{product_data['price_usd']:.2f}",
                            product_id=product_id
                        )
                        logger.info(f"📧 Email produit ajouté envoyé à {user_data['email']}")

                        # Vérifier si c'est le premier produit et envoyer email de félicitations
                        total_products = self.product_repo.count_products_by_seller(seller_id)
                        if total_products == 1:  # Premier produit
                            # AWAIT AJOUTÉ
                            await email_service.send_first_product_published_notification(
                                to_email=user_data['email'],
                                seller_name=user_data.get('seller_name', 'Vendeur'),
                                product_title=product_data['title'],
                                product_price=product_data['price_usd']
                            )
                            logger.info(f"📧 Email premier produit envoyé à {user_data['email']}")
                except (psycopg2.Error, Exception) as e:
                    logger.error(f"Erreur envoi emails produit: {e}")

                success_msg = f"✅ **Produit créé avec succès!**\n\n**ID:** {product_id}\n**Titre:** {product_data['title']}\n**Prix:** ${product_data['price_usd']:.2f}"

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

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error processing file upload: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await update.message.reply_text("Erreur lors du traitement du fichier")

    async def _rename_product_images(self, seller_id, temp_product_id, final_product_id, product_data):
        """Rename product image directory, upload to B2, and UPDATE DATABASE with B2 URLs"""
        try:
            import shutil
            from app.core.database_init import get_postgresql_connection
            from app.core.db_pool import put_connection
            from app.core import settings as core_settings
            from app.services.b2_storage_service import B2StorageService

            old_dir = os.path.join('data', 'product_images', str(seller_id), temp_product_id)
            new_dir = os.path.join('data', 'product_images', str(seller_id), final_product_id)

            if os.path.exists(old_dir):
                # Rename directory
                shutil.move(old_dir, new_dir)
                logger.info(f"📁 Renamed directory: {old_dir} -> {new_dir}")

                # Initialize B2 service
                b2_service = B2StorageService()

                # Upload images to B2 and get URLs
                cover_b2_url = None
                thumb_b2_url = None

                cover_local_path = os.path.join(new_dir, 'cover.jpg')
                thumb_local_path = os.path.join(new_dir, 'thumb.jpg')

                # Upload cover image to B2
                if os.path.exists(cover_local_path):
                    cover_b2_key = f"products/{final_product_id}/cover.jpg"
                    
                    # CORRECTION: Exécuter l'upload (qui est synchrone) dans un thread
                    loop = asyncio.get_running_loop()
                    cover_b2_url = await loop.run_in_executor(
                        None, 
                        b2_service.upload_file, 
                        cover_local_path, 
                        cover_b2_key
                    )
                    
                    if cover_b2_url:
                        logger.info(f"📤 Cover uploaded to B2: {cover_b2_url}")
                    else:
                        logger.warning(f"⚠️ Failed to upload cover to B2, using local path")
                        cover_b2_url = cover_local_path

                # Upload thumbnail to B2
                if os.path.exists(thumb_local_path):
                    thumb_b2_key = f"products/{final_product_id}/thumb.jpg"
                    
                    # CORRECTION: Idem pour la thumbnail
                    loop = asyncio.get_running_loop()
                    thumb_b2_url = await loop.run_in_executor(
                        None, 
                        b2_service.upload_file, 
                        thumb_local_path, 
                        thumb_b2_key
                    )
                    
                    if thumb_b2_url:
                        logger.info(f"📤 Thumbnail uploaded to B2: {thumb_b2_url}")
                    else:
                        logger.warning(f"⚠️ Failed to upload thumbnail to B2, using local path")
                        thumb_b2_url = thumb_local_path

                # Update DATABASE with B2 URLs (or local paths as fallback)
                if cover_b2_url or thumb_b2_url:
                    conn = get_postgresql_connection()
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    try:
                        cursor.execute(
                            '''
                            UPDATE products
                            SET cover_image_url = %s, thumbnail_url = %s
                            WHERE product_id = %s
                            ''',
                            (cover_b2_url, thumb_b2_url, final_product_id)
                        )
                        conn.commit()
                        logger.info(f"✅ Updated DB with B2 URLs: cover={cover_b2_url}, thumb={thumb_b2_url}")
                    except Exception as db_error:
                        logger.error(f"❌ DB update failed: {db_error}")
                        conn.rollback()
                    finally:
                        put_connection(conn)

                logger.info(f"✅ Product images processed: {temp_product_id} -> {final_product_id} (B2 + local cache)")
            else:
                logger.warning(f"⚠️ Old directory not found: {old_dir}")
        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error processing product images: {e}")

    async def process_seller_settings(self, bot, update, message_text: str):
        """Process paramètres vendeur"""
        user_id = update.effective_user.id
        state = bot.state_manager.get_state(user_id)
        step = state.get('step')

        lang = state.get('lang', 'fr')
        logger.info(f"🔧 process_seller_settings called - step: {step}, user: {user_id}")

        if step == 'edit_name':
            new_name = message_text.strip()[:50]
            success = self.user_repo.update_seller_name(user_id, new_name)
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text(
                "✅ Nom mis à jour !" if success else "❌ Erreur mise à jour nom.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Dashboard", callback_data='seller_dashboard')
                ]])
            )

        elif step == 'edit_bio':
            new_bio = message_text.strip()[:500]
            success = self.user_repo.update_seller_bio(user_id, new_bio)
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text(
                "✅ Biographie mise à jour !" if success else "❌ Erreur mise à jour bio.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Dashboard", callback_data='seller_dashboard')
                ]])
            )

        elif step == 'edit_email':
            new_email = message_text.strip().lower()
            if not validate_email(new_email):
                await update.message.reply_text("❌ Email invalide")
                return
            success = self.user_repo.update_seller_email(user_id, new_email)
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text(
                "✅ Email mis à jour !" if success else "❌ Erreur mise à jour email.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Dashboard", callback_data='seller_dashboard')
                ]])
            )

        elif step == 'edit_solana_address':
            new_address = message_text.strip()
            if not validate_solana_address(new_address):
                await update.message.reply_text("❌ Adresse Solana invalide (32-44 caractères)")
                return
            success = self.user_repo.update_seller_solana_address(user_id, new_address)
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text(
                "✅ Adresse Solana mise à jour !" if success else "❌ Erreur mise à jour adresse.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Dashboard", callback_data='seller_dashboard')
                ]])
            )

    # Missing methods from monolith - extracted from bot_mlt.py
    async def payout_history(self, bot, query, lang):
        """Historique payouts vendeur"""
        user_id = query.from_user.id
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT total_amount_sol, payout_status, created_at
                FROM seller_payouts
                WHERE seller_user_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            ''', (user_id,))
            payouts = cursor.fetchall()
            put_connection(conn)

            if not payouts:
                text = " Aucun payout trouvé." if lang == 'fr' else " No payouts found."
            else:
                text = " **HISTORIQUE PAYOUTS**\n\n" if lang == 'fr' else " **PAYOUT HISTORY**\n\n"
                for amount, status, date in payouts:
                    text += f"• {amount:.4f} SOL - {status} - {date[:10]}\n"

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    back_to_main_button(lang)
                ]]),
                parse_mode='Markdown'
            )

        except (psycopg2.Error, Exception) as e:
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
            # 🔧 FIX: Réinitialiser les états d'édition pour ce produit
            user_id = query.from_user.id
            bot.reset_user_state(user_id, keep={'lang', 'requires_relogin'})

            # Get product details
            product = self.product_repo.get_product_by_id(product_id)
            if not product:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
                await safe_transition_to_text(
                    query,
                    "❌ Produit introuvable." if lang == 'fr' else "❌ Product not found.",
                    keyboard
                )
                return

            title = product.get('title', 'Sans titre')
            price = product.get('price_usd', 0)
            status = product.get('status', 'active')

            menu_text = f"✏️ **Édition: {title}**\n\n💰 Prix: ${price:.2f}\n📊 Statut: {status}\n\nQue voulez-vous modifier ?"

            keyboard = [
                [InlineKeyboardButton(" Modifier titre" if lang == 'fr' else " Edit title",
                                    callback_data=f'edit_field_title_{product_id}')],
                [InlineKeyboardButton(" Modifier description" if lang == 'fr' else " Edit description",
                                    callback_data=f'edit_field_description_{product_id}')],
                [InlineKeyboardButton(" Modifier prix" if lang == 'fr' else " Edit price",
                                    callback_data=f'edit_field_price_{product_id}')],
                [InlineKeyboardButton("🔄 Changer statut" if lang == 'fr' else "🔄 Toggle status",
                                    callback_data=f'edit_field_toggle_{product_id}')],
                [InlineKeyboardButton("🗑️ Supprimer" if lang == 'fr' else "🗑️ Delete",
                                    callback_data=f'confirm_delete_{product_id}')],
                [InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')]
            ]

            await safe_transition_to_text(
                query,
                menu_text,
                InlineKeyboardMarkup(keyboard)
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in edit_product_menu: {e}")
            keyboard_error = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
            ]])
            await safe_transition_to_text(
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
                await safe_transition_to_text(
                    query,
                    "❌ Produit introuvable." if lang == 'fr' else "❌ Product not found.",
                    keyboard
                )
                return

            title = product.get('title', 'Sans titre')

            # Delete the product - Get actual seller_id (not telegram_id)
            telegram_id = query.from_user.id
            seller_user_id = telegram_id

            if not seller_user_id:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
                await safe_transition_to_text(
                    query,
                    "❌ Vous devez être connecté en tant que vendeur." if lang == 'fr' else "❌ You must be logged in as a seller.",
                    keyboard
                )
                return

            success = self.product_repo.delete_product(product_id, seller_user_id)

            if success:
                # Envoyer email de notification de suppression
                try:
                    user_data = self.user_repo.get_user(seller_user_id)
                    if user_data and user_data.get('email'):
                        from app.core.email_service import EmailService
                        email_service = EmailService()
                        # AWAIT AJOUTÉ
                        await email_service.send_product_removed_email(
                            to_email=user_data['email'],
                            seller_name=user_data.get('seller_name', 'Vendeur'),
                            product_title=title,
                            product_id=product_id,
                            reason="à votre demande"
                        )
                        logger.info(f"📧 Email produit supprimé envoyé à {user_data['email']}")
                except Exception as e:
                    logger.error(f"Erreur envoi email produit supprimé: {e}")

                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Mes produits" if lang == 'fr' else "🔙 My products", callback_data='my_products')
                ]])
                await safe_transition_to_text(
                    query,
                    f"✅ **Produit supprimé**\n\n📦 {title} a été supprimé avec succès." if lang == 'fr'
                    else f"✅ **Product deleted**\n\n📦 {title} has been deleted successfully.",
                    keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
                await safe_transition_to_text(
                    query,
                    "❌ Impossible de supprimer le produit." if lang == 'fr' else "❌ Could not delete product.",
                    keyboard
                )

        except (psycopg2.Error, Exception) as e:
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
            # Verify ownership using helper
            product = await self._verify_product_ownership(bot, query, product_id)
            if not product:
                return

            user_id = query.from_user.id

            # Set editing state using helper
            self._set_editing_state(bot, user_id, f'product_{field}', product_id)

            # Show appropriate prompt based on field
            if field == 'price':
                await safe_transition_to_text(
                    query,
                    f" **Modifier le prix de:** {product.get('title', 'N/A')}\n\n"
                    f"Prix actuel: ${product.get('price_usd', 0):.2f}\n\n"
                    f"Entrez le nouveau prix en $:" if lang == 'fr' else
                    f" **Edit price for:** {product.get('title', 'N/A')}\n\n"
                    f"Current price: ${product.get('price_usd', 0):.2f}\n\n"
                    f"Enter new price in $:",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                    ]])
                )
            elif field == 'title':
                await safe_transition_to_text(
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
                await safe_transition_to_text(
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
                await safe_transition_to_text(
                    query,
                    "❌ Champ non éditable." if lang == 'fr' else "❌ Field not editable.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data=f'edit_product_{product_id}')
                    ]])
                )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in edit_product_field: {e}")
            await safe_transition_to_text(
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

            # Set editing state using helper
            self._set_editing_state(bot, user_id, 'seller_name', True)

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

        except (psycopg2.Error, Exception) as e:
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

            # Set editing state using helper
            self._set_editing_state(bot, user_id, 'seller_bio', True)

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

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in edit_seller_bio: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')
                ]])
            )

    async def generate_shop_link(self, bot, query, lang):
        """Generate a shop link for the seller to share on social media"""
        try:
            from app.core.settings import settings
            user_id = query.from_user.id

            # Check if user is a seller
            user_data = self.user_repo.get_user(user_id)
            if not user_data or not user_data.get('is_seller'):
                await query.answer("❌ Vous devez être vendeur" if lang == 'fr' else "❌ You must be a seller", show_alert=True)
                return

            # Get seller's active products count
            products = self.product_repo.get_products_by_seller(user_id)
            active_count = len([p for p in products if p.get('status') == 'active'])

            seller_name = user_data.get('seller_name', 'Vendeur')

            # Generate shop link with seller ID payload
            bot_username = settings.TELEGRAM_BOT_USERNAME
            shop_link = f"https://t.me/{bot_username}?start=shop_{user_id}"

            message = (
                f"🔗 **Lien de votre boutique**\n\n"
                f"**Vendeur:** {seller_name}\n"
                f"**Produits actifs:** {active_count}\n\n"
                f"📋 Copiez ce lien pour partager votre boutique:\n"
                f"`{shop_link}`\n\n"
                f"💡 Partagez ce lien sur vos réseaux sociaux pour promouvoir tous vos produits !"
                if lang == 'fr' else
                f"🔗 **Your shop link**\n\n"
                f"**Seller:** {seller_name}\n"
                f"**Active products:** {active_count}\n\n"
                f"📋 Copy this link to share your shop:\n"
                f"`{shop_link}`\n\n"
                f"💡 Share this link on social media to promote all your products!"
            )

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')
                ]])
            )

        except Exception as e:
            logger.error(f"Error in generate_shop_link: {e}")
            await query.answer("❌ Erreur" if lang == 'fr' else "❌ Error", show_alert=True)

    async def generate_product_link(self, bot, query, product_id: str, lang):
        """Generate a deep link for a specific product"""
        try:
            from app.core.settings import settings
            user_id = query.from_user.id

            # Check if user owns this product
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product['seller_user_id'] != user_id:
                await query.answer("❌ Produit introuvable" if lang == 'fr' else "❌ Product not found", show_alert=True)
                return

            # Generate deep link
            bot_username = settings.TELEGRAM_BOT_USERNAME
            product_link = f"https://t.me/{bot_username}?start=product_{product_id}"

            message = (
                f"🔗 **Lien de partage produit**\n\n"
                f"**Produit:** {product['title']}\n"
                f"**Prix:** ${product['price_usd']:.2f}\n"
                f"**ID:** {product_id}\n\n"
                f"📋 Copiez ce lien pour partager ce produit:\n"
                f"`{product_link}`\n\n"
                f"💡 Toute personne cliquant sur ce lien verra directement votre produit dans le bot !\n\n"
                f"📱 Idéal pour:\n"
                f"• Instagram Stories\n"
                f"• Posts Facebook/Twitter\n"
                f"• Messages privés\n"
                f"• Forums et communautés"
                if lang == 'fr' else
                f"🔗 **Product share link**\n\n"
                f"**Product:** {product['title']}\n"
                f"**Price:** ${product['price_usd']:.2f}\n"
                f"**ID:** {product_id}\n\n"
                f"📋 Copy this link to share this product:\n"
                f"`{product_link}`\n\n"
                f"💡 Anyone clicking this link will see your product directly in the bot!\n\n"
                f"📱 Perfect for:\n"
                f"• Instagram Stories\n"
                f"• Facebook/Twitter posts\n"
                f"• Private messages\n"
                f"• Forums and communities"
            )

            # Envoyer un nouveau message (le carousel est une photo, pas du texte)
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour produit" if lang == 'fr' else "🔙 Back to product", callback_data='my_products')
                ]])
            )
            await query.answer()  # Acknowledge the callback

        except Exception as e:
            logger.error(f"Error in generate_product_link: {e}")
            await query.answer("❌ Erreur" if lang == 'fr' else "❌ Error", show_alert=True)

    async def edit_seller_email(self, bot, query, lang):
        """Edit seller email"""
        try:
            user_id = query.from_user.id
            user_data = self.user_repo.get_user(user_id)
            if not user_data or not user_data.get('is_seller'):
                await query.edit_message_text(
                    "❌ Vous devez être vendeur pour modifier ces informations." if lang == 'fr' else "❌ You must be a seller to edit this information.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')]])
                )
                return

            bot.state_manager.update_state(user_id, editing_settings=True, step='edit_email')
            current_email = user_data.get('email', 'Non défini')
            await query.edit_message_text(
                f"📧 **Modifier l'email**\n\nEmail actuel: {current_email}\n\nEntrez votre nouvel email:" if lang == 'fr' else f"📧 **Edit email**\n\nCurrent email: {current_email}\n\nEnter your new email:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='seller_settings')]])
            )
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in edit_seller_email: {e}")
            await query.edit_message_text("❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')]]))

    async def edit_solana_address(self, bot, query, lang):
        """Edit Solana address"""
        try:
            user_id = query.from_user.id
            user_data = self.user_repo.get_user(user_id)
            if not user_data or not user_data.get('is_seller'):
                await query.edit_message_text(
                    "❌ Vous devez être vendeur pour modifier ces informations." if lang == 'fr' else "❌ You must be a seller to edit this information.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')]])
                )
                return

            bot.state_manager.update_state(user_id, editing_settings=True, step='edit_solana_address')
            current_addr = user_data.get('seller_solana_address', 'Non configurée')
            await query.edit_message_text(
                f" **Modifier l'adresse Solana**\n\nAdresse actuelle: {current_addr}\n\nEntrez votre nouvelle adresse Solana (32-44 caractères):" if lang == 'fr' else f" **Edit Solana address**\n\nCurrent address: {current_addr}\n\nEnter your new Solana address (32-44 characters):",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='seller_settings')]])
            )
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in edit_solana_address: {e}")
            await query.edit_message_text("❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='seller_settings')]]))

    async def disable_seller_account(self, bot, query, lang):
        """Disable seller account temporarily"""
        await query.edit_message_text(
            "⚠️ **DÉSACTIVER COMPTE VENDEUR**\n\nÊtes-vous sûr de vouloir désactiver votre compte vendeur ?\n\n• Vos produits seront cachés\n• Vous pourrez réactiver plus tard" if lang == 'fr' else "⚠️ **DISABLE SELLER ACCOUNT**\n\nAre you sure you want to disable your seller account?\n\n• Your products will be hidden\n• You can reactivate later",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirmer" if lang == 'fr' else "✅ Confirm", callback_data='disable_seller_confirm')],
                [InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='seller_settings')]
            ]),
            parse_mode='Markdown'
        )

    async def disable_seller_confirm(self, bot, query):
        """Confirm seller account disable"""
        user_id = query.from_user.id
        success = self.user_repo.disable_seller_account(user_id)
        if success:
            await query.edit_message_text(
                "✅ **Compte vendeur désactivé**\n\nVos produits sont maintenant cachés.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu principal", callback_data='back_main')]]),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Erreur lors de la désactivation")

    async def edit_product_price_prompt(self, bot, query, product_id, lang):
        """Prompt for editing product price"""
        try:
            # Verify ownership using helper
            product = await self._verify_product_ownership(bot, query, product_id)
            if not product:
                return

            user_id = query.from_user.id

            # Set editing state using helper
            self._set_editing_state(bot, user_id, 'product_price', product_id)

            await safe_transition_to_text(
                query,
                f" **Modifier le prix de:** {product.get('title', 'N/A')}\n\n"
                f"Prix actuel: ${product.get('price_usd', 0):.2f}\n\n"
                f"Entrez le nouveau prix en $ (10-5000):" if lang == 'fr' else
                f" **Edit price for:** {product.get('title', 'N/A')}\n\n"
                f"Current price: ${product.get('price_usd', 0):.2f}\n\n"
                f"Enter new price in $ (10-5000):",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                ]])
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in edit_product_price_prompt: {e}")
            await safe_transition_to_text(
                query,
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
            )

    async def edit_product_title_prompt(self, bot, query, product_id, lang):
        """Prompt for editing product title"""
        try:
            # Verify ownership using helper
            product = await self._verify_product_ownership(bot, query, product_id)
            if not product:
                return

            user_id = query.from_user.id

            # Set editing state using helper
            self._set_editing_state(bot, user_id, 'product_title', product_id)

            await safe_transition_to_text(
                query,
                f"📝 **Modifier le titre de:** {product.get('title', 'N/A')}\n\n"
                f"Entrez le nouveau titre:" if lang == 'fr' else
                f"📝 **Edit title for:** {product.get('title', 'N/A')}\n\n"
                f"Enter new title:",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data=f'edit_product_{product_id}')
                ]])
            )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in edit_product_title_prompt: {e}")
            await safe_transition_to_text(
                query,
                "❌ Erreur lors de l'édition." if lang == 'fr' else "❌ Edit error.",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='my_products')
                ]])
            )

    async def toggle_product_status(self, bot, query, product_id, lang):
        """Toggle product active/inactive status"""
        try:
            # Verify ownership using helper
            product = await self._verify_product_ownership(bot, query, product_id)
            if not product:
                return

            # Check if product was deactivated by admin
            deactivated_by_admin = product.get('deactivated_by_admin', False)
            admin_reason = product.get('admin_deactivation_reason', '')

            if deactivated_by_admin and product.get('status') == 'inactive':
                # CRITICAL: Prevent seller from reactivating product disabled by admin
                await safe_transition_to_text(
                    query,
                    f"🚫 **PRODUIT DÉSACTIVÉ PAR L'ADMINISTRATEUR**\n\n"
                    f"Ce produit a été désactivé par un administrateur et ne peut pas être réactivé.\n\n"
                    f"**Raison:** {admin_reason}\n\n"
                    f"Contactez le support pour plus d'informations." if lang == 'fr'
                    else
                    f"🚫 **PRODUCT DISABLED BY ADMINISTRATOR**\n\n"
                    f"This product has been disabled by an administrator and cannot be reactivated.\n\n"
                    f"**Reason:** {admin_reason}\n\n"
                    f"Contact support for more information.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data=f'edit_product_{product_id}')
                    ]]),
                    parse_mode='Markdown'
                )
                return

            # Toggle status
            current_status = product.get('status', 'active')
            new_status = 'inactive' if current_status == 'active' else 'active'

            success = self.product_repo.update_status(product_id, new_status)

            if success:
                status_text = "activé" if new_status == 'active' else "désactivé"
                status_text_en = "activated" if new_status == 'active' else "deactivated"
                await safe_transition_to_text(
                    query,
                    f"✅ Produit {status_text} avec succès." if lang == 'fr' else f"✅ Product {status_text_en} successfully.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data=f'edit_product_{product_id}')
                    ]])
                )
            else:
                await safe_transition_to_text(
                    query,
                    "❌ Erreur lors de la mise à jour." if lang == 'fr' else "❌ Update error.",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data=f'edit_product_{product_id}')
                    ]])
                )

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error in toggle_product_status: {e}")
            await safe_transition_to_text(
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
            user_id = update.effective_user.id

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

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Erreur maj titre produit: {e}")
            # CORRECTION: Réinitialiser l'état même en cas d'erreur
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text(i18n(lang, 'err_update_error'))
            return False
    
    async def process_product_price_update(self, bot, update, product_id: str, price_text: str, lang: str = 'fr') -> bool:
        """Process product price update with consolidated logic"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = update.effective_user.id

            # Validate ownership
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await update.message.reply_text(i18n(lang, 'err_product_not_found'))
                return False

            # Parse and validate price (remove $ symbol if present)
            price_text_clean = price_text.replace('$', '').replace(',', '.').strip()
            price_usd = float(price_text_clean)
            if price_usd < 10 or price_usd > 5000:
                raise ValueError("Prix hors limites")

            # Update price (price is already in USD, no conversion needed)
            success = self.product_repo.update_price(product_id, user_id, price_usd)

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
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Erreur maj prix produit: {e}")
            await update.message.reply_text(i18n(lang, 'err_price_update_error'))
            return False

    async def process_product_description_update(self, bot, update, product_id: str, new_description: str, lang: str = 'fr') -> bool:
        """Process product description update"""
        try:
            # Get actual seller_id (handles multi-account mapping)
            user_id = update.effective_user.id

            # Validate ownership
            product = self.product_repo.get_product_by_id(product_id)
            if not product or product.get('seller_user_id') != user_id:
                await update.message.reply_text(
                    "❌ Produit introuvable ou vous n'êtes pas le propriétaire" if lang == 'fr' else "❌ Product not found or unauthorized"
                )
                return False

            # Validate description (10-1000 characters)
            if len(new_description) < 10 or len(new_description) > 1000:
                await update.message.reply_text(
                    "❌ La description doit contenir entre 10 et 1000 caractères." if lang == 'fr' else "❌ Description must be between 10 and 1000 characters."
                )
                return False

            # Reset state BEFORE update
            bot.state_manager.reset_state(user_id, keep={'lang'})

            # Update description in database
            success = self.product_repo.update_description(product_id, user_id, new_description)

            if success:
                await update.message.reply_text(
                    "✅ **Description mise à jour avec succès !**" if lang == 'fr' else "✅ **Description updated successfully!**",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔙 Mon Dashboard" if lang == 'fr' else "🔙 My Dashboard",
                            callback_data='seller_dashboard'
                        )
                    ]]),
                    parse_mode='Markdown'
                )
                return True
            else:
                await update.message.reply_text(
                    "❌ Erreur lors de la mise à jour" if lang == 'fr' else "❌ Update error",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔙 Mon Dashboard" if lang == 'fr' else "🔙 My Dashboard",
                            callback_data='seller_dashboard'
                        )
                    ]])
                )
                return False

        except (psycopg2.Error, Exception) as e:
            logger.error(f"Erreur maj description produit: {e}")
            bot.state_manager.reset_state(user_id, keep={'lang'})
            await update.message.reply_text(
                "❌ Erreur lors de la mise à jour" if lang == 'fr' else "❌ Update error"
            )
            return False

    async def seller_messages(self, bot, query, lang: str):
        """Affiche les messages/tickets reçus par le vendeur concernant ses produits"""
        seller_id = query.from_user.id
        
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Récupérer les tickets liés aux produits du vendeur
            cursor.execute('''
                SELECT 
                    t.ticket_id,
                    t.subject,
                    t.created_at,
                    t.status,
                    u.first_name as buyer_name,
                    p.title as product_title,
                    t.creator_user_id
                FROM tickets t
                LEFT JOIN users u ON t.creator_user_id = u.user_id
                LEFT JOIN products p ON t.product_id = p.product_id
                WHERE p.seller_user_id = %s
                ORDER BY t.created_at DESC
                LIMIT 20
            ''', (seller_id,))
            
            tickets = cursor.fetchall()
            put_connection(conn)
            
            if not tickets:
                text = (
                    "💬 **NO MESSAGES**\n\n"
                    "You have no messages from buyers yet."
                    if lang == 'en' else
                    "💬 **AUCUN MESSAGE**\n\n"
                    "Vous n'avez pas encore de messages d'acheteurs."
                )
                
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔙 Dashboard" if lang == 'en' else "🔙 Dashboard",
                            callback_data='seller_dashboard'
                        )
                    ]]),
                    parse_mode='Markdown'
                )
                return
            
            # Construire le message avec la liste des tickets
            text = (
                f"💬 **MESSAGES FROM BUYERS** ({len(tickets)})\n\n"
                if lang == 'en' else
                f"💬 **MESSAGES DES ACHETEURS** ({len(tickets)})\n\n"
            )
            
            keyboard = []
            for ticket in tickets[:10]:  # Limiter à 10 pour pas surcharger
                ticket_id, subject, created_at, status, buyer_name, product_title, creator_id = ticket
                
                # Status emoji
                status_emoji = "✅" if status == 'closed' else "🟢" if status == 'open' else "🟡"
                
                # Créer le bouton
                button_label = f"{status_emoji} {buyer_name or 'Acheteur'}: {subject[:30]}..."
                keyboard.append([
                    InlineKeyboardButton(
                        button_label,
                        callback_data=f'view_ticket_{ticket_id}'
                    )
                ])
            
            # Bouton retour
            keyboard.append([
                InlineKeyboardButton(
                    "🔙 Dashboard" if lang == 'en' else "🔙 Dashboard",
                    callback_data='seller_dashboard'
                )
            ])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except (psycopg2.Error, Exception) as e:
            logger.error(f"Error showing seller messages: {e}")
            await query.edit_message_text(
                "❌ Error loading messages." if lang == 'en' else "❌ Erreur de chargement.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔙 Dashboard" if lang == 'en' else "🔙 Dashboard",
                        callback_data='seller_dashboard'
                    )
                ]])
            )