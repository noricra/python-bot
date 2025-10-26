import sqlite3
from typing import Optional, Dict, List

from app.core import get_sqlite_connection, settings as core_settings


class OrderRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def insert_order(self, order: Dict) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO orders
                (order_id, buyer_user_id, product_id, seller_user_id, product_title, product_price_eur, seller_revenue, crypto_currency, crypto_amount, payment_status, nowpayments_id, payment_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    order['order_id'],
                    order['buyer_user_id'],
                    order['product_id'],
                    order['seller_user_id'],
                    order.get('product_title', ''),
                    order['product_price_eur'],
                    order['seller_revenue'],
                    order.get('crypto_currency'),
                    order.get('crypto_amount'),
                    order.get('payment_status', 'pending'),
                    order.get('nowpayments_id'),
                    order.get('payment_address'),
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def update_payment_status(self, order_id: str, status: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            # Mettre à jour le statut
            cursor.execute(
                'UPDATE orders SET payment_status = ? WHERE order_id = ?',
                (status, order_id)
            )

            # Si paiement complété, incrémenter sales_count et total_revenue
            if status == 'completed':
                # Récupérer product_id, seller_user_id et prix
                cursor.execute(
                    'SELECT product_id, seller_user_id, product_price_eur FROM orders WHERE order_id = ?',
                    (order_id,)
                )
                row = cursor.fetchone()
                if row:
                    product_id, seller_user_id, product_price = row

                    # Incrémenter sales_count du produit
                    cursor.execute(
                        'UPDATE products SET sales_count = sales_count + 1 WHERE product_id = ?',
                        (product_id,)
                    )

                    # Incrémenter total_sales et total_revenue du vendeur
                    cursor.execute(
                        'UPDATE users SET total_sales = total_sales + 1, total_revenue = total_revenue + ? WHERE user_id = ?',
                        (product_price, seller_user_id)
                    )

            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_orders_by_buyer(self, buyer_user_id: int) -> List[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT * FROM orders WHERE buyer_user_id = ? ORDER BY created_at DESC',
                (buyer_user_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def get_orders_by_seller(self, seller_user_id: int) -> List[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT * FROM orders WHERE seller_user_id = ? ORDER BY created_at DESC',
                (seller_user_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def check_user_purchased_product(self, buyer_user_id: int, product_id: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM orders WHERE buyer_user_id = ? AND product_id = ? AND payment_status = "completed"',
                (buyer_user_id, product_id)
            )
            count = cursor.fetchone()[0]
            return count > 0
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def increment_download_count(self, product_id: str, buyer_user_id: int) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE orders SET download_count = download_count + 1 WHERE product_id = ? AND buyer_user_id = ?',
                (product_id, buyer_user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def create_order(self, order: Dict) -> bool:
        """Alias for insert_order to maintain compatibility"""
        return self.insert_order(order)

    def count_orders(self) -> int:
          conn = get_sqlite_connection(self.database_path)
          cursor = conn.cursor()
          try:
              cursor.execute('SELECT COUNT(*) FROM orders')
              return cursor.fetchone()[0]
          except sqlite3.Error:
              return 0
          finally:
              conn.close()

    def get_total_revenue(self) -> float:
          conn = get_sqlite_connection(self.database_path)
          cursor = conn.cursor()
          try:
              cursor.execute('SELECT SUM(seller_revenue) FROM orders WHERE payment_status = "completed"')
              result = cursor.fetchone()[0]
              return result if result else 0.0
          except sqlite3.Error:
              return 0.0
          finally:
              conn.close()


