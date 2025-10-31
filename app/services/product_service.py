"""
Product Service - Business logic for product operations
"""
import re
import logging
import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional, List
from app.core.database_init import get_postgresql_connection

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product business logic"""

    def __init__(self, product_repo=None):
        self.product_repo = product_repo

    def validate_product_id_format(self, product_id: str) -> bool:
        """Basic product ID validation - accept any non-empty string"""
        return bool(product_id and product_id.strip())

    def get_product_with_seller_info(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product with seller information"""
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('''
                SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = %s AND p.status = 'active'
            ''', (product_id,))

            product = cursor.fetchone()
            conn.close()
            return product

        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error getting product with seller info: {e}")
            return None

    def increment_product_views(self, product_id: str) -> bool:
        """Increment product view count"""
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                'UPDATE products SET views_count = views_count + 1 WHERE product_id = %s',
                (product_id,)
            )
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error incrementing views: {e}")
            return False

    def search_products_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search products by category"""
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('''
                SELECT p.*, u.seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.category = %s AND p.status = 'active'
                ORDER BY p.created_at DESC
                LIMIT %s
            ''', (category, limit))

            products = cursor.fetchall()
            conn.close()
            return products

        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error searching products by category: {e}")
            return []

    def create_product(self, seller_user_id: int, title: str, description: str,
                      price: float, category: str, file_path: str) -> str:
        """Create a new product and return its ID"""
        try:
            from app.core.utils import generate_product_id

            # Generate unique product ID
            product_id = generate_product_id()

            # Prepare product data
            product_dict = {
                'product_id': product_id,
                'seller_user_id': seller_user_id,
                'title': title,
                'description': description,
                'category': category,
                'price_usd': price,  # Price in USDT
                'main_file_url': file_path,
                'file_size_mb': 2.0,  # Default size
                'status': 'active'
            }

            # Use self.product_repo if available, otherwise create new instance
            if self.product_repo:
                success = self.product_repo.insert_product(product_dict)
            else:
                from app.domain.repositories.product_repo import ProductRepository
                product_repo = ProductRepository()
                success = product_repo.insert_product(product_dict)

            return product_id if success else None

        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error creating product: {e}")
            return None

    def get_user_purchases(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's purchased products"""
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('''
                SELECT p.product_id, p.title, o.completed_at
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = %s AND o.payment_status = 'completed'
                ORDER BY o.completed_at DESC
                LIMIT %s
            ''', (user_id, limit))

            purchases = cursor.fetchall()
            conn.close()
            return purchases

        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error getting user purchases: {e}")
            return []

    def check_user_has_purchased(self, user_id: int, product_id: str) -> bool:
        """Check if user has purchased a specific product"""
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM orders
                WHERE buyer_user_id = %s AND product_id = %s AND payment_status = 'completed'
            ''', (user_id, product_id))

            count = cursor.fetchone()['count']
            conn.close()
            return count > 0

        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error checking purchase: {e}")
            return False

    def get_product_file_info(self, user_id: int, product_id: str) -> Optional[Dict[str, str]]:
        """Get product file information for download"""
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT p.main_file_url, p.title
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = %s AND o.product_id = %s AND o.payment_status = 'completed'
            ''', (user_id, product_id))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'file_path': result['main_file_url'],
                    'title': result['title']
                }
            return None

        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error getting file info: {e}")
            return None