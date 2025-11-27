"""
Enhanced Seller Analytics Handlers with Charts and CSV Export
À intégrer dans sell_handlers.py
"""

import logging
import psycopg2.extras
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from io import BytesIO

from app.services.chart_service import ChartService
from app.services.export_service import ExportService
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection

logger = logging.getLogger(__name__)


class SellerAnalyticsEnhanced:
    """
    Méthodes d'analytics améliorées pour les vendeurs
    À ajouter dans la classe des sell_handlers
    """

    def __init__(self):
        self.chart_service = ChartService()
        self.export_service = ExportService()

    async def seller_analytics_enhanced(self, bot, query, lang: str = 'fr'):
        """
        Affiche les analytics vendeur avec graphiques visuels

        Envoie:
        - Texte avec stats résumées
        - Image du graphique combiné (revenus + ventes)
        - Boutons pour export CSV et autres graphiques
        """
        seller_id = query.from_user.id

        try:
            # Notifier l'utilisateur
            await query.answer("📊 Génération des graphiques...")

            # ═══════════════════════════════════════════════════════
            # RÉCUPÉRER LES DONNÉES
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
            # PRÉPARER LES DONNÉES POUR GRAPHIQUE
            # ═══════════════════════════════════════════════════════

            # Compléter avec zéros pour jours manquants (30 derniers jours)
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
            # GÉNÉRER LE GRAPHIQUE
            # ═══════════════════════════════════════════════════════

            if sum(revenues_data) > 0:  # Seulement si données disponibles
                chart_url = self.chart_service.generate_combined_dashboard_chart(
                    dates=dates_labels,
                    revenues=revenues_data,
                    sales=sales_data,
                    width=800,
                    height=400
                )
            else:
                chart_url = None

            # ═══════════════════════════════════════════════════════
            # CONSTRUIRE LE MESSAGE TEXTE
            # ═══════════════════════════════════════════════════════

            text = f"""📊 **TABLEAU DE BORD VENDEUR**

 **Revenus**
├─ Brut: ${global_stats['total_revenue']:.2f}
├─ Commission: -${global_stats['total_commission']:.2f}
└─ Net: ${global_stats['net_revenue']:.2f}

 **Produits & Ventes**
├─ Produits: {product_count['active']}/{product_count['total']} actifs
└─ Ventes: {global_stats['total_sales']} commandes

🏆 **Top 5 Produits**"""

            if top_products:
                for i, p in enumerate(top_products, 1):
                    title_truncated = p['title'][:25] + '...' if len(p['title']) > 25 else p['title']
                    text += f"\n{i}. {title_truncated}"
                    text += f"\n   💵 ${p['revenue']:.2f} • 📦 {p['sales']} ventes"
            else:
                text += "\n\n_Aucun produit vendu pour le moment_"

            text += "\n\n📈 Graphique ci-dessous pour les 30 derniers jours"

            # ═══════════════════════════════════════════════════════
            # KEYBOARD
            # ═══════════════════════════════════════════════════════

            keyboard = [
                [
                    InlineKeyboardButton("📊 Graphiques détaillés", callback_data='analytics_detailed_charts'),
                    InlineKeyboardButton("📥 Export CSV", callback_data='analytics_export_csv')
                ],
                [
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data='seller_analytics_enhanced'),
                    InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # ═══════════════════════════════════════════════════════
            # ENVOYER LE MESSAGE
            # ═══════════════════════════════════════════════════════

            # Supprimer le message précédent
            try:
                await query.message.delete()
            except:
                pass

            # Envoyer le texte
            if chart_url:
                # Envoyer graphique en photo
                await bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=chart_url,
                    caption=text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                # Pas encore de données, juste texte
                await bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text + "\n\n_Pas encore de données de vente pour afficher un graphique_",
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
        Affiche plusieurs graphiques détaillés

        Envoie :
        - Graphique revenus seuls
        - Graphique ventes seules
        - Graphique performance par produit
        """
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

            # Compléter avec zéros
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
            # GÉNÉRER LES GRAPHIQUES
            # ═══════════════════════════════════════════════════════

            charts_to_send = []

            # Graphique 1 : Revenus
            if sum(revenues_data) > 0:
                revenue_chart_url = self.chart_service.generate_revenue_chart(
                    dates=dates_labels,
                    revenues=revenues_data
                )
                charts_to_send.append(('Revenus', revenue_chart_url))

            # Graphique 2 : Ventes
            if sum(sales_data) > 0:
                sales_chart_url = self.chart_service.generate_sales_chart(
                    dates=dates_labels,
                    sales=sales_data
                )
                charts_to_send.append(('Ventes', sales_chart_url))

            # Graphique 3 : Performance produits
            if product_performance and len(product_performance) > 0:
                product_titles = [p['title'][:20] for p in product_performance]
                product_sales = [int(p['sales']) for p in product_performance]
                product_revenues = [float(p['revenue']) for p in product_performance]

                product_chart_url = self.chart_service.generate_product_performance_chart(
                    product_titles=product_titles,
                    sales_counts=product_sales,
                    revenues=product_revenues
                )
                charts_to_send.append(('Performance Produits', product_chart_url))

            # ═══════════════════════════════════════════════════════
            # ENVOYER LES GRAPHIQUES
            # ═══════════════════════════════════════════════════════

            if charts_to_send:
                await query.message.reply_text("📊 Graphiques détaillés :")

                for title, url in charts_to_send:
                    await bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=url,
                        caption=f"**{title}**",
                        parse_mode='Markdown'
                    )

                # Bouton retour
                keyboard = [[InlineKeyboardButton("🔙 Retour Analytics", callback_data='seller_analytics_enhanced')]]
                await bot.send_message(
                    chat_id=query.message.chat_id,
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
        Exporte les statistiques vendeur en CSV et envoie le fichier
        """
        seller_id = query.from_user.id

        try:
            await query.answer("📥 Génération du fichier CSV...")

            # ═══════════════════════════════════════════════════════
            # RÉCUPÉRER LES DONNÉES
            # ═══════════════════════════════════════════════════════
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Infos vendeur
            cursor.execute("""
                SELECT seller_name, email
                FROM users
                WHERE user_id = %s
            """, (seller_id,))
            seller_info = cursor.fetchone()
            seller_name = seller_info['seller_name'] if seller_info else f"Seller_{seller_id}"

            # Tous les produits
            cursor.execute("""
                SELECT * FROM products
                WHERE seller_user_id = %s
                ORDER BY created_at DESC
            """, (seller_id,))
            products = cursor.fetchall()

            # Toutes les commandes
            cursor.execute("""
                SELECT * FROM orders
                WHERE seller_user_id = %s
                ORDER BY created_at DESC
            """, (seller_id,))
            orders = cursor.fetchall()

            put_connection(conn)

            # ═══════════════════════════════════════════════════════
            # GÉNÉRER LE CSV
            # ═══════════════════════════════════════════════════════

            csv_file = self.export_service.export_seller_stats_to_csv(
                seller_user_id=seller_id,
                seller_name=seller_name,
                products=products,
                orders=orders
            )

            # Nom du fichier
            filename = self.export_service.generate_filename('seller_stats', str(seller_id))

            # ═══════════════════════════════════════════════════════
            # ENVOYER LE FICHIER
            # ═══════════════════════════════════════════════════════

            await bot.send_document(
                chat_id=query.message.chat_id,
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
            keyboard = [[InlineKeyboardButton("🔙 Retour Analytics", callback_data='seller_analytics_enhanced')]]
            await bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ Export CSV terminé avec succès !",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Error in analytics_export_csv: {e}", exc_info=True)
            await query.message.reply_text(
                "❌ Erreur lors de l'export CSV.\n\n"
                "Veuillez réessayer dans quelques instants.",
                parse_mode='Markdown'
            )


# ═════════════════════════════════════════════════════════════════
# INSTRUCTIONS D'INTÉGRATION
# ═════════════════════════════════════════════════════════════════

"""
POUR INTÉGRER CES MÉTHODES DANS SELL_HANDLERS.PY :

1. Importer les services au début du fichier :

   from app.services.chart_service import ChartService
   from app.services.export_service import ExportService

2. Dans __init__ de la classe SellHandlers :

   self.chart_service = ChartService()
   self.export_service = ExportService()

3. Copier-coller les 3 méthodes ci-dessus dans la classe SellHandlers :
   - seller_analytics_enhanced
   - analytics_detailed_charts
   - analytics_export_csv

4. Dans le callback_router, ajouter les routes :

   'seller_analytics_enhanced': lambda bot, query: self.sell_handlers.seller_analytics_enhanced(bot, query, lang='fr')
   'analytics_detailed_charts': lambda bot, query: self.sell_handlers.analytics_detailed_charts(bot, query, lang='fr')
   'analytics_export_csv': lambda bot, query: self.sell_handlers.analytics_export_csv(bot, query, lang='fr')

5. Dans le seller_dashboard, modifier le bouton analytics pour pointer vers 'seller_analytics_enhanced'

6. Optionnellement, renommer l'ancienne méthode seller_analytics_visual en seller_analytics_old
"""
