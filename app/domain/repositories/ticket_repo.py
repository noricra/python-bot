import psycopg2
import psycopg2.extras
from typing import Optional, Dict, List

from app.core.database_init import get_postgresql_connection


class SupportTicketRepository:
    def __init__(self) -> None:
        pass

    def create_ticket(self, user_id: int, ticket_id: str, subject: str, message: str, client_email: str = None) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'INSERT INTO support_tickets (user_id, ticket_id, subject, message, client_email) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING',
                (user_id, ticket_id, subject, message, client_email),
            )
            conn.commit()
            return True
        except psycopg2.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict]:
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # Include tickets where user is creator OR seller (recipient)
            cursor.execute(
                '''SELECT * FROM support_tickets
                   WHERE user_id = %s OR seller_user_id = %s
                   ORDER BY created_at DESC LIMIT %s''',
                (user_id, user_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]
        except psycopg2.Error:
            return []
        finally:
            conn.close()

