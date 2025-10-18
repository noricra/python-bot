"""
Test script pour générer et visualiser les graphiques matplotlib
"""
from datetime import datetime, timedelta
from app.core import chart_generator
import logging

logging.basicConfig(level=logging.INFO)

def test_revenue_chart():
    """Test graphique revenus timeline"""
    print("📈 Test: Graphique Revenus Timeline")

    # Données factices (7 derniers jours)
    sales_data = []
    today = datetime.now()

    # Simuler des ventes
    revenues_per_day = [10.0, 25.0, 15.5, 42.0, 38.0, 55.5, 62.0]

    for i, rev in enumerate(revenues_per_day):
        date = today - timedelta(days=6-i)
        sales_data.append({
            'date': date,
            'revenue': rev
        })

    # Générer graphique
    try:
        chart_buffer = chart_generator.generate_revenue_chart(sales_data, days=7)
        print(f"✅ Graphique généré! Taille: {len(chart_buffer.getvalue())} bytes")

        # Sauvegarder pour visualisation
        with open('/tmp/test_revenue_chart.png', 'wb') as f:
            f.write(chart_buffer.getvalue())
        print("💾 Sauvegardé dans: /tmp/test_revenue_chart.png")

    except Exception as e:
        print(f"❌ Erreur: {e}")


def test_products_chart():
    """Test graphique produits bar chart"""
    print("\n🏆 Test: Graphique Top Produits")

    # Données factices
    product_sales = [
        {'product_name': 'Guide Trading Crypto 2025', 'sales_count': 18, 'revenue': 899.82},
        {'product_name': 'Formation Python Pro', 'sales_count': 12, 'revenue': 588.0},
        {'product_name': 'Pack Design Graphique', 'sales_count': 8, 'revenue': 319.92},
        {'product_name': 'Cours Marketing Digital', 'sales_count': 5, 'revenue': 199.95},
        {'product_name': 'Templates Web Premium', 'sales_count': 3, 'revenue': 89.97},
    ]

    # Générer graphique
    try:
        chart_buffer = chart_generator.generate_products_chart(product_sales, top_n=5)
        print(f"✅ Graphique généré! Taille: {len(chart_buffer.getvalue())} bytes")

        # Sauvegarder
        with open('/tmp/test_products_chart.png', 'wb') as f:
            f.write(chart_buffer.getvalue())
        print("💾 Sauvegardé dans: /tmp/test_products_chart.png")

    except Exception as e:
        print(f"❌ Erreur: {e}")


def test_funnel_chart():
    """Test graphique funnel de conversion"""
    print("\n🎯 Test: Graphique Funnel Conversion")

    # Données factices
    funnel_data = {
        'views': 1250,
        'previews': 342,
        'cart_adds': 128,
        'purchases': 45
    }

    # Générer graphique
    try:
        chart_buffer = chart_generator.generate_conversion_funnel_chart(funnel_data)
        print(f"✅ Graphique généré! Taille: {len(chart_buffer.getvalue())} bytes")

        # Sauvegarder
        with open('/tmp/test_funnel_chart.png', 'wb') as f:
            f.write(chart_buffer.getvalue())
        print("💾 Sauvegardé dans: /tmp/test_funnel_chart.png")

    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    print("🎨 Test Génération Graphiques Matplotlib pour Ferus\n")
    print("=" * 60)

    test_revenue_chart()
    test_products_chart()
    test_funnel_chart()

    print("\n" + "=" * 60)
    print("✅ Tests terminés!")
    print("\nVous pouvez visualiser les graphiques dans /tmp/:")
    print("  - test_revenue_chart.png")
    print("  - test_products_chart.png")
    print("  - test_funnel_chart.png")
    print("\nCommande: open /tmp/test_*.png")
