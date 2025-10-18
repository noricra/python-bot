#!/usr/bin/env python3
"""
Script de synchronisation des compteurs de ventes
À exécuter après avoir modifié manuellement des statuts de paiement dans la base de données
"""

import sqlite3
import sys
from app.core.settings import settings

def sync_sales_counters():
    """Synchronise les compteurs de ventes avec les commandes complétées"""

    conn = sqlite3.connect(settings.DATABASE_PATH)
    cursor = conn.cursor()

    print("🔄 Synchronisation des compteurs de ventes...")

    try:
        # 1. Réinitialiser tous les compteurs
        print("  ↳ Réinitialisation des compteurs produits...")
        cursor.execute("UPDATE products SET sales_count = 0")

        print("  ↳ Réinitialisation des compteurs vendeurs...")
        cursor.execute("UPDATE users SET total_sales = 0, total_revenue = 0")

        # 2. Recalculer les compteurs par produit
        print("  ↳ Recalcul des ventes par produit...")
        cursor.execute("""
            UPDATE products
            SET sales_count = (
                SELECT COUNT(DISTINCT o.order_id)
                FROM orders o
                WHERE o.product_id = products.product_id
                AND o.payment_status = 'completed'
            )
        """)

        # 3. Recalculer les compteurs par vendeur
        print("  ↳ Recalcul des ventes par vendeur...")
        cursor.execute("""
            UPDATE users
            SET total_sales = (
                SELECT COUNT(DISTINCT o.order_id)
                FROM orders o
                WHERE o.seller_user_id = users.user_id
                AND o.payment_status = 'completed'
            ),
            total_revenue = (
                SELECT COALESCE(SUM(o.product_price_eur), 0)
                FROM orders o
                WHERE o.seller_user_id = users.user_id
                AND o.payment_status = 'completed'
            )
        """)

        conn.commit()

        # 4. Afficher les résultats
        cursor.execute("SELECT COUNT(*) FROM products WHERE sales_count > 0")
        products_with_sales = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE total_sales > 0")
        sellers_with_sales = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders WHERE payment_status = 'completed'")
        total_completed_orders = cursor.fetchone()[0]

        print("\n✅ Synchronisation terminée !")
        print(f"  ↳ Total commandes complétées: {total_completed_orders}")
        print(f"  ↳ Produits avec ventes: {products_with_sales}")
        print(f"  ↳ Vendeurs avec ventes: {sellers_with_sales}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    sync_sales_counters()