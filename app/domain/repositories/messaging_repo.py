import psycopg2
import psycopg2.extras
from typing import Optional, List, Dict

from app.core.db_pool import get_connection
from app.core.db_pool import put_connection
from app.core import settings as core_settings


class MessagingRepository:
    def __init__(self) -> None:
        pass

    # Tickets
    def get_or_create_ticket(self, buyer_user_id: int, order_id: str, seller_user_id: int, subject: str) -> Optional[str]:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'SELECT ticket_id FROM support_tickets WHERE user_id = %s AND order_id = %s AND seller_user_id = %s AND status IN (%s,%s,%s)',
                (buyer_user_id, order_id, seller_user_id, 'open', 'pending_user', 'pending_admin')
            )
            row = cursor.fetchone()
            if row:
                return row['ticket_id']
            from app.core.utils import generate_ticket_id
            ticket_id = generate_ticket_id()
            cursor.execute(
                'INSERT INTO support_tickets (user_id, ticket_id, subject, message, status, order_id, seller_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (buyer_user_id, ticket_id, subject[:100], '', 'open', order_id, seller_user_id)
            )
            conn.commit()
            return ticket_id
        except psycopg2.Error:
            conn.rollback()
            return None
        finally:
            put_connection(conn)

    def set_ticket_status(self, ticket_id: str, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE support_tickets SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s', (status, ticket_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    # Messages
    def insert_message(self, ticket_id: str, sender_user_id: int, sender_role: str, message: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'INSERT INTO support_messages (ticket_id, sender_user_id, sender_role, message) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING',
                (ticket_id, sender_user_id, sender_role, message[:2000])
            )
            cursor.execute('UPDATE support_tickets SET updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s', (ticket_id,))
            conn.commit()
            return True
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def list_messages(self, ticket_id: str, limit: int = 10) -> List[Dict]:
        conn = get_connection()
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
            put_connection(conn)

    def get_ticket_participants(self, ticket_id: str) -> Optional[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT user_id, seller_user_id, status FROM support_tickets WHERE ticket_id = %s', (ticket_id,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            put_connection(conn)

    def escalate_ticket(self, ticket_id: str, admin_user_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE support_tickets SET assigned_to_user_id = %s, status = %s, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s', (admin_user_id, 'pending_admin', ticket_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def list_recent_tickets(self, limit: int = 10) -> List[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT ticket_id, user_id, seller_user_id, subject, status, updated_at FROM support_tickets ORDER BY updated_at DESC LIMIT %s', (limit,))
            return [dict(r) for r in cursor.fetchall()]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def get_ticket(self, ticket_id: str) -> Optional[Dict]:
        conn = get_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT * FROM support_tickets WHERE ticket_id = %s', (ticket_id,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            put_connection(conn)
