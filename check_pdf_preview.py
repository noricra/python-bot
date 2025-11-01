"""Script pour diagnostiquer le problème d'aperçu PDF"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Import database connection function
from app.core.database_init import get_postgresql_connection

try:
    conn = get_postgresql_connection()
    cur = conn.cursor()

    # First, check table structure
    print("=" * 60)
    print("CHECKING PRODUCTS TABLE STRUCTURE")
    print("=" * 60)

    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'products'
        ORDER BY ordinal_position
    """)

    columns = cur.fetchall()
    for col_name, col_type in columns:
        print(f"   {col_name}: {col_type}")

    # Check recent products with file paths
    print("\n" + "=" * 60)
    print("CHECKING PRODUCT FILE PATHS")
    print("=" * 60)

    cur.execute("""
        SELECT product_id, title, main_file_url, thumbnail_url, cover_image_url
        FROM products
        WHERE main_file_url IS NOT NULL OR thumbnail_url IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 5
    """)

    products = cur.fetchall()

    for product_id, title, main_file, cover, thumb in products:
        print(f"\n📦 Product: {product_id}")
        print(f"   Title: {title}")
        print(f"   Main file: {main_file}")
        print(f"   Cover: {cover}")
        print(f"   Thumbnail: {thumb}")

        # Check if main file exists locally
        if main_file:
            # Try different path constructions
            paths_to_check = [
                main_file,  # As-is
                os.path.join("uploads", main_file),
                os.path.join(os.getcwd(), main_file),
                os.path.join(os.getcwd(), "uploads", main_file)
            ]

            found = False
            for path in paths_to_check:
                if os.path.exists(path):
                    size = os.path.getsize(path) / 1024  # KB
                    print(f"   ✅ File found at: {path} ({size:.1f} KB)")
                    found = True
                    break

            if not found:
                print(f"   ❌ File NOT found (checked {len(paths_to_check)} locations)")
                print(f"      - Is this a B2/cloud URL? {main_file.startswith('http')}")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("CHECKING UPLOADS DIRECTORY")
    print("=" * 60)

    uploads_dir = "uploads"
    if os.path.exists(uploads_dir):
        print(f"✅ Uploads directory exists: {uploads_dir}")

        # List products subdirectory
        products_dir = os.path.join(uploads_dir, "products")
        if os.path.exists(products_dir):
            print(f"✅ Products subdirectory exists")
            subdirs = os.listdir(products_dir)
            print(f"   Found {len(subdirs)} seller directories")
        else:
            print(f"❌ Products subdirectory NOT found")
    else:
        print(f"❌ Uploads directory NOT found: {uploads_dir}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
