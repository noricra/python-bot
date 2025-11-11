"""
Vérifier les ordres avec des file_path invalides
"""
import psycopg2.extras
from app.core.db_pool import init_connection_pool, get_connection, put_connection

def check_orders():
    """Vérifie les ordres"""
    init_connection_pool()
    conn = get_connection()
    cursor = cursor.execute('''
            SELECT
                o.order_id,
                o.product_id,
                p.title,
                p.main_file_url,
                o.payment_status
            FROM orders o
            LEFT JOIN products p ON p.product_id = o.product_id
            ORDER BY o.created_at DESC
            LIMIT 10
        ''')

    orders = cursor.fetchall()

    print("=" * 80)
    print("DERNIÈRES COMMANDES ET LEURS FICHIERS")
    print("=" * 80)

    for order in orders:
        print(f"\n📦 Order: {order['order_id']}")
        print(f"   Produit: {order['title']}")
        print(f"   main_file_url: {order['main_file_url']}")
        print(f"   Statut: {order['payment_status']}")

        if order['main_file_url'] and not order['main_file_url'].startswith('https://'):
            print(f"   ⚠️  URL INVALIDE!")

    put_connection(conn)

if __name__ == "__main__":
    check_orders()
