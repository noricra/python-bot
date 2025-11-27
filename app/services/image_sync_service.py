"""
Image Synchronization Service
Ensures product images are available locally, downloading from B2 if needed.
Critical for Railway deployments where local storage is ephemeral.
"""
import os
import logging
from typing import Optional, Tuple
from app.services.b2_storage_service import B2StorageService
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
import psycopg2.extras

logger = logging.getLogger(__name__)


class ImageSyncService:
    """Service to sync product images between local storage and B2"""

    def __init__(self):
        self.b2_service = B2StorageService()

    async def ensure_product_images_local(self, product_id: str, seller_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Ensure product images exist locally, download from B2 if missing (async, non-bloquant).

        This is critical for Railway: after restart, local files are gone but B2 persists.

        Args:
            product_id: Product ID
            seller_id: Seller user ID

        Returns:
            tuple: (local_cover_path, local_thumbnail_path) or (None, None) if unavailable
        """
        try:
            # Define local paths
            product_dir = os.path.join('data', 'product_images', str(seller_id), product_id)
            os.makedirs(product_dir, exist_ok=True)

            cover_local = os.path.join(product_dir, 'cover.jpg')
            thumb_local = os.path.join(product_dir, 'thumb.jpg')

            # Check if files exist locally
            cover_exists = os.path.exists(cover_local)
            thumb_exists = os.path.exists(thumb_local)

            if cover_exists and thumb_exists:
                logger.info(f"✅ Product images already local: {product_id}")
                return cover_local, thumb_local

            # Files missing - download from B2
            logger.warning(f"⚠️ Product images missing locally for {product_id}, downloading from B2...")

            # B2 keys
            cover_b2_key = f"products/{product_id}/cover.jpg"
            thumb_b2_key = f"products/{product_id}/thumb.jpg"

            # Download cover if missing
            if not cover_exists:
                success = await self.b2_service.download_file(cover_b2_key, cover_local)
                if success:
                    logger.info(f"✅ Downloaded cover from B2: {product_id}")
                else:
                    logger.error(f"❌ Failed to download cover from B2: {product_id}")
                    cover_local = None

            # Download thumbnail if missing
            if not thumb_exists:
                success = await self.b2_service.download_file(thumb_b2_key, thumb_local)
                if success:
                    logger.info(f"✅ Downloaded thumbnail from B2: {product_id}")
                else:
                    logger.error(f"❌ Failed to download thumbnail from B2: {product_id}")
                    thumb_local = None

            return cover_local, thumb_local

        except Exception as e:
            logger.error(f"❌ Error ensuring product images local: {e}")
            return None, None

    def sync_all_products_on_startup(self) -> dict:
        """
        Sync all products' images from B2 on app startup.

        This ensures Railway has all product images after restart.
        Only downloads missing files to save bandwidth.

        Returns:
            dict: Stats about sync operation
        """
        try:
            logger.info("🔄 Starting product images sync from B2...")

            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Get all products with images
            cursor.execute("""
                SELECT product_id, seller_user_id, cover_image_url, thumbnail_url
                FROM products
                WHERE cover_image_url IS NOT NULL
                AND status = 'active'
            """)
            products = cursor.fetchall()
            put_connection(conn)

            stats = {
                'total': len(products),
                'synced': 0,
                'already_local': 0,
                'failed': 0
            }

            for product in products:
                product_id = product['product_id']
                seller_id = product['seller_user_id']

                # Check if images exist locally
                product_dir = os.path.join('data', 'product_images', str(seller_id), product_id)
                cover_local = os.path.join(product_dir, 'cover.jpg')
                thumb_local = os.path.join(product_dir, 'thumb.jpg')

                if os.path.exists(cover_local) and os.path.exists(thumb_local):
                    stats['already_local'] += 1
                    continue

                # Download missing images
                cover_path, thumb_path = self.ensure_product_images_local(product_id, seller_id)

                if cover_path and thumb_path:
                    stats['synced'] += 1
                else:
                    stats['failed'] += 1

            logger.info(f"✅ Image sync complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"❌ Error syncing products on startup: {e}")
            return {'error': str(e)}

    def get_image_path_with_fallback(self, product_id: str, seller_id: int, image_type: str = 'cover') -> Optional[str]:
        """
        Get image path with automatic B2 download fallback.

        Args:
            product_id: Product ID
            seller_id: Seller user ID
            image_type: 'cover' or 'thumb'

        Returns:
            str: Local path to image, or None if unavailable
        """
        try:
            # Define local path
            product_dir = os.path.join('data', 'product_images', str(seller_id), product_id)
            filename = 'cover.jpg' if image_type == 'cover' else 'thumb.jpg'
            local_path = os.path.join(product_dir, filename)

            # Check if exists locally
            if os.path.exists(local_path):
                return local_path

            # Download from B2
            logger.info(f"🔄 Image not local, downloading from B2: {product_id}/{filename}")
            os.makedirs(product_dir, exist_ok=True)

            b2_key = f"products/{product_id}/{filename}"
            success = self.b2_service.download_file(b2_key, local_path)

            if success and os.path.exists(local_path):
                logger.info(f"✅ Downloaded {image_type} from B2: {product_id}")
                return local_path
            else:
                logger.error(f"❌ Failed to download {image_type} from B2: {product_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting image with fallback: {e}")
            return None

    async def backup_to_b2_if_missing(self, product_id: str, seller_id: int) -> bool:
        """
        Backup local images to B2 if not already there (async, non-bloquant).

        Useful after Railway restart to re-upload any missing B2 files.

        Args:
            product_id: Product ID
            seller_id: Seller user ID

        Returns:
            bool: True if successful or already backed up
        """
        try:
            # Check local files
            product_dir = os.path.join('data', 'product_images', str(seller_id), product_id)
            cover_local = os.path.join(product_dir, 'cover.jpg')
            thumb_local = os.path.join(product_dir, 'thumb.jpg')

            if not os.path.exists(cover_local) or not os.path.exists(thumb_local):
                logger.warning(f"⚠️ Local images missing, cannot backup: {product_id}")
                return False

            # B2 keys
            cover_b2_key = f"products/{product_id}/cover.jpg"
            thumb_b2_key = f"products/{product_id}/thumb.jpg"

            # Check if already on B2
            cover_exists = self.b2_service.file_exists(cover_b2_key)
            thumb_exists = self.b2_service.file_exists(thumb_b2_key)

            if cover_exists and thumb_exists:
                logger.info(f"✅ Images already on B2: {product_id}")
                return True

            # Upload missing files
            if not cover_exists:
                result = await self.b2_service.upload_file(cover_local, cover_b2_key)
                if result:
                    logger.info(f"✅ Backed up cover to B2: {product_id}")
                else:
                    logger.error(f"❌ Failed to backup cover to B2: {product_id}")
                    return False

            if not thumb_exists:
                result = await self.b2_service.upload_file(thumb_local, thumb_b2_key)
                if result:
                    logger.info(f"✅ Backed up thumbnail to B2: {product_id}")
                else:
                    logger.error(f"❌ Failed to backup thumbnail to B2: {product_id}")
                    return False

            return True

        except Exception as e:
            logger.error(f"❌ Error backing up to B2: {e}")
            return False
