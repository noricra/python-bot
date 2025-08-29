"""
SQLite implementation of OrderRepositoryInterface.
"""

import sqlite3
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.entities import Order
from app.domain.entities.order import OrderStatus, PaymentMethod
from app.application.interfaces import OrderRepositoryInterface
from app.core import get_sqlite_connection, settings


class SqliteOrderRepository(OrderRepositoryInterface):
    """SQLite implementation of order repository."""
    
    def __init__(self, database_path: Optional[str] = None):
        self.database_path = database_path or settings.DATABASE_PATH
    
    async def create(self, order: Order) -> bool:
        """Create a new order."""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO orders
                (order_id, buyer_user_id, seller_user_id, product_id, amount_eur,
                 payment_method, status, nowpayments_payment_id, crypto_currency,
                 crypto_amount, payment_address, platform_commission_eur,
                 seller_payout_eur, referrer_commission_eur, referrer_user_id,
                 download_count, creation_date, payment_date, completion_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.order_id, order.buyer_user_id, order.seller_user_id,
                order.product_id, float(order.amount_eur), order.payment_method.value,
                order.status.value, order.nowpayments_payment_id, order.crypto_currency,
                float(order.crypto_amount) if order.crypto_amount else None,
                order.payment_address, 
                float(order.platform_commission_eur) if order.platform_commission_eur else None,
                float(order.seller_payout_eur) if order.seller_payout_eur else None,
                float(order.referrer_commission_eur) if order.referrer_commission_eur else None,
                order.referrer_user_id, order.download_count,
                order.creation_date, order.payment_date, order.completion_date
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error creating order: {e}")
            return False
        finally:
            conn.close()
    
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
            row = cursor.fetchone()
            if row:
                return Order(
                    order_id=row['order_id'],
                    buyer_user_id=row['buyer_user_id'],
                    seller_user_id=row['seller_user_id'],
                    product_id=row['product_id'],
                    amount_eur=Decimal(str(row['amount_eur'])),
                    payment_method=PaymentMethod(row['payment_method']),
                    status=OrderStatus(row['status']),
                    nowpayments_payment_id=row['nowpayments_payment_id'],
                    crypto_currency=row['crypto_currency'],
                    crypto_amount=Decimal(str(row['crypto_amount'])) if row['crypto_amount'] else None,
                    payment_address=row['payment_address'],
                    platform_commission_eur=Decimal(str(row['platform_commission_eur'])) if row['platform_commission_eur'] else None,
                    seller_payout_eur=Decimal(str(row['seller_payout_eur'])) if row['seller_payout_eur'] else None,
                    referrer_commission_eur=Decimal(str(row['referrer_commission_eur'])) if row['referrer_commission_eur'] else None,
                    referrer_user_id=row['referrer_user_id'],
                    download_count=row['download_count'] or 0,
                    creation_date=datetime.fromisoformat(row['creation_date']) if row['creation_date'] else None,
                    payment_date=datetime.fromisoformat(row['payment_date']) if row['payment_date'] else None,
                    completion_date=datetime.fromisoformat(row['completion_date']) if row['completion_date'] else None
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting order: {e}")
            return None
        finally:
            conn.close()
    
    async def get_by_buyer(self, buyer_id: int) -> List[Order]:
        """Get orders by buyer."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE buyer_user_id = ?', (buyer_id,))
            rows = cursor.fetchall()
            orders = []
            for row in rows:
                order = await self.get_by_id(row['order_id'])
                if order:
                    orders.append(order)
            return orders
        except sqlite3.Error as e:
            print(f"Error getting orders by buyer: {e}")
            return []
        finally:
            conn.close()
    
    async def get_by_seller(self, seller_id: int) -> List[Order]:
        """Get orders by seller."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE seller_user_id = ?', (seller_id,))
            rows = cursor.fetchall()
            orders = []
            for row in rows:
                order = await self.get_by_id(row['order_id'])
                if order:
                    orders.append(order)
            return orders
        except sqlite3.Error as e:
            print(f"Error getting orders by seller: {e}")
            return []
        finally:
            conn.close()
    
    async def get_by_product(self, product_id: str) -> List[Order]:
        """Get orders by product."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE product_id = ?', (product_id,))
            rows = cursor.fetchall()
            orders = []
            for row in rows:
                order = await self.get_by_id(row['order_id'])
                if order:
                    orders.append(order)
            return orders
        except sqlite3.Error as e:
            print(f"Error getting orders by product: {e}")
            return []
        finally:
            conn.close()
    
    async def get_by_payment_id(self, payment_id: str) -> Optional[Order]:
        """Get order by NOWPayments payment ID."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE nowpayments_payment_id = ?', (payment_id,))
            row = cursor.fetchone()
            if row:
                return await self.get_by_id(row['order_id'])
            return None
        except sqlite3.Error as e:
            print(f"Error getting order by payment ID: {e}")
            return None
        finally:
            conn.close()
    
    async def update(self, order: Order) -> bool:
        """Update order."""
        return await self.create(order)  # Use REPLACE behavior
    
    async def get_completed_orders_for_seller(self, seller_id: int) -> List[Order]:
        """Get completed orders for seller."""
        orders = await self.get_by_seller(seller_id)
        return [order for order in orders if order.is_completed]