"""
Cleanup Task: Remove old soft-deleted products
Automatically cleans up products deleted more than 90 days ago with no recent orders.
"""
import logging
import psycopg2
import psycopg2.extras
from typing import Dict
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
from app.services.b2_storage_service import B2StorageService
import os
import shutil

logger = logging.getLogger(__name__)


def cleanup_old_deleted_products(dry_run: bool = False) -> Dict:
    """
    Clean up products soft-deleted more than 90 days ago
    with no recent orders in the last 30 days.

    Strategy:
    - Find products with deleted_at > 90 days ago
    - Check no orders in last 30 days
    - Delete B2 files (main file + images)
    - Delete local images
    - Hard delete from database

    Args:
        dry_run: If True, only log what would be deleted without actually deleting

    Returns:
        dict: Statistics about cleanup operation
    """
    try:
        logger.info(f"🧹 Starting cleanup of old deleted products (dry_run={dry_run})...")

        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Find products to clean up
        cursor.execute('''
            SELECT
                p.product_id,
                p.seller_user_id,
                p.main_file_url,
                p.deleted_at,
                COUNT(o.order_id) as recent_orders_count
            FROM products p
            LEFT JOIN orders o ON o.product_id = p.product_id
                AND o.created_at > NOW() - INTERVAL '30 days'
            WHERE p.deleted_at IS NOT NULL
                AND p.deleted_at < NOW() - INTERVAL '90 days'
            GROUP BY p.product_id, p.seller_user_id, p.main_file_url, p.deleted_at
            HAVING COUNT(o.order_id) = 0
        ''')

        products_to_clean = cursor.fetchall()
        stats = {
            'total_found': len(products_to_clean),
            'cleaned': 0,
            'b2_files_deleted': 0,
            'local_dirs_deleted': 0,
            'db_deleted': 0,
            'errors': 0
        }

        if not products_to_clean:
            logger.info("✅ No products to clean up")
            put_connection(conn)
            return stats

        logger.info(f"📋 Found {stats['total_found']} products to clean up")

        # Initialize B2 service
        b2 = B2StorageService()

        for product in products_to_clean:
            product_id = product['product_id']
            seller_user_id = product['seller_user_id']
            main_file_url = product['main_file_url']

            try:
                logger.info(f"🗑️ Cleaning product {product_id} (deleted {product['deleted_at']})")

                if dry_run:
                    logger.info(f"   [DRY RUN] Would delete B2 files for {product_id}")
                    logger.info(f"   [DRY RUN] Would delete local images for {product_id}")
                    logger.info(f"   [DRY RUN] Would hard delete {product_id} from DB")
                    stats['cleaned'] += 1
                    continue

                # 1. Delete B2 main file
                if main_file_url:
                    success = b2.delete_file(main_file_url)
                    if success:
                        logger.info(f"   ✅ Deleted B2 file: {main_file_url}")
                        stats['b2_files_deleted'] += 1
                    else:
                        logger.warning(f"   ⚠️ Failed to delete B2 file: {main_file_url}")

                # 2. Delete B2 images
                cover_b2_key = f"products/{product_id}/cover.jpg"
                thumb_b2_key = f"products/{product_id}/thumb.jpg"

                b2.delete_file(cover_b2_key)
                b2.delete_file(thumb_b2_key)
                logger.info(f"   ✅ Deleted B2 images: {product_id}")
                stats['b2_files_deleted'] += 2

                # 3. Delete local images directory
                local_dir = os.path.join('data', 'product_images', str(seller_user_id), product_id)
                if os.path.exists(local_dir):
                    shutil.rmtree(local_dir)
                    logger.info(f"   ✅ Deleted local directory: {local_dir}")
                    stats['local_dirs_deleted'] += 1

                # 4. Hard delete from database
                cursor.execute(
                    'DELETE FROM products WHERE product_id = %s',
                    (product_id,)
                )
                logger.info(f"   ✅ Deleted from DB: {product_id}")
                stats['db_deleted'] += 1
                stats['cleaned'] += 1

            except Exception as e:
                logger.error(f"   ❌ Error cleaning product {product_id}: {e}")
                stats['errors'] += 1

        # Commit all deletions
        if not dry_run:
            conn.commit()
            logger.info("✅ All deletions committed to database")

        put_connection(conn)
        logger.info(f"✅ Cleanup complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return {'error': str(e)}


def schedule_periodic_cleanup():
    """
    Schedule periodic cleanup (to be called from bot startup)
    Runs cleanup every 7 days
    """
    import asyncio

    async def periodic_task():
        while True:
            try:
                # Wait 7 days
                await asyncio.sleep(7 * 24 * 3600)

                # Run cleanup
                logger.info("⏰ Running scheduled cleanup of old deleted products")
                stats = cleanup_old_deleted_products(dry_run=False)
                logger.info(f"📊 Scheduled cleanup stats: {stats}")

            except Exception as e:
                logger.error(f"❌ Scheduled cleanup error: {e}")
                # Wait 1 hour before retrying
                await asyncio.sleep(3600)

    return asyncio.create_task(periodic_task())


if __name__ == "__main__":
    # Manual run with dry_run
    print("🧪 Running cleanup in DRY RUN mode...")
    stats = cleanup_old_deleted_products(dry_run=True)
    print(f"\n📊 Results: {stats}")

    # Uncomment to run for real
    # print("\n⚠️ Running cleanup for REAL...")
    # stats = cleanup_old_deleted_products(dry_run=False)
    # print(f"\n📊 Results: {stats}")
