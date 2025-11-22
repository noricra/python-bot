#!/usr/bin/env python3
"""
Migration script: Upload all local product images to B2 and update DB
"""
import os
import sys
import psycopg2
import psycopg2.extras
from app.services.b2_storage_service import B2StorageService
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection, init_connection_pool
from app.core.settings import settings

def migrate_images_to_b2():
    """Upload all local product images to B2 and update DB with B2 URLs"""

    # Initialize connection pool first (CRITICAL)
    print("🔌 Initializing database connection pool...")
    init_connection_pool(min_connections=1, max_connections=3)

    b2_service = B2StorageService()

    print("🚀 Starting image migration to B2...")

    # Get all products with local image paths
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT product_id, seller_user_id, thumbnail_url, cover_image_url
        FROM products
        WHERE thumbnail_url IS NOT NULL
        AND thumbnail_url NOT LIKE 'https://%'
    """)

    products = cursor.fetchall()
    put_connection(conn)

    print(f"📊 Found {len(products)} products with local images\n")

    success_count = 0
    fail_count = 0

    for product in products:
        product_id = product['product_id']
        seller_id = product['seller_user_id']
        local_thumb = product['thumbnail_url']
        local_cover = product['cover_image_url']

        print(f"🔄 Processing {product_id}...")

        try:
            # Check if local files exist
            if not os.path.exists(local_thumb) or not os.path.exists(local_cover):
                print(f"  ⚠️  Local files missing, skipping")
                fail_count += 1
                continue

            # Upload to B2
            thumb_b2_key = f"products/{product_id}/thumb.jpg"
            cover_b2_key = f"products/{product_id}/cover.jpg"

            print(f"  📤 Uploading to B2...")
            thumb_url = b2_service.upload_file(local_thumb, thumb_b2_key)
            cover_url = b2_service.upload_file(local_cover, cover_b2_key)

            if not thumb_url or not cover_url:
                print(f"  ❌ B2 upload failed")
                fail_count += 1
                continue

            # Update DB with B2 URLs
            conn = get_postgresql_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products
                SET thumbnail_url = %s,
                    cover_image_url = %s
                WHERE product_id = %s
            """, (thumb_url, cover_url, product_id))
            conn.commit()
            put_connection(conn)

            print(f"  ✅ Migrated successfully")
            print(f"     Thumb: {thumb_url}")
            print(f"     Cover: {cover_url}")
            success_count += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            fail_count += 1
            continue

    print(f"\n📊 Migration complete:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   📦 Total: {len(products)}")

if __name__ == "__main__":
    migrate_images_to_b2()
