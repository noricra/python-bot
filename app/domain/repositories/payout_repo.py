import sqlite3
from typing import Optional, List, Tuple

from app.core import get_sqlite_connection, settings as core_settings


class PayoutRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def insert_payout(self, seller_user_id: int, order_ids: List[str], total_amount_sol: float) -> Optional[int]:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            import json
            cursor.execute(
                '''
                INSERT INTO seller_payouts (seller_user_id, order_ids, total_amount_sol, payout_status)
                VALUES (?, ?, ?, 'pending')
                ''',
                (seller_user_id, json.dumps(order_ids), total_amount_sol),
            )
            payout_id = cursor.lastrowid
            conn.commit()
            return payout_id
        except sqlite3.Error:
            conn.rollback()
            return None
        finally:
            conn.close()

    def mark_all_pending_as_completed(self) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                UPDATE seller_payouts SET payout_status = 'completed', processed_at = CURRENT_TIMESTAMP
                WHERE payout_status = 'pending'
                '''
            )
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_recent_for_seller(self, seller_user_id: int, limit: int = 10) -> List[Tuple]:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                SELECT id, total_amount_sol, payout_status, created_at, processed_at
                FROM seller_payouts
                WHERE seller_user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                (seller_user_id, limit),
            )
            return cursor.fetchall()
        except sqlite3.Error:
            return []
        finally:
            conn.close()

