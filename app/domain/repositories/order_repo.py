import sqlite3
from typing import Optional, Dict

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
                (order_id, buyer_user_id, product_id, seller_user_id, product_price_eur, platform_commission, seller_revenue, partner_commission, crypto_currency, crypto_amount, payment_status, nowpayments_id, payment_address, partner_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    order['order_id'],
                    order['buyer_user_id'],
                    order['product_id'],
                    order['seller_user_id'],
                    order['product_price_eur'],
                    order['platform_commission'],
                    order['seller_revenue'],
                    order.get('partner_commission', 0.0),
                    order['crypto_currency'],
                    order['crypto_amount'],
                    order.get('payment_status', 'pending'),
                    order.get('nowpayments_id'),
                    order.get('payment_address'),
                    order.get('partner_code'),
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

