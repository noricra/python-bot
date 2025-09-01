import sqlite3
from typing import Optional, List, Dict

from app.core import get_sqlite_connection, settings as core_settings


class MessagingRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    # Tickets
    def get_or_create_ticket(self, buyer_user_id: int, order_id: str, seller_user_id: int, subject: str) -> Optional[str]:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT ticket_id FROM support_tickets WHERE user_id = ? AND order_id = ? AND seller_user_id = ? AND status IN ("open","pending_user","pending_admin")',
                (buyer_user_id, order_id, seller_user_id)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            ticket_id = f"TKT-{buyer_user_id}-{order_id}"
            cursor.execute(
                'INSERT INTO support_tickets (user_id, ticket_id, subject, message, status, order_id, seller_user_id) VALUES (?, ?, ?, ?, "open", ?, ?)',
                (buyer_user_id, ticket_id, subject[:100], '', order_id, seller_user_id)
            )
            conn.commit()
            return ticket_id
        except sqlite3.Error:
            conn.rollback()
            return None
        finally:
            conn.close()

    def set_ticket_status(self, ticket_id: str, status: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('UPDATE support_tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = ?', (status, ticket_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    # Messages
    def insert_message(self, ticket_id: str, sender_user_id: int, sender_role: str, message: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO support_messages (ticket_id, sender_user_id, sender_role, message) VALUES (?, ?, ?, ?)',
                (ticket_id, sender_user_id, sender_role, message[:2000])
            )
            cursor.execute('UPDATE support_tickets SET updated_at = CURRENT_TIMESTAMP WHERE ticket_id = ?', (ticket_id,))
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_messages(self, ticket_id: str, limit: int = 10) -> List[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT sender_user_id, sender_role, message, created_at FROM support_messages WHERE ticket_id = ? ORDER BY created_at DESC LIMIT ?',
                (ticket_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def get_ticket_participants(self, ticket_id: str) -> Optional[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT user_id, seller_user_id, status FROM support_tickets WHERE ticket_id = ?', (ticket_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()
