"""Review Repository - Handles review data access"""

import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional
from app.core.utils import logger
from app.core.database_init import get_postgresql_connection


class ReviewRepository:
    """Repository for managing product reviews"""

    def __init__(self):
        pass

    def _get_connection(self):
        """Create database connection"""
        return get_postgresql_connection()

    def get_product_reviews(self, product_id: str, limit: int = 5, offset: int = 0) -> List[Dict]:
        """
        Get paginated reviews for a product

        Args:
            product_id: Product ID
            limit: Number of reviews per page (default 5)
            offset: Offset for pagination

        Returns:
            List of review dicts with buyer info
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            query = '''
                SELECT
                    r.review_id,
                    r.product_id,
                    r.buyer_user_id,
                    r.order_id,
                    r.rating,
                    r.comment,
                    r.review_text,
                    r.created_at,
                    r.updated_at,
                    u.first_name,
                    u.username
                FROM reviews r
                LEFT JOIN users u ON r.buyer_user_id = u.user_id
                WHERE r.product_id = %s
                ORDER BY r.created_at DESC
                LIMIT %s OFFSET %s
            '''

            cursor.execute(query, (product_id, limit, offset))
            rows = cursor.fetchall()
            conn.close()

            reviews = []
            for row in rows:
                reviews.append({
                    'id': row['review_id'],
                    'product_id': row['product_id'],
                    'buyer_user_id': row['buyer_user_id'],
                    'order_id': row['order_id'],
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'review_text': row['review_text'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'buyer_first_name': row['first_name'],
                    'buyer_username': row['username']
                })

            return reviews

        except psycopg2.Error as e:
            logger.error(f"Error getting product reviews: {e}")
            return []

    def get_review_count(self, product_id: str) -> int:
        """Get total number of reviews for a product"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('SELECT COUNT(*) as count FROM reviews WHERE product_id = %s', (product_id,))
            count = cursor.fetchone()['count']
            conn.close()

            return count

        except psycopg2.Error as e:
            logger.error(f"Error getting review count: {e}")
            return 0

    def get_product_rating_summary(self, product_id: str) -> Dict:
        """
        Get rating summary for a product

        Returns:
            Dict with average_rating, total_reviews, rating_distribution
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Get average and count
            cursor.execute('''
                SELECT AVG(rating), COUNT(*)
                FROM reviews
                WHERE product_id = %s
            ''', (product_id,))

            avg_rating, total = cursor.fetchone()
            avg_rating = avg_rating if avg_rating else 0.0
            total = total if total else 0

            # Get rating distribution (1-5 stars)
            distribution = {}
            for stars in range(1, 6):
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM reviews
                    WHERE product_id = %s AND rating = %s
                ''', (product_id, stars))

                count = cursor.fetchone()['count']
                distribution[stars] = count

            conn.close()

            return {
                'average_rating': round(avg_rating, 1),
                'total_reviews': total,
                'rating_distribution': distribution
            }

        except psycopg2.Error as e:
            logger.error(f"Error getting rating summary: {e}")
            return {
                'average_rating': 0.0,
                'total_reviews': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }

    def add_review(self, product_id: str, buyer_user_id: int, order_id: str,
                   rating: int, comment: str = None, review_text: str = None) -> bool:
        """
        Add a new review for a product

        Args:
            product_id: Product ID
            buyer_user_id: Buyer's user ID
            order_id: Order ID
            rating: Rating 1-5
            comment: Short comment
            review_text: Detailed review text

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('''
                INSERT INTO reviews
                (product_id, buyer_user_id, order_id, rating, comment, review_text)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
            ''', (product_id, buyer_user_id, order_id, rating, comment, review_text))

            conn.commit()
            conn.close()

            logger.info(f"✅ Review added: product={product_id}, buyer={buyer_user_id}, rating={rating}")
            return True

        except psycopg2.IntegrityError:
            logger.warning(f"Review already exists for buyer {buyer_user_id} on product {product_id}")
            return False
        except psycopg2.Error as e:
            logger.error(f"Error adding review: {e}")
            return False

    def has_user_reviewed(self, product_id: str, buyer_user_id: int) -> bool:
        """Check if user has already reviewed this product"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('''
                SELECT COUNT(*) as count
                FROM reviews
                WHERE product_id = %s AND buyer_user_id = %s
            ''', (product_id, buyer_user_id))

            count = cursor.fetchone()['count']
            conn.close()

            return count > 0

        except psycopg2.Error as e:
            logger.error(f"Error checking review existence: {e}")
            return False
