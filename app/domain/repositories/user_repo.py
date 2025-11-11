import psycopg2
import psycopg2.extras
from typing import Optional, Dict

from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection


class UserRepository:
    def __init__(self) -> None:
        pass

    def add_user(self, user_id: int, username: str, first_name: str, language_code: str = 'fr') -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                '''
                INSERT INTO users
                (user_id, username, first_name, language_code)
                VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
                ''',
                (user_id, username, first_name, language_code),
            )
            conn.commit()
            return True
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def get_user(self, user_id: int) -> Optional[Dict]:
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            put_connection(conn)

    def update_seller_name(self, user_id: int, seller_name: str) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE users SET seller_name = %s WHERE user_id = %s', (seller_name, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def update_seller_bio(self, user_id: int, seller_bio: str) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE users SET seller_bio = %s WHERE user_id = %s', (seller_bio, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def update_seller_email(self, user_id: int, email: str) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE users SET email = %s WHERE user_id = %s', (email, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def update_seller_solana_address(self, user_id: int, seller_solana_address: str) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE users SET seller_solana_address = %s WHERE user_id = %s', (seller_solana_address, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def update_user_language(self, user_id: int, language_code: str) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE users SET language_code = %s WHERE user_id = %s', (language_code, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def delete_seller_account(self, user_id: int) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE users SET is_seller = FALSE, seller_name = NULL, seller_bio = NULL WHERE user_id = %s', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            put_connection(conn)

    def get_all_users(self, limit: int = 100):
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT * FROM users ORDER BY registration_date DESC LIMIT %s', (limit,))
            rows = cursor.fetchall()
            return [row for row in rows]
        except psycopg2.Error:
            return []
        finally:
            put_connection(conn)

    def count_users(self) -> int:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT COUNT(*) as count FROM users')
            return cursor.fetchone()['count']
        except psycopg2.Error:
            return 0
        finally:
            put_connection(conn)

    def count_sellers(self) -> int:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_seller = TRUE')
            return cursor.fetchone()['count']
        except psycopg2.Error:
            return 0
        finally:
            put_connection(conn)

    # get_user_by_partner_code removed - referral system deleted


    def get_user_by_email(self, email: str):
        conn = get_postgresql_connection()
        # PostgreSQL uses RealDictCursor
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cursor.fetchone()
            return row if row else None
        except psycopg2.Error:
            return None
        finally:
            put_connection(conn)

    def suspend_user(self, user_id: int, reason: str, days: int = None) -> bool:
        """Suspend a user account"""
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        try:
            if days:
                # Temporary suspension
                cursor.execute('''
                    UPDATE users
                    SET is_suspended = TRUE,
                        suspension_reason = %s,
                        suspended_at = CURRENT_TIMESTAMP,
                        suspended_until = CURRENT_TIMESTAMP + INTERVAL '%s days'
                    WHERE user_id = %s
                ''', (reason, days, user_id))
            else:
                # Permanent suspension
                cursor.execute('''
                    UPDATE users
                    SET is_suspended = TRUE,
                        suspension_reason = %s,
                        suspended_at = CURRENT_TIMESTAMP,
                        suspended_until = NULL
                    WHERE user_id = %s
                ''', (reason, user_id))

            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error suspending user: {e}")
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def restore_user(self, user_id: int) -> bool:
        """Restore a suspended user account"""
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE users
                SET is_suspended = FALSE,
                    suspension_reason = NULL,
                    suspended_at = NULL,
                    suspended_until = NULL
                WHERE user_id = %s
            ''', (user_id,))

            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error restoring user: {e}")
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    # Recovery code system removed - no longer needed (no password system)

