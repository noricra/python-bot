import psycopg2
import psycopg2.extras
from typing import Optional, Dict, List

from app.core.db_pool import get_connection
from app.core.db_pool import put_connection


class OrderRepository:
    def __init__(self) -> None:
        pass

    def insert_order(self, order: Dict) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                INSERT INTO orders
                (order_id, buyer_user_id, product_id, seller_user_id, product_title, product_price_usd,
                 seller_revenue_usd, platform_commission_usd, payment_currency, payment_status,
                 nowpayments_id, payment_id, payment_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
                ''',
                (
                    order['order_id'],
                    order['buyer_user_id'],
                    order['product_id'],
                    order['seller_user_id'],
                    order.get('product_title', ''),
                    order.get('product_price_usd', order.get('product_price_eur', 0)),
                    order.get('seller_revenue_usd', order.get('seller_revenue', 0)),
                    order.get('platform_commission_usd', 0),
                    order.get('payment_currency', order.get('crypto_currency')),
                    order.get('payment_status', 'pending'),
                    order.get('nowpayments_id'),
                    order.get('payment_id'),
                    order.get('payment_address'),
                ),
            )
            conn.commit()
            return True
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT * FROM orders WHERE order_id = %s', (order_id,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            put_connection(conn)

    def update_payment_status(self, order_id: str, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # Mettre à jour le statut
            cursor.execute(
                'UPDATE orders SET payment_status = %s WHERE order_id = %s',
                (status, order_id)
            )

            # Si paiement complété, incrémenter sales_count et total_revenue
            if status == 'completed':
                # Récupérer product_id, seller_user_id et prix
                cursor.execute(
                    'SELECT product_id, seller_user_id, product_price_usd FROM orders WHERE order_id = %s',
                    (order_id,)
                )
                row = cursor.fetchone()
                if row:
                    product_id = row['product_id']
                    seller_user_id = row['seller_user_id']
                    product_price = row['product_price_usd']

                    # Incrémenter sales_count du produit
                    cursor.execute(
                        'UPDATE products SET sales_count = sales_count + 1 WHERE product_id = %s',
                        (product_id,)
                    )

                    # Incrémenter total_sales et total_revenue du vendeur
                    cursor.execute(
                        'UPDATE users SET total_sales = total_sales + 1, total_revenue = total_revenue + %s WHERE user_id = %s',
                        (product_price, seller_user_id)
                    )

            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def get_orders_by_buyer(self, buyer_user_id: int) -> List[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'SELECT * FROM orders WHERE buyer_user_id = %s ORDER BY created_at DESC',
                (buyer_user_id,)
            )
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def get_orders_by_seller(self, seller_user_id: int) -> List[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'SELECT * FROM orders WHERE seller_user_id = %s ORDER BY created_at DESC',
                (seller_user_id,)
            )
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def check_user_purchased_product(self, buyer_user_id: int, product_id: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'SELECT COUNT(*) as count FROM orders WHERE buyer_user_id = %s AND product_id = %s AND payment_status = %s',
                (buyer_user_id, product_id, 'completed')
            )
            count = cursor.fetchone()['count']
            return count > 0
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def increment_download_count(self, product_id: str, buyer_user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'UPDATE orders SET download_count = download_count + 1 WHERE product_id = %s AND buyer_user_id = %s',
                (product_id, buyer_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def create_order(self, order: Dict) -> bool:
        """Alias for insert_order to maintain compatibility"""
        return self.insert_order(order)

    def count_orders(self) -> int:
          conn = get_connection()
          cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
          try:
              cursor.execute('SELECT COUNT(*) as count FROM orders')
              return cursor.fetchone()['count']
          except psycopg2.Error:
              return 0
          finally:
              put_connection(conn)

    def get_total_revenue(self) -> float:
          """Get total revenue from all completed orders (seller revenue only)"""
          conn = get_connection()
          cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
          try:
              cursor.execute('SELECT SUM(seller_revenue_usd) as total FROM orders WHERE payment_status = %s', ('completed',))
              result = cursor.fetchone()['total']
              return result if result else 0.0
          except psycopg2.Error:
              return 0.0
          finally:
              put_connection(conn)


