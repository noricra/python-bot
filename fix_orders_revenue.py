#!/usr/bin/env python3
"""
Script de migration pour corriger seller_revenue_usd et platform_commission_usd
pour les commandes existantes.

Ce script :
1. Trouve toutes les commandes avec seller_revenue_usd = 0
2. Recalcule seller_revenue_usd et platform_commission_usd
3. Met à jour la DB

Usage:
    python fix_orders_revenue.py
"""

import os
import sys
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def get_db_connection():
    """Connexion à PostgreSQL"""
    # Utiliser les variables PG* comme dans le code
    pghost = os.getenv('PGHOST')
    pgport = os.getenv('PGPORT', 5432)
    pgdatabase = os.getenv('PGDATABASE')
    pguser = os.getenv('PGUSER')
    pgpassword = os.getenv('PGPASSWORD', '')

    if not all([pghost, pgdatabase, pguser]):
        print("❌ Variables PostgreSQL manquantes (PGHOST, PGDATABASE, PGUSER)")
        print(f"   PGHOST: {pghost}")
        print(f"   PGDATABASE: {pgdatabase}")
        print(f"   PGUSER: {pguser}")
        sys.exit(1)

    sslmode = 'prefer' if pghost in ['localhost', '127.0.0.1'] else 'require'

    return psycopg2.connect(
        host=pghost,
        port=pgport,
        database=pgdatabase,
        user=pguser,
        password=pgpassword,
        sslmode=sslmode
    )

def fix_orders_revenue():
    """Corriger les revenus des commandes existantes"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        print("🔍 Recherche des commandes à corriger...")

        # Trouver toutes les commandes avec seller_revenue_usd = 0
        cursor.execute('''
            SELECT order_id, product_price_usd, seller_revenue_usd, platform_commission_usd
            FROM orders
            WHERE seller_revenue_usd = 0 OR platform_commission_usd = 0
        ''')

        orders = cursor.fetchall()

        if not orders:
            print("✅ Aucune commande à corriger !")
            return

        print(f"📊 {len(orders)} commandes trouvées")
        print()

        fixed_count = 0

        for order in orders:
            order_id = order['order_id']
            product_price_usd = order['product_price_usd']

            # Recalculer selon la commission 2.78%
            platform_commission_usd = round(product_price_usd * 0.0278, 2)
            seller_revenue_usd = product_price_usd  # Le vendeur reçoit 100% du prix du produit

            print(f"🔧 Correction de {order_id}:")
            print(f"   Prix produit: ${product_price_usd:.2f}")
            print(f"   Ancien seller_revenue: ${order['seller_revenue_usd']:.2f}")
            print(f"   Nouveau seller_revenue: ${seller_revenue_usd:.2f}")
            print(f"   Commission plateforme: ${platform_commission_usd:.2f}")

            # Mettre à jour
            cursor.execute('''
                UPDATE orders
                SET seller_revenue_usd = %s,
                    platform_commission_usd = %s
                WHERE order_id = %s
            ''', (seller_revenue_usd, platform_commission_usd, order_id))

            fixed_count += 1
            print(f"   ✅ Corrigé")
            print()

        # Commit
        conn.commit()

        print(f"\n✅ Migration terminée ! {fixed_count} commandes corrigées")

        # Afficher les stats
        cursor.execute('SELECT SUM(seller_revenue_usd) as total FROM orders WHERE payment_status = %s', ('completed',))
        total_revenue = cursor.fetchone()['total'] or 0

        cursor.execute('SELECT SUM(platform_commission_usd) as total FROM orders WHERE payment_status = %s', ('completed',))
        total_commission = cursor.fetchone()['total'] or 0

        print(f"\n📊 STATS APRÈS MIGRATION:")
        print(f"   Total revenus vendeurs (commandes complétées): ${total_revenue:.2f}")
        print(f"   Total commissions plateforme: ${total_commission:.2f}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("  MIGRATION: Correction des revenus des commandes")
    print("=" * 60)
    print()

    fix_orders_revenue()

    print()
    print("=" * 60)
    print("  Migration terminée !")
    print("=" * 60)
