"""Check products in database"""
from dotenv import load_dotenv
from app.core.database_init import get_postgresql_connection

load_dotenv()

try:
    conn = get_postgresql_connection()
    cur = conn.cursor()

    print("=" * 60)
    print("CHECKING PRODUCTS STATUS")
    print("=" * 60)

    # Count by status
    cur.execute("SELECT status, COUNT(*) FROM products GROUP BY status")
    print("\nProducts by status:")
    for status, count in cur.fetchall():
        print(f"  {status}: {count}")

    # Count by category
    cur.execute("SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY category")
    print("\nProducts by category:")
    for category, count in cur.fetchall():
        print(f"  {category}: {count}")

    # Check active products
    cur.execute("""
        SELECT product_id, title, category, status, deactivated_by_admin
        FROM products
        ORDER BY created_at DESC
        LIMIT 5
    """)
    print("\nRecent products (last 5):")
    for product_id, title, category, status, deactivated in cur.fetchall():
        print(f"  {product_id}: {title}")
        print(f"    Category: {category}")
        print(f"    Status: {status}")
        print(f"    Deactivated by admin: {deactivated}")
        print()

    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
