import psycopg2
import psycopg2.extras
from typing import Optional, List, Dict

from app.core.database_init import get_postgresql_connection, settings as core_settings


class MessagingRepository:
    def __init__(self) -> None:
        pass

    # Tickets
    def get_or_create_ticket(self, buyer_user_id: int, order_id: str, seller_user_id: int, subject: str) -> Optional[str]:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'SELECT ticket_id FROM support_tickets WHERE user_id = %s AND order_id = %s AND seller_user_id = %s AND status IN ("open","pending_user","pending_admin")',
                (buyer_user_id, order_id, seller_user_id)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            from app.core.utils import generate_ticket_id
            from app.core import settings as core_settings
            ticket_id = generate_ticket_id(core_settings.DATABASE_PATH)
            cursor.execute(
                'INSERT INTO support_tickets (user_id, ticket_id, subject, message, status, order_id, seller_user_id) VALUES (?, ?, ?, ?, "open", ?, ?)',
                (buyer_user_id, ticket_id, subject[:100], '', order_id, seller_user_id)
            )
            conn.commit()
            return ticket_id
        except psycopg2.Error:
            conn.rollback()
            return None
        finally:
            conn.close()

    def set_ticket_status(self, ticket_id: str, status: str) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE support_tickets SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s', (status, ticket_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    # Messages
    def insert_message(self, ticket_id: str, sender_user_id: int, sender_role: str, message: str) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'INSERT INTO support_messages (ticket_id, sender_user_id, sender_role, message) VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING',
                (ticket_id, sender_user_id, sender_role, message[:2000])
            )
            cursor.execute('UPDATE support_tickets SET updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s', (ticket_id,))
            conn.commit()
            return True
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_messages(self, ticket_id: str, limit: int = 10) -> List[Dict]:
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'SELECT sender_user_id, sender_role, message, created_at FROM support_messages WHERE ticket_id = %s ORDER BY created_at DESC LIMIT %s',
                (ticket_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except psycopg2.Error:
            return []
        finally:
            conn.close()

    def get_ticket_participants(self, ticket_id: str) -> Optional[Dict]:
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT user_id, seller_user_id, status FROM support_tickets WHERE ticket_id = %s', (ticket_id,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            conn.close()

    def escalate_ticket(self, ticket_id: str, admin_user_id: int) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE support_tickets SET assigned_to_user_id = %s, status = "pending_admin", updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s', (admin_user_id, ticket_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_recent_tickets(self, limit: int = 10) -> List[Dict]:
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT ticket_id, user_id, seller_user_id, subject, status, updated_at FROM support_tickets ORDER BY updated_at DESC LIMIT %s', (limit,))
            return [dict(r) for r in cursor.fetchall()]
        except psycopg2.Error:
            return []
        finally:
            conn.close()

    def get_ticket(self, ticket_id: str) -> Optional[Dict]:
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT * FROM support_tickets WHERE ticket_id = %s', (ticket_id,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            conn.close()
