#!/usr/bin/env python3
"""
Quick demo of the spectacular analytics features
Run this to see the AI-powered insights in action
"""

from app.core.analytics_engine import AnalyticsEngine
from app.core.chart_generator import ChartGenerator
import sqlite3


def demo_analytics():
    """Demonstrate analytics capabilities"""
    print("=" * 60)
    print("🚀 TECH BOT MARKETPLACE - ANALYTICS DEMO")
    print("=" * 60)
    print()

    # Initialize
    engine = AnalyticsEngine()
    charts = ChartGenerator()

    # Get a real product from database
    conn = sqlite3.connect("marketplace_database.db")
    cursor = conn.cursor()

    # Find a product with some data
    cursor.execute("""
        SELECT p.product_id, p.title, p.seller_user_id
        FROM products p
        WHERE p.status = 'active'
        LIMIT 1
    """)

    product_row = cursor.fetchone()

    if not product_row:
        print("❌ No active products found in database")
        print("Create a product first to test analytics")
        return

    product_id, product_title, seller_id = product_row

    print(f"📊 Analyzing Product: {product_title}")
    print(f"    ID: {product_id}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 1: Product Performance Score
    # ═══════════════════════════════════════════════════════════════

    print("─" * 60)
    print("TEST 1: PRODUCT PERFORMANCE SCORE (AI-POWERED)")
    print("─" * 60)

    perf = engine.calculate_product_score(product_id)

    if perf:
        # Show performance card
        card = charts.format_performance_card(
            f"Product {product_id[-6:]}",
            perf.score,
            perf.trend,
            perf.recommendations
        )

        print(card)
        print()

        # Show details
        print("📈 Detailed Metrics:")
        print(f"   Revenue (7d):     {perf.revenue_7d:.2f}€")
        print(f"   Sales (7d):       {perf.sales_7d}")
        print(f"   Conversion:       {perf.conversion_rate:.2f}%")
        print(f"   Trend:            {perf.trend.capitalize()}")

        if perf.optimal_price:
            print(f"   💡 Optimal Price: {perf.optimal_price}€")
            print()
            print(f"   ✨ AI Recommendation: Change price to {perf.optimal_price}€")
            print(f"      for optimal revenue")
        else:
            print("   ✓ Current price is optimal")

        print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 2: Seller Dashboard Analytics
    # ═══════════════════════════════════════════════════════════════

    print("─" * 60)
    print("TEST 2: SELLER DASHBOARD ANALYTICS")
    print("─" * 60)

    dashboard_data = engine.get_seller_dashboard_data(seller_id)

    # Show revenue stats
    print()
    print("💰 Revenue Breakdown:")
    print(f"   Today:    {dashboard_data['revenue']['today']:.2f}€")
    print(f"   Week:     {dashboard_data['revenue']['week']:.2f}€")
    print(f"   Month:    {dashboard_data['revenue']['month']:.2f}€")
    print(f"   Total:    {dashboard_data['revenue']['total']:.2f}€")
    print()

    # Show sales stats
    print("🛒 Sales Breakdown:")
    print(f"   Today:    {dashboard_data['sales']['today']}")
    print(f"   Week:     {dashboard_data['sales']['week']}")
    print(f"   Month:    {dashboard_data['sales']['month']}")
    print(f"   Total:    {dashboard_data['sales']['total']}")
    print()

    # Show top products
    if dashboard_data['top_products']:
        print("🏆 Top Products:")
        for i, prod in enumerate(dashboard_data['top_products'][:3], 1):
            print(f"   {i}. {prod['title'][:30]:<30} {prod['sales']:>3} sales  {prod['revenue']:>7.2f}€")
        print()

    # Show performance
    if dashboard_data['performance']['products']:
        print("📊 Performance Overview:")
        print(f"   Average Score: {dashboard_data['performance']['avg_score']:.1f}/100")
        print()

    # Show action items
    print("⚡ AI Recommendations:")
    for action in dashboard_data['action_items']:
        print(f"   • {action}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 3: Visual Charts
    # ═══════════════════════════════════════════════════════════════

    print("─" * 60)
    print("TEST 3: VISUAL ASCII CHARTS")
    print("─" * 60)
    print()

    # Get chart data
    chart_data = engine.get_revenue_chart_data(seller_id, days=30)

    if chart_data:
        # Extract revenue values
        revenue_values = [d['revenue'] for d in chart_data]

        # Generate sparkline
        sparkline = charts.sparkline(revenue_values, width=25)

        print("📈 Revenue Trend (30 days):")
        print(f"   {sparkline}")
        print()

        # Show trend arrow
        if len(revenue_values) >= 2:
            arrow = charts.trend_arrow(revenue_values[-1], revenue_values[0])
            print(f"   Trend: {arrow}")
        print()

        # Show bar chart for last 7 days
        if len(chart_data) >= 7:
            print("📊 Last 7 Days Detail:")
            last_7 = chart_data[-7:]
            bar_data = [(d['date'][-5:], d['revenue']) for d in last_7]

            bar_chart = charts.horizontal_bar_chart(bar_data, max_width=15, show_values=True)
            print(bar_chart)
            print()

    # ═══════════════════════════════════════════════════════════════
    # TEST 4: Market Insights
    # ═══════════════════════════════════════════════════════════════

    print("─" * 60)
    print("TEST 4: MARKET INSIGHTS")
    print("─" * 60)
    print()

    market = engine.get_market_insights()

    print("🌐 Marketplace Overview:")
    print(f"   Revenue (24h):    {market.total_revenue_24h:.2f}€")
    print(f"   Sales (24h):      {market.total_sales_24h}")
    print(f"   Avg Product Price: {market.avg_product_price:.2f}€")
    print(f"   Top Category:     {market.top_category}")
    print(f"   Growth Rate:      {market.growth_rate:+.1f}%")
    print()

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════

    print("=" * 60)
    print("✅ ANALYTICS DEMO COMPLETE")
    print("=" * 60)
    print()
    print("🎯 What you just saw:")
    print()
    print("   ✓ AI-powered performance scoring (0-100)")
    print("   ✓ Smart price recommendations")
    print("   ✓ Trend analysis (rising/stable/declining)")
    print("   ✓ Actionable recommendations")
    print("   ✓ Beautiful ASCII charts")
    print("   ✓ Sparklines & trend arrows")
    print("   ✓ Market insights")
    print()
    print("🚀 This is the 'wow' factor.")
    print()
    print("To see this in Telegram:")
    print("   1. Start the bot: python3 bot_mlt.py")
    print("   2. Login as seller")
    print("   3. Click: 📊 Analytics Pro ▸")
    print()

    conn.close()


if __name__ == "__main__":
    try:
        demo_analytics()
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure:")
        print("  1. Database exists (marketplace_database.db)")
        print("  2. At least one active product exists")
        print("  3. You're in the project root directory")