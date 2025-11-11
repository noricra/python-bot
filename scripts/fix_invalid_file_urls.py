#!/usr/bin/env python3
"""
Script to find and fix invalid main_file_url values in products table.

This fixes products that have:
- main_file_url = NULL
- main_file_url = empty string
- main_file_url = 'uploads/main_file_url' (literal string bug)
- main_file_url starting with 'uploads/' (local path instead of B2 URL)
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
import psycopg2.extras
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_invalid_products():
    """Find all products with invalid main_file_url"""
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Find products with invalid URLs
        cursor.execute('''
            SELECT
                product_id,
                title,
                seller_user_id,
                main_file_url,
                cover_image_url,
                status
            FROM products
            WHERE
                main_file_url IS NULL
                OR main_file_url = ''
                OR main_file_url LIKE 'uploads/%'
                OR main_file_url = 'main_file_url'
            ORDER BY created_at DESC
        ''')

        products = cursor.fetchall()
        put_connection(conn)

        return products

    except Exception as e:
        put_connection(conn)
        logger.error(f"Error finding invalid products: {e}")
        return []


def fix_product_file_url(product_id: str, seller_id: int):
    """
    Try to fix a product's main_file_url by checking B2

    Args:
        product_id: Product ID
        seller_id: Seller user ID
    """
    from app.services.b2_storage_service import B2StorageService

    b2_service = B2StorageService()

    # Common file extensions to try
    extensions = ['.pdf', '.zip', '.mp4', '.docx', '.pptx', '.xlsx', '.jpg', '.png']

    for ext in extensions:
        # Try to find file on B2
        possible_key = f"products/{product_id}/file{ext}"

        if b2_service.file_exists(possible_key):
            # Found it! Update the database
            b2_url = f"{b2_service.client._endpoint.host}/{b2_service.bucket_name}/{possible_key}"

            conn = get_postgresql_connection()
            cursor = conn.cursor()

            try:
                cursor.execute('''
                    UPDATE products
                    SET main_file_url = %s
                    WHERE product_id = %s
                ''', (b2_url, product_id))

                conn.commit()
                put_connection(conn)

                logger.info(f"✅ Fixed {product_id}: {b2_url}")
                return True

            except Exception as e:
                conn.rollback()
                put_connection(conn)
                logger.error(f"Error updating product {product_id}: {e}")
                return False

    logger.warning(f"⚠️  Could not find file on B2 for {product_id}")
    return False


def deactivate_broken_products():
    """Deactivate products that have no valid file"""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE products
            SET status = 'inactive',
                admin_deactivation_reason = 'Fichier principal manquant ou invalide'
            WHERE
                (main_file_url IS NULL
                OR main_file_url = ''
                OR main_file_url LIKE 'uploads/%'
                OR main_file_url = 'main_file_url')
                AND status = 'active'
        ''')

        count = cursor.rowcount
        conn.commit()
        put_connection(conn)

        logger.info(f"✅ Deactivated {count} broken products")
        return count

    except Exception as e:
        conn.rollback()
        put_connection(conn)
        logger.error(f"Error deactivating products: {e}")
        return 0


def main():
    """Main script execution"""
    print("=" * 60)
    print("PRODUCT FILE URL FIXER")
    print("=" * 60)
    print()

    # Find invalid products
    print("🔍 Searching for products with invalid file URLs...")
    invalid_products = find_invalid_products()

    if not invalid_products:
        print("✅ No invalid products found!")
        return

    print(f"\n❌ Found {len(invalid_products)} invalid products:\n")

    for product in invalid_products:
        print(f"  • {product['product_id']}: {product['title']}")
        print(f"    URL: {product['main_file_url']}")
        print(f"    Status: {product['status']}")
        print()

    # Ask what to do
    print("\nOptions:")
    print("1. Try to auto-fix by finding files on B2")
    print("2. Deactivate all broken products")
    print("3. Show details only (no changes)")
    print("4. Exit")

    choice = input("\nYour choice (1-4): ").strip()

    if choice == "1":
        print("\n🔧 Attempting to auto-fix...")
        fixed_count = 0
        for product in invalid_products:
            if fix_product_file_url(product['product_id'], product['seller_user_id']):
                fixed_count += 1

        print(f"\n✅ Fixed {fixed_count}/{len(invalid_products)} products")

        if fixed_count < len(invalid_products):
            remaining = len(invalid_products) - fixed_count
            print(f"⚠️  {remaining} products could not be auto-fixed")

            if input("\nDeactivate remaining broken products? (y/n): ").lower() == 'y':
                deactivate_broken_products()

    elif choice == "2":
        if input("\n⚠️  This will deactivate all broken products. Confirm? (y/n): ").lower() == 'y':
            deactivate_broken_products()

    elif choice == "3":
        print("\n📋 Details shown above. No changes made.")

    else:
        print("\n👋 Exiting...")


if __name__ == "__main__":
    main()
