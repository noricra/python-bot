import psycopg2
import psycopg2.extras
from typing import Optional, Dict

from app.core.database_init import get_postgresql_connection


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
                VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                ''',
                (user_id, username, first_name, language_code),
            )
            conn.commit()
            return True
        except psycopg2.Error:
            return False
        finally:
            conn.close()

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
            conn.close()

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
            conn.close()

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
            conn.close()

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
            conn.close()

    def delete_seller_account(self, user_id: int) -> bool:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('UPDATE users SET is_seller = 0, seller_name = NULL, seller_bio = NULL WHERE user_id = %s', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            conn.close()

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
            conn.close()

    def count_users(self) -> int:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT COUNT(*) FROM users')
            return cursor.fetchone()[0]
        except psycopg2.Error:
            return 0
        finally:
            conn.close()

    def count_sellers(self) -> int:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_seller = 1')
            return cursor.fetchone()[0]
        except psycopg2.Error:
            return 0
        finally:
            conn.close()

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
            conn.close()

    def set_recovery_code(self, email: str, code_hash: str, expiry_timestamp: int) -> bool:
        """Set recovery code hash and expiry for password recovery"""
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'UPDATE users SET recovery_code_hash = %s, recovery_code_expiry = %s WHERE email = %s',
                (code_hash, expiry_timestamp, email)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            conn.close()

    def validate_recovery_code(self, email: str, code_hash: str, current_timestamp: int) -> bool:
        """Validate recovery code with expiration check"""
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'SELECT user_id FROM users WHERE email = %s AND recovery_code_hash = %s AND recovery_code_expiry > %s',
                (email, code_hash, current_timestamp)
            )
            row = cursor.fetchone()
            return row is not None
        except psycopg2.Error:
            return False
        finally:
            conn.close()

    def update_password_by_email(self, email: str, password_salt: str, password_hash: str) -> bool:
        """Update password and clear recovery code after successful recovery"""
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(
                'UPDATE users SET password_salt = %s, password_hash = %s, recovery_code_hash = NULL WHERE email = %s',
                (password_salt, password_hash, email)
            )
            conn.commit()
            return cursor.rowcount > 0
        except psycopg2.Error:
            return False
        finally:
            conn.close()

