"""
Real-time Analytics Engine for TechBot Marketplace
Generates live insights, performance scores, and smart recommendations
"""

import sqlite3
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json


@dataclass
class ProductPerformance:
    """Product performance metrics"""
    product_id: str
    score: float  # 0-100
    trend: str  # "rising" | "stable" | "declining"
    revenue_7d: float
    sales_7d: int
    conversion_rate: float
    recommendations: List[str]
    optimal_price: Optional[float] = None


@dataclass
class MarketInsights:
    """Market-wide insights"""
    total_revenue_24h: float
    total_sales_24h: int
    avg_product_price: float
    top_category: str
    growth_rate: float  # % vs previous period


class AnalyticsEngine:
    """Advanced analytics engine with AI-powered insights"""

    def __init__(self, db_path: str = "marketplace_database.db"):
        self.db_path = db_path

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    # ═══════════════════════════════════════════════════════
    # PRODUCT PERFORMANCE SCORING
    # ═══════════════════════════════════════════════════════

    def calculate_product_score(self, product_id: str) -> ProductPerformance:
        """
        Calculate comprehensive performance score (0-100)

        Factors:
        - Sales velocity (30%)
        - Revenue trend (25%)
        - View-to-purchase conversion (20%)
        - Rating (15%)
        - Recency (10%)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get product data
            cursor.execute("""
                SELECT
                    p.product_id,
                    p.title,
                    p.price_eur,
                    p.views_count,
                    p.sales_count,
                    p.created_at,
                    COALESCE(AVG(r.rating), 0) as avg_rating
                FROM products p
                LEFT JOIN reviews r ON p.product_id = r.product_id
                WHERE p.product_id = ?
                GROUP BY p.product_id
            """, (product_id,))

            product = cursor.fetchone()
            if not product:
                return None

            product_id, title, price, views, total_sales, created_at, avg_rating = product

            # Sales last 7 days
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(product_price_eur), 0)
                FROM orders
                WHERE product_id = ?
                AND payment_status = 'completed'
                AND completed_at >= datetime('now', '-7 days')
            """, (product_id,))

            sales_7d, revenue_7d = cursor.fetchone()

            # Sales 7-14 days ago (for trend)
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(product_price_eur), 0)
                FROM orders
                WHERE product_id = ?
                AND payment_status = 'completed'
                AND completed_at BETWEEN datetime('now', '-14 days') AND datetime('now', '-7 days')
            """, (product_id,))

            sales_prev_7d, revenue_prev_7d = cursor.fetchone()

            # Calculate score components

            # 1. Sales velocity (30 points) - normalized to 7-day window
            sales_velocity_score = min(30, (sales_7d / 7) * 10)  # 3 sales/day = 30 points

            # 2. Revenue trend (25 points)
            if revenue_prev_7d > 0:
                revenue_growth = ((revenue_7d - revenue_prev_7d) / revenue_prev_7d) * 100
                revenue_trend_score = min(25, max(0, 12.5 + (revenue_growth / 4)))  # +50% = 25 points
            else:
                revenue_trend_score = 12.5 if revenue_7d > 0 else 0

            # 3. Conversion rate (20 points)
            conversion_rate = (total_sales / views * 100) if views > 0 else 0
            conversion_score = min(20, conversion_rate * 4)  # 5% = 20 points

            # 4. Rating (15 points)
            rating_score = (avg_rating / 5) * 15

            # 5. Recency (10 points) - newer products get boost
            days_old = (datetime.now() - datetime.fromisoformat(created_at)).days
            recency_score = max(0, 10 - (days_old / 30))  # Full points first 30 days

            # Total score
            total_score = (
                sales_velocity_score +
                revenue_trend_score +
                conversion_score +
                rating_score +
                recency_score
            )

            # Determine trend
            if sales_7d > sales_prev_7d * 1.2:
                trend = "rising"
            elif sales_7d < sales_prev_7d * 0.8:
                trend = "declining"
            else:
                trend = "stable"

            # Generate recommendations
            recommendations = self._generate_recommendations(
                total_score,
                conversion_rate,
                avg_rating,
                price,
                sales_7d
            )

            # Calculate optimal price
            optimal_price = self._calculate_optimal_price(product_id, price, sales_7d, conversion_rate)

            return ProductPerformance(
                product_id=product_id,
                score=round(total_score, 1),
                trend=trend,
                revenue_7d=revenue_7d,
                sales_7d=sales_7d,
                conversion_rate=conversion_rate,
                recommendations=recommendations,
                optimal_price=optimal_price
            )

        finally:
            conn.close()

    def _generate_recommendations(
        self,
        score: float,
        conversion: float,
        rating: float,
        price: float,
        sales_7d: int
    ) -> List[str]:
        """Generate actionable recommendations"""
        recs = []

        if score < 30:
            recs.append("⚠ Performance critique : révision complète nécessaire")

        if conversion < 2:
            recs.append("↑ Conversion faible : améliorez la description et les visuels")

        if rating < 3.5 and rating > 0:
            recs.append("★ Note insuffisante : contactez les acheteurs pour améliorer")

        if sales_7d == 0:
            recs.append("📉 Aucune vente : baisse de prix ou promotion recommandée")
        elif sales_7d > 20:
            recs.append("🚀 Forte demande : augmentation de prix possible")

        if price < 10:
            recs.append("💰 Prix très bas : valorisez votre expertise")
        elif price > 200:
            recs.append("💰 Prix premium : assurez une qualité exceptionnelle")

        if not recs:
            recs.append("✓ Performance optimale : continuez ainsi")

        return recs

    def _calculate_optimal_price(
        self,
        product_id: str,
        current_price: float,
        sales_7d: int,
        conversion: float
    ) -> Optional[float]:
        """
        AI-powered price optimization

        Uses market data and product performance to suggest optimal price
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get category average
            cursor.execute("""
                SELECT AVG(p.price_eur), AVG(p.sales_count)
                FROM products p
                JOIN (
                    SELECT category FROM products WHERE product_id = ?
                ) cat ON p.category = cat.category
                WHERE p.status = 'active'
            """, (product_id,))

            avg_price, avg_sales = cursor.fetchone()

            if not avg_price:
                return None

            # Price optimization logic
            if sales_7d > avg_sales * 1.5:
                # High demand: can increase price
                optimal = current_price * 1.15
            elif sales_7d < avg_sales * 0.5 and conversion < 2:
                # Low demand: decrease price
                optimal = current_price * 0.85
            elif current_price < avg_price * 0.7:
                # Underpriced vs market
                optimal = avg_price * 0.9
            elif current_price > avg_price * 1.5 and sales_7d < 3:
                # Overpriced with low sales
                optimal = avg_price * 1.2
            else:
                # Price is optimal
                return None

            return round(optimal, 2)

        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════
    # MARKET INSIGHTS
    # ═══════════════════════════════════════════════════════

    def get_market_insights(self) -> MarketInsights:
        """Get real-time market insights"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Revenue & sales last 24h
            cursor.execute("""
                SELECT
                    COUNT(*),
                    COALESCE(SUM(product_price_eur), 0)
                FROM orders
                WHERE payment_status = 'completed'
                AND completed_at >= datetime('now', '-24 hours')
            """)

            sales_24h, revenue_24h = cursor.fetchone()

            # Previous 24h (for growth rate)
            cursor.execute("""
                SELECT COALESCE(SUM(product_price_eur), 0)
                FROM orders
                WHERE payment_status = 'completed'
                AND completed_at BETWEEN datetime('now', '-48 hours') AND datetime('now', '-24 hours')
            """)

            revenue_prev_24h = cursor.fetchone()[0]

            # Growth rate
            if revenue_prev_24h > 0:
                growth_rate = ((revenue_24h - revenue_prev_24h) / revenue_prev_24h) * 100
            else:
                growth_rate = 0.0

            # Average product price
            cursor.execute("""
                SELECT AVG(price_eur)
                FROM products
                WHERE status = 'active'
            """)

            avg_price = cursor.fetchone()[0] or 0

            # Top category
            cursor.execute("""
                SELECT p.category, COUNT(*) as sales
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.payment_status = 'completed'
                AND o.completed_at >= datetime('now', '-7 days')
                GROUP BY p.category
                ORDER BY sales DESC
                LIMIT 1
            """)

            top_cat_row = cursor.fetchone()
            top_category = top_cat_row[0] if top_cat_row else "N/A"

            return MarketInsights(
                total_revenue_24h=revenue_24h,
                total_sales_24h=sales_24h,
                avg_product_price=avg_price,
                top_category=top_category,
                growth_rate=growth_rate
            )

        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════
    # SELLER ANALYTICS
    # ═══════════════════════════════════════════════════════

    def get_seller_dashboard_data(self, seller_user_id: int) -> Dict:
        """
        Get comprehensive seller analytics

        Returns:
        - Revenue breakdown (today, week, month, all-time)
        - Top products
        - Performance trends
        - Action items
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Revenue by timeframe
            timeframes = {
                'today': "datetime('now', 'start of day')",
                'week': "datetime('now', '-7 days')",
                'month': "datetime('now', '-30 days')"
            }

            revenue_data = {}
            sales_data = {}

            for period, sql_time in timeframes.items():
                cursor.execute(f"""
                    SELECT
                        COUNT(*),
                        COALESCE(SUM(product_price_eur), 0)
                    FROM orders
                    WHERE seller_user_id = ?
                    AND payment_status = 'completed'
                    AND completed_at >= {sql_time}
                """, (seller_user_id,))

                count, revenue = cursor.fetchone()
                sales_data[period] = count
                revenue_data[period] = revenue

            # All-time
            cursor.execute("""
                SELECT
                    COUNT(*),
                    COALESCE(SUM(product_price_eur), 0)
                FROM orders
                WHERE seller_user_id = ?
                AND payment_status = 'completed'
            """, (seller_user_id,))

            total_sales, total_revenue = cursor.fetchone()

            # Top 3 products
            cursor.execute("""
                SELECT
                    p.product_id,
                    p.title,
                    COUNT(*) as sales,
                    SUM(o.product_price_eur) as revenue
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.seller_user_id = ?
                AND o.payment_status = 'completed'
                GROUP BY p.product_id
                ORDER BY revenue DESC
                LIMIT 3
            """, (seller_user_id,))

            top_products = [
                {
                    'id': row[0],
                    'title': row[1],
                    'sales': row[2],
                    'revenue': row[3]
                }
                for row in cursor.fetchall()
            ]

            # Performance scores for all products
            cursor.execute("""
                SELECT product_id
                FROM products
                WHERE seller_user_id = ?
                AND status = 'active'
            """, (seller_user_id,))

            product_ids = [row[0] for row in cursor.fetchall()]

            product_scores = []
            for pid in product_ids:
                perf = self.calculate_product_score(pid)
                if perf:
                    product_scores.append({
                        'id': pid,
                        'score': perf.score,
                        'trend': perf.trend
                    })

            # Calculate average score
            avg_score = sum(p['score'] for p in product_scores) / len(product_scores) if product_scores else 0

            # Generate action items
            action_items = []

            if avg_score < 40:
                action_items.append("⚠ Score moyen faible : optimisez vos produits")

            if sales_data['week'] == 0:
                action_items.append("📉 Aucune vente cette semaine : action requise")

            if len(top_products) < 3:
                action_items.append("➕ Ajoutez plus de produits pour augmenter vos revenus")

            declining_products = [p for p in product_scores if p['trend'] == 'declining']
            if declining_products:
                action_items.append(f"📊 {len(declining_products)} produit(s) en déclin")

            if not action_items:
                action_items.append("✓ Tout va bien, continuez !")

            return {
                'revenue': {
                    'today': revenue_data['today'],
                    'week': revenue_data['week'],
                    'month': revenue_data['month'],
                    'total': total_revenue
                },
                'sales': {
                    'today': sales_data['today'],
                    'week': sales_data['week'],
                    'month': sales_data['month'],
                    'total': total_sales
                },
                'top_products': top_products,
                'performance': {
                    'avg_score': round(avg_score, 1),
                    'products': product_scores
                },
                'action_items': action_items
            }

        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════
    # LIVE CHART DATA
    # ═══════════════════════════════════════════════════════

    def get_revenue_chart_data(self, seller_user_id: int, days: int = 30) -> List[Dict]:
        """
        Get daily revenue data for charts

        Returns list of {date, revenue, sales} for last N days
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    DATE(completed_at) as date,
                    COUNT(*) as sales,
                    COALESCE(SUM(product_price_eur), 0) as revenue
                FROM orders
                WHERE seller_user_id = ?
                AND payment_status = 'completed'
                AND completed_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(completed_at)
                ORDER BY date ASC
            """, (seller_user_id, days))

            data = [
                {
                    'date': row[0],
                    'sales': row[1],
                    'revenue': row[2]
                }
                for row in cursor.fetchall()
            ]

            return data

        finally:
            conn.close()

    def get_category_distribution(self, seller_user_id: int) -> List[Dict]:
        """Get sales distribution by category for pie charts"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    p.category,
                    COUNT(*) as sales,
                    SUM(o.product_price_eur) as revenue
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.seller_user_id = ?
                AND o.payment_status = 'completed'
                GROUP BY p.category
                ORDER BY revenue DESC
            """, (seller_user_id,))

            return [
                {
                    'category': row[0],
                    'sales': row[1],
                    'revenue': row[2]
                }
                for row in cursor.fetchall()
            ]

        finally:
            conn.close()