import psycopg2
import psycopg2.extras
from typing import Optional, List, Tuple

from app.core.database_init import get_postgresql_connection


class PayoutRepository:
    def __init__(self) -> None:
        pass

    def insert_payout(self, seller_user_id: int, order_ids: List[str], total_amount_sol: float) -> Optional[int]:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            import json
            cursor.execute(
                '''
                INSERT INTO seller_payouts (seller_user_id, order_ids, total_amount_sol, payout_status)
                VALUES (?, ?, ?, 'pending')
                ON CONFLICT DO NOTHING
                ''',
                (seller_user_id, json.dumps(order_ids), total_amount_sol),
            )
            payout_id = cursor.lastrowid
            conn.commit()
            return payout_id
        except psycopg2.Error:
            conn.rollback()
            return None
        finally:
            conn.close()

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
            conn.close()

    def list_recent_for_seller(self, seller_user_id: int, limit: int = 10) -> List[Tuple]:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                SELECT id, total_amount_sol, payout_status, created_at, processed_at
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
            conn.close()

    def get_pending_payouts(self, limit: int = 20) -> List[dict]:
        """Get pending payouts for admin"""
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                SELECT seller_user_id as user_id, total_amount_sol as amount, payout_status
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
            conn.close()

    def get_all_payouts(self, limit: int = 50) -> List[dict]:
        """Get all payouts for export"""
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                SELECT seller_user_id as user_id, total_amount_sol as amount, payout_status as status
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
            conn.close()

