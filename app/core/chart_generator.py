"""
Visual Chart Generator for Telegram
Creates beautiful ASCII and image charts for analytics
"""

from typing import List, Dict, Tuple
from datetime import datetime
import io


class ChartGenerator:
    """Generate beautiful visual charts for Telegram"""

    # ═══════════════════════════════════════════════════════
    # ASCII MINI CHARTS (Sparklines)
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def sparkline(values: List[float], width: int = 20) -> str:
        """
        Generate sparkline chart (mini inline chart)

        Examples:
        [1,2,3,4,5] -> "▁▂▃▅█"
        [5,4,3,2,1] -> "█▅▃▂▁"
        """
        if not values or all(v == 0 for v in values):
            return "▁" * width

        # Normalize values to 0-8 range
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val

        if range_val == 0:
            return "▄" * width

        blocks = " ▁▂▃▄▅▆▇█"

        # Sample values if too many
        if len(values) > width:
            step = len(values) / width
            sampled = [values[int(i * step)] for i in range(width)]
        else:
            sampled = values

        chart = ""
        for val in sampled:
            normalized = (val - min_val) / range_val
            block_index = int(normalized * 8)
            chart += blocks[min(block_index, 8)]

        return chart

    @staticmethod
    def trend_arrow(current: float, previous: float) -> str:
        """
        Get trend arrow with percentage

        Returns: "↑ +15%" or "↓ -8%" or "→ 0%"
        """
        if previous == 0:
            return "→ N/A"

        change = ((current - previous) / previous) * 100

        if change > 5:
            return f"↑ +{change:.0f}%"
        elif change < -5:
            return f"↓ {change:.0f}%"
        else:
            return f"→ {change:.0f}%"

    # ═══════════════════════════════════════════════════════
    # BAR CHARTS (ASCII)
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def horizontal_bar_chart(
        data: List[Tuple[str, float]],
        max_width: int = 20,
        show_values: bool = True
    ) -> str:
        """
        Generate horizontal bar chart

        Example:
        Product A  ████████████ 120
        Product B  ████████ 80
        Product C  ████ 40
        """
        if not data:
            return "No data"

        max_value = max(v for _, v in data)
        if max_value == 0:
            max_value = 1

        chart = ""
        for label, value in data:
            # Calculate bar length
            bar_length = int((value / max_value) * max_width)

            # Create bar
            bar = "█" * bar_length

            # Format value
            if value >= 1000:
                value_str = f"{value/1000:.1f}k"
            else:
                value_str = f"{value:.0f}"

            # Add line
            if show_values:
                chart += f"{label:<15} {bar:<{max_width}} {value_str}\n"
            else:
                chart += f"{label:<15} {bar}\n"

        return chart.rstrip()

    @staticmethod
    def vertical_bar_chart(
        data: List[Tuple[str, float]],
        height: int = 10
    ) -> str:
        """
        Generate vertical bar chart (better for time series)

        Example:
            █
            █
          █ █
        █ █ █ █
        M T W T F
        """
        if not data:
            return "No data"

        max_value = max(v for _, v in data)
        if max_value == 0:
            max_value = 1

        # Create chart rows from top to bottom
        chart_lines = []

        for level in range(height, 0, -1):
            threshold = (level / height) * max_value
            line = ""
            for label, value in data:
                if value >= threshold:
                    line += "█ "
                else:
                    line += "  "
            chart_lines.append(line)

        # Add labels
        labels_line = "".join(f"{label[0]} " for label, _ in data)
        chart_lines.append(labels_line)

        return "\n".join(chart_lines)

    # ═══════════════════════════════════════════════════════
    # PERFORMANCE DASHBOARD
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def format_performance_card(
        title: str,
        score: float,
        trend: str,
        recommendations: List[str]
    ) -> str:
        """
        Format beautiful performance card

        ╔══════════════════════════════╗
        ║  Product Performance         ║
        ║                              ║
        ║  Score: 87/100   ↑ Rising    ║
        ║  ████████████████░░░         ║
        ║                              ║
        ║  Recommendations:            ║
        ║  • Great performance         ║
        ╚══════════════════════════════╝
        """

        # Score bar
        bar_width = 20
        filled = int((score / 100) * bar_width)
        empty = bar_width - filled
        score_bar = "█" * filled + "░" * empty

        # Trend emoji
        trend_emoji = {
            "rising": "↑",
            "stable": "→",
            "declining": "↓"
        }.get(trend, "→")

        # Color-coded score
        if score >= 70:
            score_label = f"Score: {score:.0f}/100"
        elif score >= 40:
            score_label = f"Score: {score:.0f}/100"
        else:
            score_label = f"⚠ Score: {score:.0f}/100"

        # Format recommendations (max 3)
        rec_lines = "\n".join(f"  • {rec}" for rec in recommendations[:3])

        card = f"""╔══════════════════════════════╗
║  {title:<28}║
║                              ║
║  {score_label:<17} {trend_emoji} {trend.capitalize():<8}║
║  {score_bar}         ║
║                              ║
║  Recommandations:            ║
{rec_lines}
╚══════════════════════════════╝"""

        return card

    @staticmethod
    def format_revenue_dashboard(
        today: float,
        week: float,
        month: float,
        total: float,
        trend_data: List[float]
    ) -> str:
        """
        Format beautiful revenue dashboard

        ╔══════════════════════════════════════╗
        ║  Revenus                             ║
        ║                                      ║
        ║  Aujourd'hui     125€   ↑ +15%      ║
        ║  7 derniers j.   890€   ↑ +23%      ║
        ║  30 derniers j. 3.2k€   → +2%       ║
        ║  Total          12.5k€              ║
        ║                                      ║
        ║  Tendance (30j): ▁▂▃▅▅▇█▇▅▃▂▁      ║
        ╚══════════════════════════════════════╗
        """

        # Format currency
        def fmt(val):
            if val >= 1000:
                return f"{val/1000:.1f}k€"
            else:
                return f"{val:.0f}€"

        # Generate sparkline
        sparkline = ChartGenerator.sparkline(trend_data, 15)

        # Calculate trends (mock for now, would need historical data)
        today_trend = "↑ +15%" if today > 0 else "→ 0%"
        week_trend = "↑ +23%" if week > 0 else "→ 0%"
        month_trend = "→ +2%" if month > 0 else "→ 0%"

        card = f"""╔══════════════════════════════════════╗
║  Revenus                             ║
║                                      ║
║  Aujourd'hui     {fmt(today):<8} {today_trend:<8}║
║  7 derniers j.   {fmt(week):<8} {week_trend:<8}║
║  30 derniers j.  {fmt(month):<8} {month_trend:<8}║
║  Total           {fmt(total):<8}          ║
║                                      ║
║  Tendance (30j): {sparkline}      ║
╚══════════════════════════════════════╝"""

        return card

    @staticmethod
    def format_sales_dashboard(
        today: int,
        week: int,
        month: int,
        total: int,
        top_products: List[Dict]
    ) -> str:
        """
        Format sales dashboard with top products

        ╔════════════════════════════════════════╗
        ║  Ventes                                ║
        ║                                        ║
        ║  Aujourd'hui      5 ventes             ║
        ║  7 derniers j.   23 ventes             ║
        ║  30 derniers j.  87 ventes             ║
        ║  Total          245 ventes             ║
        ║                                        ║
        ║  Top produits:                         ║
        ║  Python Pro    ████████████ 45  (2.1k)║
        ║  Trading Bot   ████████ 32  (1.6k)    ║
        ║  Web Scraping  ████ 18  (890€)        ║
        ╚════════════════════════════════════════╝
        """

        # Format top products bar chart
        if top_products:
            max_sales = max(p['sales'] for p in top_products)
            product_lines = []

            for prod in top_products[:3]:
                title = prod['title'][:14]
                sales = prod['sales']
                revenue = prod['revenue']

                # Bar
                bar_width = 12
                bar_length = int((sales / max_sales) * bar_width) if max_sales > 0 else 0
                bar = "█" * bar_length

                # Format revenue
                if revenue >= 1000:
                    rev_str = f"{revenue/1000:.1f}k€"
                else:
                    rev_str = f"{revenue:.0f}€"

                line = f"║  {title:<14} {bar:<{bar_width}} {sales:<3} ({rev_str})║"
                product_lines.append(line)

            products_section = "\n".join(product_lines)
        else:
            products_section = "║  Aucune vente                          ║"

        card = f"""╔════════════════════════════════════════╗
║  Ventes                                ║
║                                        ║
║  Aujourd'hui      {today:<3} ventes             ║
║  7 derniers j.   {week:<3} ventes             ║
║  30 derniers j.  {month:<3} ventes             ║
║  Total          {total:<4} ventes      ║
║                                        ║
║  Top produits:                         ║
{products_section}
╚════════════════════════════════════════╝"""

        return card

    # ═══════════════════════════════════════════════════════
    # QUICK STATS (One-liners)
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def format_quick_stat(label: str, value: str, trend: str = None) -> str:
        """
        Format single stat line

        Examples:
        "Revenue Today    125€  ↑ +15%"
        "Active Products   12"
        """
        if trend:
            return f"{label:<20} {value:<10} {trend}"
        else:
            return f"{label:<20} {value}"

    @staticmethod
    def format_mini_dashboard(stats: Dict) -> str:
        """
        Ultra-compact dashboard for quick view

        ▸ Revenus: 890€ (7j)  ↑ +23%
        ▸ Ventes: 23  ↑ +15%
        ▸ Score: 87/100  ↑ Rising
        ▸ Tendance: ▁▂▃▅▇█▇▅
        """

        lines = []

        if 'revenue' in stats:
            lines.append(f"▸ Revenus: {stats['revenue']}€ (7j)  {stats.get('revenue_trend', '→')}")

        if 'sales' in stats:
            lines.append(f"▸ Ventes: {stats['sales']}  {stats.get('sales_trend', '→')}")

        if 'score' in stats:
            lines.append(f"▸ Score: {stats['score']:.0f}/100  {stats.get('score_trend', '→')}")

        if 'sparkline' in stats:
            lines.append(f"▸ Tendance: {stats['sparkline']}")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    # COMPLETE ANALYTICS PAGE
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def format_complete_analytics(data: Dict) -> str:
        """
        Generate complete analytics view

        Combines multiple charts into one beautiful view
        """

        sections = []

        # Header
        sections.append("📊 ANALYTICS DASHBOARD")
        sections.append("═" * 40)
        sections.append("")

        # Revenue section
        if 'revenue' in data:
            rev_data = data['revenue']
            trend_data = data.get('revenue_trend_data', [0])
            revenue_card = ChartGenerator.format_revenue_dashboard(
                rev_data.get('today', 0),
                rev_data.get('week', 0),
                rev_data.get('month', 0),
                rev_data.get('total', 0),
                trend_data
            )
            sections.append(revenue_card)
            sections.append("")

        # Sales section
        if 'sales' in data and 'top_products' in data:
            sales_data = data['sales']
            sales_card = ChartGenerator.format_sales_dashboard(
                sales_data.get('today', 0),
                sales_data.get('week', 0),
                sales_data.get('month', 0),
                sales_data.get('total', 0),
                data['top_products']
            )
            sections.append(sales_card)
            sections.append("")

        # Performance section
        if 'performance' in data:
            perf_data = data['performance']
            avg_score = perf_data.get('avg_score', 0)

            # Show individual product scores
            sections.append("╔════════════════════════════════════════╗")
            sections.append("║  Performance des produits              ║")
            sections.append("║                                        ║")

            products = perf_data.get('products', [])
            for prod in products[:5]:  # Max 5
                prod_id = prod['id'][-6:]  # Last 6 chars
                score = prod['score']
                trend_arrow = {"rising": "↑", "stable": "→", "declining": "↓"}.get(prod['trend'], "→")

                # Score bar
                bar_length = int(score / 5)  # 0-20 chars
                bar = "█" * bar_length + "░" * (20 - bar_length)

                line = f"║  {prod_id}  {bar}  {score:.0f} {trend_arrow}   ║"
                sections.append(line)

            sections.append("╚════════════════════════════════════════╝")
            sections.append("")

        # Action items
        if 'action_items' in data:
            sections.append("⚡ ACTIONS RECOMMANDÉES")
            sections.append("─" * 40)
            for action in data['action_items'][:3]:
                sections.append(f"  {action}")
            sections.append("")

        return "\n".join(sections)


# ═══════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════

def format_number(num: float) -> str:
    """Format number with K/M suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{num:.0f}"


def format_currency(amount: float) -> str:
    """Format currency with € symbol"""
    if amount >= 1000:
        return f"{amount/1000:.1f}k€"
    else:
        return f"{amount:.2f}€"


def format_percentage(value: float) -> str:
    """Format percentage with + or - sign"""
    if value > 0:
        return f"+{value:.1f}%"
    else:
        return f"{value:.1f}%"


# ═══════════════════════════════════════════════════════
# MATPLOTLIB IMAGE CHARTS (Real Graphics)
# ═══════════════════════════════════════════════════════

try:
    import matplotlib
    matplotlib.use('Agg')  # Backend non-GUI pour serveur
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from collections import defaultdict
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib not available - image charts disabled")


# Couleurs Ferus (de la landing page)
CHART_COLORS = {
    'bg_primary': '#0a0f1b',      # Fond sombre
    'bg_secondary': '#0f172a',
    'primary': '#5eead4',          # Teal/Turquoise
    'accent': '#a78bfa',           # Purple
    'success': '#10b981',          # Green
    'warning': '#f59e0b',          # Orange
    'text_primary': '#f1f5f9',     # Blanc cassé
    'text_secondary': '#94a3b8',   # Gris
    'border': '#1e293b'
}


def setup_chart_theme():
    """Configure le thème sombre Ferus pour matplotlib"""
    if not MATPLOTLIB_AVAILABLE:
        return

    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': CHART_COLORS['bg_primary'],
        'axes.facecolor': CHART_COLORS['bg_secondary'],
        'axes.edgecolor': CHART_COLORS['border'],
        'axes.labelcolor': CHART_COLORS['text_primary'],
        'text.color': CHART_COLORS['text_primary'],
        'xtick.color': CHART_COLORS['text_secondary'],
        'ytick.color': CHART_COLORS['text_secondary'],
        'grid.color': CHART_COLORS['border'],
        'grid.alpha': 0.3,
        'font.family': 'sans-serif',
        'font.size': 11
    })


def generate_revenue_chart(sales_data: List[Dict], days: int = 7) -> io.BytesIO:
    """
    Génère un graphique matplotlib des revenus sur N jours

    Args:
        sales_data: Liste de {'date': datetime, 'revenue': float}
        days: Nombre de jours à afficher

    Returns:
        BytesIO contenant l'image PNG
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required for image charts")

    setup_chart_theme()
    from datetime import timedelta

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)

    # Préparer les données - regrouper par jour
    revenue_by_day = defaultdict(float)
    today = datetime.now().date()

    # Initialiser tous les jours avec 0
    for i in range(days):
        date = today - timedelta(days=i)
        revenue_by_day[date] = 0.0

    # Remplir avec les vraies données
    for sale in sales_data:
        sale_date = sale.get('date')
        if isinstance(sale_date, str):
            sale_date = datetime.fromisoformat(sale_date).date()
        elif hasattr(sale_date, 'date'):
            sale_date = sale_date.date()

        if sale_date in revenue_by_day:
            revenue_by_day[sale_date] += float(sale.get('revenue', 0))

    # Trier et extraire
    sorted_dates = sorted(revenue_by_day.keys())
    revenues = [revenue_by_day[d] for d in sorted_dates]

    # Tracer ligne + area fill
    ax.plot(sorted_dates, revenues,
            color=CHART_COLORS['primary'],
            linewidth=3,
            marker='o',
            markersize=6,
            markerfacecolor=CHART_COLORS['primary'],
            markeredgewidth=0)

    ax.fill_between(sorted_dates, revenues,
                    alpha=0.3,
                    color=CHART_COLORS['primary'])

    # Configurer axes
    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel('Revenus (€)', fontsize=12, fontweight='bold')
    ax.set_title(f'📈 Revenus des {days} derniers jours',
                fontsize=16,
                fontweight='bold',
                color=CHART_COLORS['primary'],
                pad=20)

    # Format dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 7)))
    plt.xticks(rotation=45, ha='right')

    # Grille
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.set_axisbelow(True)

    # Statistiques
    total_revenue = sum(revenues)
    avg_revenue = total_revenue / len(revenues) if revenues else 0

    stats_text = f'Total: {total_revenue:.2f}€\nMoyenne: {avg_revenue:.2f}€/jour'
    ax.text(0.02, 0.98, stats_text,
           transform=ax.transAxes,
           fontsize=11,
           verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor=CHART_COLORS['bg_primary'], alpha=0.8),
           color=CHART_COLORS['text_primary'])

    plt.tight_layout()

    # Sauvegarder en mémoire
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_products_chart(product_sales: List[Dict], top_n: int = 5) -> io.BytesIO:
    """
    Génère un graphique bar chart horizontal des ventes par produit

    Args:
        product_sales: Liste de {'product_name': str, 'sales_count': int, 'revenue': float}
        top_n: Nombre de produits à afficher

    Returns:
        BytesIO contenant l'image PNG
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required for image charts")

    setup_chart_theme()

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)

    # Trier par revenue et prendre top N
    sorted_products = sorted(product_sales,
                            key=lambda x: x.get('revenue', 0),
                            reverse=True)[:top_n]

    if not sorted_products:
        # Pas de données
        ax.text(0.5, 0.5, 'Aucune vente pour le moment',
               ha='center', va='center',
               fontsize=18, color=CHART_COLORS['text_secondary'],
               transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
    else:
        # Extraire données
        product_names = [p.get('product_name', 'Sans nom')[:30] for p in sorted_products]
        revenues = [p.get('revenue', 0) for p in sorted_products]
        sales_counts = [p.get('sales_count', 0) for p in sorted_products]

        # Gradient de couleurs
        colors = []
        for i in range(len(product_names)):
            ratio = i / max(len(product_names) - 1, 1)
            colors.append(CHART_COLORS['primary'] if ratio < 0.5 else CHART_COLORS['accent'])

        # Barres horizontales
        bars = ax.barh(product_names, revenues, color=colors, alpha=0.8)

        # Annotations nombre de ventes
        for i, (bar, sales) in enumerate(zip(bars, sales_counts)):
            width = bar.get_width()
            ax.text(width + max(revenues) * 0.02, bar.get_y() + bar.get_height()/2,
                   f'{sales} ventes',
                   va='center',
                   fontsize=10,
                   color=CHART_COLORS['text_secondary'])

        # Configurer axes
        ax.set_xlabel('Revenus (€)', fontsize=12, fontweight='bold')
        ax.set_title(f'🏆 Top {len(product_names)} Produits par Revenus',
                    fontsize=16,
                    fontweight='bold',
                    color=CHART_COLORS['primary'],
                    pad=20)

        # Grille verticale uniquement
        ax.grid(True, axis='x', alpha=0.2, linestyle='--')
        ax.set_axisbelow(True)
        ax.invert_yaxis()  # Meilleur en haut

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_conversion_funnel_chart(funnel_data: Dict) -> io.BytesIO:
    """
    Génère un funnel de conversion

    Args:
        funnel_data: {'views': int, 'previews': int, 'cart_adds': int, 'purchases': int}

    Returns:
        BytesIO contenant l'image PNG
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib required for image charts")

    setup_chart_theme()

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)

    # Données
    stages = ['👁️ Vues', '🔍 Previews', '🛒 Panier', '✅ Achats']
    values = [
        funnel_data.get('views', 0),
        funnel_data.get('previews', 0),
        funnel_data.get('cart_adds', 0),
        funnel_data.get('purchases', 0)
    ]

    # Taux conversion
    conversions = []
    for i in range(len(values) - 1):
        if values[i] > 0:
            conv = (values[i + 1] / values[i]) * 100
            conversions.append(f'{conv:.1f}%')
        else:
            conversions.append('0%')

    # Couleurs
    colors = [CHART_COLORS['primary'], CHART_COLORS['accent'],
              CHART_COLORS['success'], CHART_COLORS['warning']]

    # Barres horizontales
    y_positions = range(len(stages))
    bars = ax.barh(y_positions, values, color=colors, alpha=0.7)

    # Annotations
    for i, (bar, stage, value) in enumerate(zip(bars, stages, values)):
        ax.text(value + max(values) * 0.02, bar.get_y() + bar.get_height()/2,
               f'{value}',
               va='center',
               fontsize=12,
               fontweight='bold',
               color=CHART_COLORS['text_primary'])

        # Taux conversion entre étapes
        if i < len(conversions):
            ax.text(max(values) * 0.5, i + 0.5,
                   f'▼ {conversions[i]}',
                   ha='center',
                   fontsize=10,
                   color=CHART_COLORS['text_secondary'],
                   style='italic')

    # Config axes
    ax.set_yticks(y_positions)
    ax.set_yticklabels(stages, fontsize=12)
    ax.set_xlabel('Nombre d\'utilisateurs', fontsize=12, fontweight='bold')
    ax.set_title('🎯 Funnel de Conversion',
                fontsize=16,
                fontweight='bold',
                color=CHART_COLORS['primary'],
                pad=20)

    # Conversion globale
    if values[0] > 0:
        overall_conv = (values[-1] / values[0]) * 100
        ax.text(0.98, 0.02, f'Conversion globale: {overall_conv:.1f}%',
               transform=ax.transAxes,
               ha='right',
               fontsize=12,
               fontweight='bold',
               bbox=dict(boxstyle='round', facecolor=CHART_COLORS['success'], alpha=0.3),
               color=CHART_COLORS['text_primary'])

    ax.grid(True, axis='x', alpha=0.2, linestyle='--')
    ax.set_axisbelow(True)
    ax.invert_yaxis()

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    return buf