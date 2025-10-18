import sqlite3
import logging
from typing import Optional, Dict, List, Tuple

from app.core import get_sqlite_connection, settings as core_settings

logger = logging.getLogger(__name__)


class ProductRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def insert_product(self, product: Dict) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO products
                (product_id, seller_user_id, title, description, category, price_eur, price_usd, main_file_path, file_size_mb, cover_image_path, thumbnail_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    product['product_id'],
                    product['seller_user_id'],
                    product['title'],
                    product.get('description'),
                    product.get('category'),
                    product['price_eur'],
                    product['price_usd'],
                    product.get('main_file_path'),
                    product.get('file_size_mb'),
                    product.get('cover_image_path'),
                    product.get('thumbnail_path'),
                    product.get('status', 'active'),
                ),
            )

            # Update category product count
            category = product.get('category')
            if category:
                cursor.execute(
                    'UPDATE categories SET products_count = products_count + 1 WHERE name = ?',
                    (category,)
                )
                # If category doesn't exist, create it
                if cursor.rowcount == 0:
                    cursor.execute(
                        'INSERT OR IGNORE INTO categories (name, products_count) VALUES (?, 1)',
                        (category,)
                    )

            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            # Join with users table to get seller info
            cursor.execute('''
                SELECT p.*, u.seller_name, u.seller_bio
                FROM products p
                LEFT JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = ?
            ''', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def get_product_with_seller_info(self, product_id: str) -> Optional[Dict]:
        """Récupère un produit avec les informations du vendeur"""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = ? AND p.status = 'active'
                ''', (product_id,))

            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération produit avec seller: {e}")
            return None
        finally:
            conn.close()

    def increment_views(self, product_id: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE products SET views_count = views_count + 1 WHERE product_id = ?',
                (product_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_status(self, product_id: str, status: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE products SET status = ? WHERE product_id = ?',
                (status, product_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_product(self, product_id: str, seller_user_id: int) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            # DEBUG: Check what exists
            cursor.execute('SELECT seller_user_id, title FROM products WHERE product_id = ?', (product_id,))
            check = cursor.fetchone()
            if check:
                logger.info(f"🔍 DELETE CHECK: Product {product_id} exists, seller_id={check[0]}, trying to delete with seller_id={seller_user_id}")
            else:
                logger.warning(f"❌ DELETE CHECK: Product {product_id} NOT FOUND in database")

            # Get category before deletion to update count
            cursor.execute('SELECT category FROM products WHERE product_id = ? AND seller_user_id = ?', (product_id, seller_user_id))
            result = cursor.fetchone()
            category = result[0] if result else None

            if not category:
                logger.warning(f"❌ DELETE FAILED: Product {product_id} not found for seller {seller_user_id} (ownership mismatch or product doesn't exist)")

            cursor.execute(
                'DELETE FROM products WHERE product_id = ? AND seller_user_id = ?',
                (product_id, seller_user_id)
            )

            deleted_count = cursor.rowcount
            logger.info(f"🗑️ DELETE RESULT: Deleted {deleted_count} rows for product {product_id}")

            # Update category product count if deletion was successful
            if deleted_count > 0 and category:
                cursor.execute(
                    'UPDATE categories SET products_count = CASE WHEN products_count > 0 THEN products_count - 1 ELSE 0 END WHERE name = ?',
                    (category,)
                )

            conn.commit()
            return deleted_count > 0
        except sqlite3.Error as e:
            logger.error(f"❌ DELETE ERROR: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_products_by_seller(self, seller_user_id: int, limit: int = None, offset: int = 0) -> List[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            if limit is not None:
                cursor.execute(
                    'SELECT * FROM products WHERE seller_user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
                    (seller_user_id, limit, offset)
                )
            else:
                cursor.execute(
                    'SELECT * FROM products WHERE seller_user_id = ? ORDER BY created_at DESC',
                    (seller_user_id,)
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def count_products_by_seller(self, seller_user_id: int) -> int:
        """Count total products by seller"""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM products WHERE seller_user_id = ?",
                (seller_user_id,)
            )
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    def get_products_by_category(self, category: str, limit: int = 10, offset: int = 0) -> List[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                SELECT * FROM products
                WHERE category = ? AND status = 'active'
                ORDER BY sales_count DESC, created_at DESC
                LIMIT ? OFFSET ?
                ''',
                (category, limit, offset)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def count_products_by_category(self, category: str) -> int:
        """Count total products in a category"""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM products WHERE category = ? AND status = 'active'",
                (category,)
            )
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    def update_price(self, product_id: str, seller_user_id: int, price_eur: float, price_usd: float) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                UPDATE products SET price_eur = ?, price_usd = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ? AND seller_user_id = ?
                ''',
                (price_eur, price_usd, product_id, seller_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_title(self, product_id: str, seller_user_id: int, title: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                UPDATE products SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ? AND seller_user_id = ?
                ''',
                (title, product_id, seller_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_description(self, product_id: str, seller_user_id: int, description: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                UPDATE products SET description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ? AND seller_user_id = ?
                ''',
                (description, product_id, seller_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_all_products(self, limit: int = 100):
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM products ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def count_products(self) -> int:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM products")
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    def create_product(self, product_data: Dict) -> Optional[str]:
        """Create a new product with auto-generated ID"""
        from app.core.utils import generate_product_id

        # Generate unique product ID
        product_id = generate_product_id(self.database_path)

        # Ensure we have all required fields
        product = {
            'product_id': product_id,
            'seller_user_id': product_data.get('seller_id'),
            'title': product_data.get('title'),
            'description': product_data.get('description', ''),
            'category': product_data.get('category', 'General'),
            'price_eur': product_data.get('price_eur'),
            'price_usd': product_data.get('price_usd'),
            'main_file_path': product_data.get('file_path'),
            'file_size_mb': round(product_data.get('file_size', 0) / (1024 * 1024), 2),
            'cover_image_path': product_data.get('cover_image_path'),
            'thumbnail_path': product_data.get('thumbnail_path'),
            'status': 'active'
        }

        if self.insert_product(product):
            return product_id
        else:
            return None

    def recalculate_category_counts(self) -> bool:
        """Recalcule tous les comptages de produits par catégorie"""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            # Reset all counts to 0
            cursor.execute('UPDATE categories SET products_count = 0')

            # Recalculate counts from products table
            cursor.execute('''
                UPDATE categories SET products_count = (
                    SELECT COUNT(*) FROM products
                    WHERE products.category = categories.name
                    AND products.status = 'active'
                )
            ''')

            # Insert missing categories with their counts
            cursor.execute('''
                INSERT OR IGNORE INTO categories (name, products_count)
                SELECT DISTINCT category, COUNT(*)
                FROM products
                WHERE status = 'active' AND category IS NOT NULL
                AND category NOT IN (SELECT name FROM categories)
                GROUP BY category
            ''')

            conn.commit()
            logger.info("Category counts recalculated successfully")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error recalculating category counts: {e}")
            return False
        finally:
            conn.close()