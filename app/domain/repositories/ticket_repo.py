import sqlite3
from typing import Optional, Dict, List

from app.core import get_sqlite_connection, settings as core_settings


class SupportTicketRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def create_ticket(self, user_id: int, ticket_id: str, subject: str, message: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO support_tickets (user_id, ticket_id, subject, message) VALUES (?, ?, ?, ?)',
                (user_id, ticket_id, subject, message),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            # Include tickets where user is creator OR seller (recipient)
            cursor.execute(
                '''SELECT * FROM support_tickets
                   WHERE user_id = ? OR seller_user_id = ?
                   ORDER BY created_at DESC LIMIT ?''',
                (user_id, user_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

