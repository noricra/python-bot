#!/usr/bin/env python3
"""
Script Admin - Nettoyage des produits orphelins
Supprime les produits que tu ne peux pas delete via le bot
"""

import psycopg2
import psycopg2.extras
import sys
from app.core.database_init import get_postgresql_connection

def list_products():
    """Liste tous les produits avec leurs infos"""
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT product_id, seller_user_id, title, created_at, status
        FROM products
        ORDER BY created_at DESC
    """)

    products = cursor.fetchall()
    conn.close()

    print("\n" + "="*80)
    print("📦 TOUS LES PRODUITS")
    print("="*80)

    if not products:
        print("Aucun produit dans la base.")
        return []

    for i, product in enumerate(products, 1):
        print(f"{i}. {product['product_id']}")
        print(f"   Titre: {product['title']}")
        print(f"   Seller ID: {product['seller_user_id']}")
        print(f"   Créé: {product['created_at']}")
        print(f"   Status: {product['status']}")
        print()

    return products


def delete_product_force(product_id):
    """Supprime un produit SANS vérifier le seller_id"""
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get product info first
    cursor.execute("SELECT title, seller_user_id FROM products WHERE product_id = %s", (product_id,))
    result = cursor.fetchone()

    if not result:
        print(f"❌ Produit {product_id} introuvable")
        conn.close()
        return False

    print(f"\n🗑️  Suppression FORCÉE de:")
    print(f"   ID: {product_id}")
    print(f"   Titre: {result['title']}")
    print(f"   Seller: {result['seller_user_id']}")

    confirm = input("\n⚠️  CONFIRMER LA SUPPRESSION ? (yes/no): ")

    if confirm.lower() != 'yes':
        print("❌ Annulé")
        conn.close()
        return False

    try:
        # Delete without checking seller_id
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        deleted = cursor.rowcount

        conn.commit()

        if deleted > 0:
            print(f"✅ Produit {product_id} supprimé avec succès")
            return True
        else:
            print(f"❌ Échec de la suppression")
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_all_products():
    """Supprime TOUS les produits (DANGER!)"""
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT COUNT(*) as count FROM products")
    count = cursor.fetchone()['count']

    print(f"\n⚠️  DANGER: Supprimer TOUS les {count} produits ?")
    confirm = input("Tapez 'DELETE ALL' pour confirmer: ")

    if confirm != 'DELETE ALL':
        print("❌ Annulé")
        conn.close()
        return

    cursor.execute("DELETE FROM products")
    cursor.execute("UPDATE categories SET products_count = 0")
    conn.commit()
    conn.close()

    print(f"✅ {count} produits supprimés")


def main():
    print("\n🛠️  ADMIN TOOL - Nettoyage Produits")

    products = list_products()

    if not products:
        return

    print("\n" + "="*80)
    print("OPTIONS:")
    print("  1 - Supprimer un produit spécifique (force)")
    print("  2 - Supprimer TOUS les produits (DANGER)")
    print("  0 - Quitter")
    print("="*80)

    choice = input("\nChoix: ")

    if choice == '1':
        product_id = input("\nProduct ID à supprimer: ")
        delete_product_force(product_id)

    elif choice == '2':
        delete_all_products()

    elif choice == '0':
        print("Bye!")

    else:
        print("❌ Choix invalide")


if __name__ == "__main__":
    main()
