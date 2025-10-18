"""
Product Service - Business logic for product operations
"""
import re
import logging
from typing import Dict, Any, Optional, List
from app.core import get_sqlite_connection

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product business logic"""

    def __init__(self, db_path: str = None, product_repo=None):
        self.db_path = db_path
        self.product_repo = product_repo

    def validate_product_id_format(self, product_id: str) -> bool:
        """Basic product ID validation - accept any non-empty string"""
        return bool(product_id and product_id.strip())

    def get_product_with_seller_info(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product with seller information"""
        try:
            conn = get_sqlite_connection(self.db_path)
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = ? AND p.status = 'active'
            ''', (product_id,))

            product = cursor.fetchone()
            conn.close()
            return product

        except Exception as e:
            logger.error(f"❌ Error getting product with seller info: {e}")
            return None

    def increment_product_views(self, product_id: str) -> bool:
        """Increment product view count"""
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE products SET views_count = views_count + 1 WHERE product_id = ?',
                (product_id,)
            )
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            logger.error(f"❌ Error incrementing views: {e}")
            return False

    def search_products_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search products by category"""
        try:
            conn = get_sqlite_connection(self.db_path)
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.*, u.seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.category = ? AND p.status = 'active'
                ORDER BY p.created_at DESC
                LIMIT ?
            ''', (category, limit))

            products = cursor.fetchall()
            conn.close()
            return products

        except Exception as e:
            logger.error(f"❌ Error searching products by category: {e}")
            return []

    def create_product(self, seller_user_id: int, title: str, description: str,
                      price: float, category: str, file_path: str) -> str:
        """Create a new product and return its ID"""
        try:
            from app.core.utils import generate_product_id

            # Generate unique product ID
            product_id = generate_product_id(self.db_path)

            # Prepare product data
            product_dict = {
                'product_id': product_id,
                'seller_user_id': seller_user_id,
                'title': title,
                'description': description,
                'category': category,
                'price_eur': price,
                'price_usd': price * 1.1,  # Simple EUR->USD conversion
                'main_file_path': file_path,
                'file_size_mb': 2.0,  # Default size
                'status': 'active'
            }

            # Use self.product_repo if available, otherwise create new instance
            if self.product_repo:
                success = self.product_repo.insert_product(product_dict)
            else:
                from app.domain.repositories.product_repo import ProductRepository
                product_repo = ProductRepository(self.db_path)
                success = product_repo.insert_product(product_dict)

            return product_id if success else None

        except Exception as e:
            logger.error(f"❌ Error creating product: {e}")
            return None

    def get_user_purchases(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's purchased products"""
        try:
            conn = get_sqlite_connection(self.db_path)
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.product_id, p.title, o.completed_at
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = ? AND o.payment_status = 'completed'
                ORDER BY o.completed_at DESC
                LIMIT ?
            ''', (user_id, limit))

            purchases = cursor.fetchall()
            conn.close()
            return purchases

        except Exception as e:
            logger.error(f"❌ Error getting user purchases: {e}")
            return []

    def check_user_has_purchased(self, user_id: int, product_id: str) -> bool:
        """Check if user has purchased a specific product"""
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*)
                FROM orders
                WHERE buyer_user_id = ? AND product_id = ? AND payment_status = 'completed'
            ''', (user_id, product_id))

            count = cursor.fetchone()[0]
            conn.close()
            return count > 0

        except Exception as e:
            logger.error(f"❌ Error checking purchase: {e}")
            return False

    def get_product_file_info(self, user_id: int, product_id: str) -> Optional[Dict[str, str]]:
        """Get product file information for download"""
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.main_file_path, p.title
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.buyer_user_id = ? AND o.product_id = ? AND o.payment_status = 'completed'
            ''', (user_id, product_id))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'file_path': result[0],
                    'title': result[1]
                }
            return None

        except Exception as e:
            logger.error(f"❌ Error getting file info: {e}")
            return None