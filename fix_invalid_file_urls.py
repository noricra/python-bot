"""
Script pour corriger les main_file_url invalides dans la base de données
"""
import psycopg2.extras
from app.core.db_pool import init_connection_pool, get_connection, put_connection

def fix_invalid_file_urls():
    """Corrige les main_file_url invalides"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Trouver tous les produits avec des URLs invalides
        cursor.execute('''
            SELECT product_id, title, main_file_url, seller_user_id
            FROM products
            WHERE main_file_url IS NOT NULL
            AND (
                main_file_url = 'main_file_url'
                OR main_file_url LIKE 'uploads/%'
                OR main_file_url NOT LIKE 'https://%'
            )
        ''')

        invalid_products = cursor.fetchall()

        if not invalid_products:
            print("✅ Aucun produit avec URL invalide trouvé")
            return

        print(f"🔍 Trouvé {len(invalid_products)} produit(s) avec URL invalide:\n")

        for product in invalid_products:
            print(f"📦 {product['product_id']} - {product['title']}")
            print(f"   URL invalide: {product['main_file_url']}")

        print("\n" + "=" * 80)
        print("CORRECTION:")
        print("=" * 80)

        # Mettre à NULL les URLs invalides
        cursor.execute('''
            UPDATE products
            SET main_file_url = NULL
            WHERE main_file_url IS NOT NULL
            AND (
                main_file_url = 'main_file_url'
                OR main_file_url LIKE 'uploads/%'
                OR main_file_url NOT LIKE 'https://%'
            )
        ''')

        affected = cursor.rowcount
        conn.commit()

        print(f"\n✅ {affected} produit(s) corrigé(s) - main_file_url mis à NULL")
        print("\n⚠️  ACTION REQUISE:")
        print("   Les vendeurs devront re-upload leurs fichiers pour ces produits.")
        print("   Le système stockera maintenant correctement les URLs B2.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        put_connection(conn)

if __name__ == "__main__":
    print("🔧 Correction des main_file_url invalides...\n")
    # Initialize connection pool
    init_connection_pool()
    fix_invalid_file_urls()
