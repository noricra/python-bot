#!/usr/bin/env python3
"""
Script Admin - Nettoyage des produits orphelins
Supprime les produits que tu ne peux pas delete via le bot
"""

import sqlite3
import sys

DATABASE_PATH = "marketplace_database.db"

def list_products():
    """Liste tous les produits avec leurs infos"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

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

    for i, (pid, seller_id, title, created, status) in enumerate(products, 1):
        print(f"{i}. {pid}")
        print(f"   Titre: {title}")
        print(f"   Seller ID: {seller_id}")
        print(f"   Créé: {created}")
        print(f"   Status: {status}")
        print()

    return products


def delete_product_force(product_id):
    """Supprime un produit SANS vérifier le seller_id"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get product info first
    cursor.execute("SELECT title, seller_user_id FROM products WHERE product_id = ?", (product_id,))
    result = cursor.fetchone()

    if not result:
        print(f"❌ Produit {product_id} introuvable")
        conn.close()
        return False

    title, seller_id = result
    print(f"\n🗑️  Suppression FORCÉE de:")
    print(f"   ID: {product_id}")
    print(f"   Titre: {title}")
    print(f"   Seller: {seller_id}")

    confirm = input("\n⚠️  CONFIRMER LA SUPPRESSION ? (yes/no): ")

    if confirm.lower() != 'yes':
        print("❌ Annulé")
        conn.close()
        return False

    try:
        # Delete without checking seller_id
        cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
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
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]

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
