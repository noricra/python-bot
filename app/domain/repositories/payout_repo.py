import psycopg2
import psycopg2.extras
from typing import Optional, List, Tuple

from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection


class PayoutRepository:
    def __init__(self) -> None:
        pass

    def insert_payout(self, seller_user_id: int, order_ids: List[str], total_amount_usdt: float,
                     seller_wallet_address: str, payment_currency: str = 'USDT') -> Optional[int]:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            import json
            cursor.execute(
                '''
                INSERT INTO seller_payouts (seller_user_id, order_ids, total_amount_usdt,
                                           seller_wallet_address, payment_currency, payout_status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
                RETURNING id
                ''',
                (seller_user_id, json.dumps(order_ids), total_amount_usdt, seller_wallet_address, payment_currency),
            )
            result = cursor.fetchone()
            payout_id = result['id'] if result else None
            conn.commit()
            return payout_id
        except psycopg2.Error as e:
            import logging
            logging.getLogger(__name__).error(f"Error inserting payout: {e}")
            conn.rollback()
            return None
        finally:
            put_connection(conn)

    def mark_all_pending_as_completed(self) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                UPDATE seller_payouts SET payout_status = 'completed', processed_at = CURRENT_TIMESTAMP
                WHERE payout_status = 'pending'
                '''
            )
            conn.commit()
            return True
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def list_recent_for_seller(self, seller_user_id: int, limit: int = 10) -> List[Tuple]:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                SELECT id, total_amount_usdt, payout_status, seller_wallet_address,
                       payment_currency, created_at, processed_at
                FROM seller_payouts
                WHERE seller_user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (seller_user_id, limit),
            )
            return cursor.fetchall()
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def get_pending_payouts(self, limit: int = 20) -> List[dict]:
        """Get pending payouts for admin with full details"""
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                SELECT id, seller_user_id as user_id, total_amount_usdt as amount,
                       seller_wallet_address, payment_currency, order_ids,
                       payout_status, created_at
                FROM seller_payouts
                WHERE payout_status = 'pending'
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (limit,)
            )
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def get_all_payouts(self, limit: int = 50) -> List[dict]:
        """Get all payouts for export"""
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                SELECT seller_user_id as user_id, total_amount_usdt as amount, payout_status as status,
                       seller_wallet_address, payment_currency
                FROM seller_payouts
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (limit,)
            )
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def mark_payout_completed(self, payout_id: int) -> bool:
        """Mark a specific payout as completed"""
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                UPDATE seller_payouts SET payout_status = 'completed', processed_at = CURRENT_TIMESTAMP
                WHERE id = %s AND payout_status = 'pending'
                ''',
                (payout_id,)
            )
            conn.commit()
            return True
        except psycopg2.Error as e:
            import logging
            logging.getLogger(__name__).error(f"Error marking payout {payout_id} as completed: {e}")
            conn.rollback()
            return False
        finally:
            put_connection(conn)

