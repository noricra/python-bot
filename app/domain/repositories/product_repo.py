import psycopg2
import psycopg2.extras
import logging
from typing import Optional, Dict, List, Tuple

from app.core.db_pool import get_connection, put_connection

logger = logging.getLogger(__name__)


class ProductRepository:
    def __init__(self) -> None:
        pass

    def insert_product(self, product: Dict) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                INSERT INTO products
                (product_id, seller_user_id, title, description, category, price_usd, main_file_url, file_size_mb, cover_image_url, thumbnail_url, preview_url, status, sales_count, rating, reviews_count, imported_rating, imported_reviews_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    product['product_id'],
                    product['seller_user_id'],
                    product['title'],
                    product.get('description'),
                    product.get('category'),
                    product.get('price_usd', product.get('price_eur', 0)),  # fallback to price_eur if needed
                    product.get('main_file_url'),
                    product.get('file_size_mb'),
                    product.get('cover_image_url'),
                    product.get('thumbnail_url'),
                    product.get('preview_url'),  # URL aperçu PDF généré côté client
                    product.get('status', 'active'),
                    product.get('sales_count', 0),
                    product.get('rating', 0),
                    product.get('reviews_count', 0),
                    product.get('imported_rating', 0),
                    product.get('imported_reviews_count', 0),
                ),
            )

            # Update category product count
            category = product.get('category')
            if category:
                cursor.execute(
                    'UPDATE categories SET products_count = products_count + 1 WHERE name = %s',
                    (category,)
                )
                # If category doesn't exist, create it
                if cursor.rowcount == 0:
                    cursor.execute(
                        'INSERT INTO categories (name, products_count) VALUES (%s, 1) ON CONFLICT DO NOTHING',
                        (category,)
                    )

            conn.commit()
            return True
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # Join with users table to get seller info
            cursor.execute('''
                SELECT p.*, u.seller_name, u.seller_bio
                FROM products p
                LEFT JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = %s
            ''', (product_id,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            put_connection(conn)

    def get_product_with_seller_info(self, product_id: str) -> Optional[Dict]:
        """Récupère un produit avec les informations du vendeur"""
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cursor.execute(
                '''
                SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = %s AND p.status = 'active'
                ''', (product_id,))

            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error as e:
            logger.error(f"Erreur récupération produit avec seller: {e}")
            return None
        finally:
            put_connection(conn)

    def increment_views(self, product_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'UPDATE products SET views_count = views_count + 1 WHERE product_id = %s',
                (product_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def update_status(self, product_id: str, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'UPDATE products SET status = %s WHERE product_id = %s',
                (status, product_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def delete_product(self, product_id: str, seller_user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # DEBUG: Check what exists
            cursor.execute('SELECT seller_user_id, title FROM products WHERE product_id = %s', (product_id,))
            check = cursor.fetchone()
            if check:
                logger.info(f"🔍 DELETE CHECK: Product {product_id} exists, seller_id={check['seller_user_id']}, trying to delete with seller_id={seller_user_id}")
            else:
                logger.warning(f"❌ DELETE CHECK: Product {product_id} NOT FOUND in database")

            # Get category before deletion to update count
            cursor.execute('SELECT category FROM products WHERE product_id = %s AND seller_user_id = %s', (product_id, seller_user_id))
            result = cursor.fetchone()
            category = result['category'] if result else None

            if not category:
                logger.warning(f"❌ DELETE FAILED: Product {product_id} not found for seller {seller_user_id} (ownership mismatch or product doesn't exist)")

            cursor.execute(
                'DELETE FROM products WHERE product_id = %s AND seller_user_id = %s',
                (product_id, seller_user_id)
            )

            deleted_count = cursor.rowcount
            logger.info(f"🗑️ DELETE RESULT: Deleted {deleted_count} rows for product {product_id}")

            # Update category product count if deletion was successful
            if deleted_count > 0 and category:
                cursor.execute(
                    'UPDATE categories SET products_count = CASE WHEN products_count > 0 THEN products_count - 1 ELSE 0 END WHERE name = %s',
                    (category,)
                )

            conn.commit()
            return deleted_count > 0
        except psycopg2.Error as e:
            logger.error(f"❌ DELETE ERROR: {e}")
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def get_products_by_seller(self, seller_user_id: int, limit: int = None, offset: int = 0) -> List[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            if limit is not None:
                cursor.execute(
                    '''
                    SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
                    FROM products p
                    LEFT JOIN users u ON p.seller_user_id = u.user_id
                    WHERE p.seller_user_id = %s
                    ORDER BY p.created_at DESC
                    LIMIT %s OFFSET %s
                    ''',
                    (seller_user_id, limit, offset)
                )
            else:
                cursor.execute(
                    '''
                    SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
                    FROM products p
                    LEFT JOIN users u ON p.seller_user_id = u.user_id
                    WHERE p.seller_user_id = %s
                    ORDER BY p.created_at DESC
                    ''',
                    (seller_user_id,)
                )
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def count_products_by_seller(self, seller_user_id: int) -> int:
        """Count total products by seller"""
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                "SELECT COUNT(*) as count FROM products WHERE seller_user_id = %s",
                (seller_user_id,)
            )
            return cursor.fetchone()['count']
        except psycopg2.Error:
            return 0
        finally:
            put_connection(conn)

    def get_products_by_category(self, category: str, limit: int = 10, offset: int = 0) -> List[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
                FROM products p
                LEFT JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.category = %s AND p.status = 'active'
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
                ''',
                (category, limit, offset)
            )
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def count_products_by_category(self, category: str) -> int:
        """Count total products in a category"""
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                "SELECT COUNT(*) as count FROM products WHERE category = %s AND status = 'active'",
                (category,)
            )
            return cursor.fetchone()['count']
        except psycopg2.Error:
            return 0
        finally:
            put_connection(conn)

    def update_price(self, product_id: str, seller_user_id: int, price_usd: float) -> bool:
        """Update product price (USDT only, EUR shown in UI)"""
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                UPDATE products SET price_usd = %s, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s AND seller_user_id = %s
                ''',
                (price_usd, product_id, seller_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def update_title(self, product_id: str, seller_user_id: int, title: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                UPDATE products SET title = %s, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s AND seller_user_id = %s
                ''',
                (title, product_id, seller_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def update_description(self, product_id: str, seller_user_id: int, description: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                UPDATE products SET description = %s, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s AND seller_user_id = %s
                ''',
                (description, product_id, seller_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def update_product_file_url(self, product_id: str, file_url: str) -> bool:
        """Update product's main file URL after B2 upload"""
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'UPDATE products SET main_file_url = %s WHERE product_id = %s',
                (file_url, product_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error as e:
            logger.error(f"Error updating product file URL: {e}")
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def get_all_products(self, limit: int = 100):
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("SELECT * FROM products ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def count_products(self) -> int:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("SELECT COUNT(*) as count FROM products")
            return cursor.fetchone()['count']
        except psycopg2.Error:
            return 0
        finally:
            put_connection(conn)

    def search_products(self, query: str, limit: int = 10):
        """
        Recherche full-text dans titre + description des produits

        Args:
            query: Texte de recherche
            limit: Nombre max de résultats

        Returns:
            Liste de produits correspondants
        """
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            search_pattern = f'%{query}%'
            cursor.execute('''
                SELECT * FROM products
                WHERE (title LIKE %s OR description LIKE %s)
                  AND status = 'active'
                ORDER BY sales_count DESC, created_at DESC
                LIMIT %s
            ''', (search_pattern, search_pattern, limit))
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error as e:
            import logging
            logging.error(f"Search error: {e}")
            return []
        finally:
            put_connection(conn)

    def create_product(self, product_data: Dict) -> Optional[str]:
        """Create a new product with auto-generated ID or use existing one"""
        from app.core.utils import generate_product_id

        # ✅ Utiliser product_id existant si fourni (miniapp), sinon générer (chat)
        product_id = product_data.get('product_id') or generate_product_id()

        # Ensure we have all required fields
        product = {
            'product_id': product_id,
            'seller_user_id': product_data.get('seller_id'),
            'title': product_data.get('title'),
            'description': product_data.get('description', ''),
            'category': product_data.get('category', 'General'),
            'price_usd': product_data.get('price_usd', product_data.get('price_eur', 0)),  # USDT only
            'main_file_url': product_data.get('main_file_url'),  # ✅ Utiliser URL fournie (miniapp) ou None (chat)
            'file_size_mb': round(product_data.get('file_size', 0) / (1024 * 1024), 2),
            'cover_image_url': product_data.get('cover_image_url'),
            'thumbnail_url': product_data.get('thumbnail_url'),
            'preview_url': product_data.get('preview_url'),  # PDF preview généré côté client
            'status': 'active',
            'sales_count': product_data.get('sales_count', 0),
            'rating': product_data.get('rating', 0),
            'reviews_count': product_data.get('reviews_count', 0),
            'imported_rating': product_data.get('rating', 0) if product_data.get('imported_from') else 0,
            'imported_reviews_count': product_data.get('reviews_count', 0) if product_data.get('imported_from') else 0,
        }

        if self.insert_product(product):
            return product_id
        else:
            return None

    def recalculate_category_counts(self) -> bool:
        """Recalcule tous les comptages de produits par catégorie"""
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
                INSERT INTO categories (name, products_count)
                SELECT DISTINCT category, COUNT(*)
                FROM products
                WHERE status = 'active' AND category IS NOT NULL
                AND category NOT IN (SELECT name FROM categories)
                GROUP BY category
            ''')

            conn.commit()
            logger.info("Category counts recalculated successfully")
            return True
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error recalculating category counts: {e}")
            return False
        finally:
            put_connection(conn)

    def create_product_from_import(
        self,
        product_id: str,
        seller_id: int,
        title: str,
        description: str,
        price_usd: float,
        cover_image_url: Optional[str],
        imported_from: str,
        imported_url: Optional[str],
        source_profile: str
    ) -> str:
        """
        Creer produit depuis import externe (Gumroad, etc.)

        Produit cree en status='draft' car fichiers manquants

        Args:
            product_id: ID genere
            seller_id: User ID vendeur
            title: Titre produit
            description: Description
            price_usd: Prix USD
            cover_image_url: URL image R2 (peut etre None)
            imported_from: Source ('gumroad', 'shopify', etc.)
            imported_url: URL produit original
            source_profile: URL profil source

        Returns:
            product_id cree

        Raises:
            Exception: Si insertion echoue
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO products (
                    product_id, seller_user_id, title, description,
                    price_usd, cover_image_url, status,
                    imported_from, imported_url, source_profile,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (
                product_id, seller_id, title, description,
                price_usd, cover_image_url, 'draft',
                imported_from, imported_url, source_profile
            ))

            conn.commit()
            logger.info(f"Product imported: {product_id} from {imported_from}")

            return product_id

        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Error creating imported product: {e}")
            raise Exception(f"Failed to create imported product: {e}")
        finally:
            put_connection(conn)
