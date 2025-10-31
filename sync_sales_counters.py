#!/usr/bin/env python3
"""
Script de synchronisation des compteurs de ventes
À exécuter après avoir modifié manuellement des statuts de paiement dans la base de données
"""

import psycopg2
import psycopg2.extras
import sys
from app.core.database_init import get_postgresql_connection

def sync_sales_counters():
    """Synchronise les compteurs de ventes avec les commandes complétées"""

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
                SELECT COALESCE(SUM(o.product_price_usdt), 0)
                FROM orders o
                WHERE o.seller_user_id = users.user_id
                AND o.payment_status = 'completed'
            )
        """)

        conn.commit()

        # 4. Afficher les résultats
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE sales_count > 0")
        products_with_sales = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE total_sales > 0")
        sellers_with_sales = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE payment_status = 'completed'")
        total_completed_orders = cursor.fetchone()['count']

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