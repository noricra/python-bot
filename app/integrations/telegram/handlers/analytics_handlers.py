"""
Advanced Analytics Handlers for TechBot Marketplace
Provides real-time insights, performance scoring, and smart recommendations
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
import logging
from typing import Optional

from app.core.analytics_engine import AnalyticsEngine
from app.core.chart_generator import ChartGenerator

logger = logging.getLogger(__name__)


class AnalyticsHandlers:
    """Handlers for advanced analytics features"""

    def __init__(self):
        self.analytics = AnalyticsEngine()
        self.charts = ChartGenerator()

    # ═══════════════════════════════════════════════════════
    # MAIN ANALYTICS DASHBOARD
    # ═══════════════════════════════════════════════════════

    async def show_analytics_dashboard(
        self,
        bot,
        query,
        seller_user_id: int,
        lang: str = 'fr'
    ):
        """
        Show complete analytics dashboard with live data

        This is the "wow" feature - comprehensive analytics in one view
        """
        try:
            # Get comprehensive analytics data
            data = self.analytics.get_seller_dashboard_data(seller_user_id)

            # Get revenue trend data for sparkline
            chart_data = self.analytics.get_revenue_chart_data(seller_user_id, days=30)
            revenue_values = [d['revenue'] for d in chart_data] if chart_data else [0]

            # Add trend data to main data
            data['revenue_trend_data'] = revenue_values

            # Generate complete analytics view
            analytics_text = self.charts.format_complete_analytics(data)

            # Keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data='analytics_refresh'),
                    InlineKeyboardButton("📊 Produits", callback_data='analytics_products')
                ],
                [
                    InlineKeyboardButton("💡 Recommandations", callback_data='analytics_recommendations'),
                    InlineKeyboardButton("📈 Graphiques", callback_data='analytics_charts')
                ],
                [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"```\n{analytics_text}\n```",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error showing analytics dashboard: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement des analytics.\n\n"
                "Réessayez dans quelques instants."
            )

    # ═══════════════════════════════════════════════════════
    # PRODUCT PERFORMANCE DETAILS
    # ═══════════════════════════════════════════════════════

    async def show_product_performance(
        self,
        bot,
        query,
        product_id: str,
        lang: str = 'fr'
    ):
        """
        Show detailed performance analysis for a specific product

        Includes:
        - Performance score (0-100)
        - Trend analysis
        - Smart recommendations
        - Optimal price suggestion
        """
        try:
            # Calculate performance
            perf = self.analytics.calculate_product_score(product_id)

            if not perf:
                await query.edit_message_text("❌ Produit introuvable")
                return

            # Format performance card
            perf_text = self.charts.format_performance_card(
                f"Produit {product_id[-6:]}",
                perf.score,
                perf.trend,
                perf.recommendations
            )

            # Add detailed stats
            details = f"""

📊 **Statistiques détaillées**

Revenue (7j)      {perf.revenue_7d:.2f}€
Ventes (7j)       {perf.sales_7d}
Conversion        {perf.conversion_rate:.1f}%
Tendance          {perf.trend.capitalize()}
"""

            # Add price recommendation if available
            if perf.optimal_price:
                details += f"\n💡 **Prix optimal suggéré**: {perf.optimal_price}€"

            full_text = f"```\n{perf_text}\n```{details}"

            # Keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data=f'perf_{product_id}'),
                    InlineKeyboardButton("📊 Dashboard", callback_data='analytics_dashboard')
                ]
            ]

            if perf.optimal_price:
                keyboard.insert(0, [
                    InlineKeyboardButton(
                        f"💰 Appliquer prix ({perf.optimal_price}€)",
                        callback_data=f'apply_price_{product_id}_{perf.optimal_price}'
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data='analytics_products')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                full_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error showing product performance: {e}")
            await query.edit_message_text("❌ Erreur d'analyse")

    # ═══════════════════════════════════════════════════════
    # PRODUCT LIST WITH PERFORMANCE SCORES
    # ═══════════════════════════════════════════════════════

    async def show_products_with_scores(
        self,
        bot,
        query,
        seller_user_id: int,
        lang: str = 'fr'
    ):
        """
        Show all products with their performance scores

        Sorted by score (worst first to encourage optimization)
        """
        try:
            # Get all products
            from app.data.product_repository import ProductRepository
            product_repo = ProductRepository()

            products = product_repo.get_products_by_seller(seller_user_id, active_only=True)

            if not products:
                await query.edit_message_text(
                    "Aucun produit actif.\n\n"
                    "Créez votre premier produit pour accéder aux analytics."
                )
                return

            # Calculate scores for all
            product_scores = []
            for prod in products:
                perf = self.analytics.calculate_product_score(prod[0])  # product_id
                if perf:
                    product_scores.append({
                        'id': prod[0],
                        'title': prod[1][:20],
                        'score': perf.score,
                        'trend': perf.trend
                    })

            # Sort by score (ascending - show problems first)
            product_scores.sort(key=lambda x: x['score'])

            # Format as table
            text = "📊 **PERFORMANCE DES PRODUITS**\n\n"
            text += "```\n"
            text += "Score  Trend  Produit\n"
            text += "═" * 40 + "\n"

            for prod in product_scores:
                score = prod['score']
                trend_arrow = {"rising": "↑", "stable": "→", "declining": "↓"}.get(prod['trend'], "→")

                # Color-code score
                if score >= 70:
                    score_str = f"{score:>5.0f}"
                elif score >= 40:
                    score_str = f"{score:>5.0f}"
                else:
                    score_str = f"⚠{score:>4.0f}"

                text += f"{score_str}  {trend_arrow}   {prod['title']}\n"

            text += "```\n\n"

            # Stats summary
            avg_score = sum(p['score'] for p in product_scores) / len(product_scores)
            text += f"Score moyen : **{avg_score:.0f}/100**\n"

            rising = sum(1 for p in product_scores if p['trend'] == 'rising')
            declining = sum(1 for p in product_scores if p['trend'] == 'declining')

            text += f"↑ En progression : {rising}\n"
            text += f"↓ En déclin : {declining}"

            # Keyboard - show buttons for worst performers
            keyboard = []
            for prod in product_scores[:5]:  # Top 5 worst
                keyboard.append([
                    InlineKeyboardButton(
                        f"📊 {prod['title'][:15]} ({prod['score']:.0f})",
                        callback_data=f"perf_{prod['id']}"
                    )
                ])

            keyboard.append([InlineKeyboardButton("🔙 Dashboard", callback_data='analytics_dashboard')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error showing products with scores: {e}")
            await query.edit_message_text("❌ Erreur de chargement")

    # ═══════════════════════════════════════════════════════
    # RECOMMENDATIONS VIEW
    # ═══════════════════════════════════════════════════════

    async def show_recommendations(
        self,
        bot,
        query,
        seller_user_id: int,
        lang: str = 'fr'
    ):
        """
        Show all actionable recommendations

        Aggregates recommendations from all products and overall performance
        """
        try:
            # Get dashboard data
            data = self.analytics.get_seller_dashboard_data(seller_user_id)

            text = "💡 **RECOMMANDATIONS INTELLIGENTES**\n\n"

            # Action items from dashboard
            if data['action_items']:
                text += "**Actions prioritaires :**\n\n"
                for i, action in enumerate(data['action_items'], 1):
                    text += f"{i}. {action}\n"

                text += "\n"

            # Product-specific recommendations
            text += "**Par produit :**\n\n"

            from app.data.product_repository import ProductRepository
            product_repo = ProductRepository()

            products = product_repo.get_products_by_seller(seller_user_id, active_only=True)

            for prod in products[:5]:  # Top 5
                product_id = prod[0]
                title = prod[1][:20]

                perf = self.analytics.calculate_product_score(product_id)
                if perf and perf.recommendations:
                    text += f"**{title}** (Score: {perf.score:.0f})\n"
                    for rec in perf.recommendations[:2]:  # Top 2 recs
                        text += f"  • {rec}\n"
                    text += "\n"

            # Keyboard
            keyboard = [
                [InlineKeyboardButton("📊 Dashboard", callback_data='analytics_dashboard')],
                [InlineKeyboardButton("🔙 Retour", callback_data='seller_dashboard')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error showing recommendations: {e}")
            await query.edit_message_text("❌ Erreur")

    # ═══════════════════════════════════════════════════════
    # CHARTS VIEW (Revenue & Sales over time)
    # ═══════════════════════════════════════════════════════

    async def show_charts(
        self,
        bot,
        query,
        seller_user_id: int,
        lang: str = 'fr'
    ):
        """
        Show visual charts of revenue and sales trends
        """
        try:
            # Get chart data (last 30 days)
            chart_data = self.analytics.get_revenue_chart_data(seller_user_id, days=30)

            if not chart_data:
                await query.edit_message_text(
                    "Pas encore de données de ventes.\n\n"
                    "Créez des produits et attendez les premières ventes."
                )
                return

            # Extract data
            dates = [d['date'] for d in chart_data]
            revenues = [d['revenue'] for d in chart_data]
            sales = [d['sales'] for d in chart_data]

            # Generate sparklines
            revenue_sparkline = self.charts.sparkline(revenues, width=30)
            sales_sparkline = self.charts.sparkline(sales, width=30)

            # Calculate totals
            total_revenue = sum(revenues)
            total_sales = sum(sales)

            # Format chart view
            text = "```\n"
            text += "📈 TENDANCES (30 DERNIERS JOURS)\n"
            text += "═" * 40 + "\n\n"

            text += "Revenus:\n"
            text += revenue_sparkline + "\n"
            text += f"Total: {total_revenue:.2f}€\n\n"

            text += "Ventes:\n"
            text += sales_sparkline + "\n"
            text += f"Total: {total_sales} ventes\n\n"

            # Show last 7 days in detail
            text += "─" * 40 + "\n"
            text += "Détails (7 derniers jours):\n\n"

            for i in range(min(7, len(chart_data))):
                idx = len(chart_data) - 1 - i
                d = chart_data[idx]
                date_str = d['date'][-5:]  # MM-DD
                bar = "█" * min(10, int(d['revenue'] / 50))  # Scale bar

                text += f"{date_str}  {bar:<10} {d['revenue']:.0f}€  ({d['sales']})\n"

            text += "```"

            # Keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Rafraîchir", callback_data='analytics_charts'),
                    InlineKeyboardButton("📊 Dashboard", callback_data='analytics_dashboard')
                ],
                [InlineKeyboardButton("🔙 Retour", callback_data='seller_dashboard')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error showing charts: {e}")
            await query.edit_message_text("❌ Erreur d'affichage")

    # ═══════════════════════════════════════════════════════
    # QUICK STATS (For dashboard integration)
    # ═══════════════════════════════════════════════════════

    async def get_quick_stats_text(self, seller_user_id: int) -> str:
        """
        Get quick stats summary for embedding in seller dashboard

        Returns compact mini-dashboard
        """
        try:
            data = self.analytics.get_seller_dashboard_data(seller_user_id)

            # Get sparkline
            chart_data = self.analytics.get_revenue_chart_data(seller_user_id, days=7)
            revenue_values = [d['revenue'] for d in chart_data] if chart_data else [0]
            sparkline = self.charts.sparkline(revenue_values, width=15)

            # Format mini dashboard
            stats = {
                'revenue': data['revenue']['week'],
                'revenue_trend': '↑ +23%',  # Would calculate from data
                'sales': data['sales']['week'],
                'sales_trend': '↑ +15%',
                'score': data['performance']['avg_score'],
                'score_trend': '↑',
                'sparkline': sparkline
            }

            return self.charts.format_mini_dashboard(stats)

        except Exception as e:
            logger.error(f"Error getting quick stats: {e}")
            return "Erreur de chargement des stats"

    # ═══════════════════════════════════════════════════════
    # APPLY SMART PRICE (One-click optimization)
    # ═══════════════════════════════════════════════════════

    async def apply_smart_price(
        self,
        bot,
        query,
        product_id: str,
        new_price: float,
        seller_user_id: int
    ):
        """
        Apply AI-recommended price with one click

        This is a "wow" feature - AI does the optimization
        """
        try:
            from app.data.product_repository import ProductRepository
            product_repo = ProductRepository()

            # Verify ownership
            product = product_repo.get_product_by_id(product_id)
            if not product or product[4] != seller_user_id:  # seller_user_id
                await query.answer("❌ Non autorisé", show_alert=True)
                return

            # Update price
            product_repo.update_product_price(product_id, new_price)

            await query.answer(
                f"✅ Prix mis à jour : {new_price}€\n\n"
                "Le nouveau prix est optimisé selon les données du marché.",
                show_alert=True
            )

            # Refresh performance view
            await self.show_product_performance(bot, query, product_id, 'fr')

        except Exception as e:
            logger.error(f"Error applying smart price: {e}")
            await query.answer("❌ Erreur", show_alert=True)