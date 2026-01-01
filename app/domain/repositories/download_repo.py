"""
Download Repository
Gestion des tokens de telechargement et rate limiting
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import uuid

from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection


class DownloadRepository:
    """Repository pour gestion downloads et tokens"""

    @staticmethod
    def check_and_update_rate_limit(user_id: int, max_tokens: int = 10, window_seconds: int = 3600) -> Tuple[bool, Optional[str]]:
        """
        Verifie et met a jour le rate limit pour un user

        Returns:
            (is_allowed, error_message)
        """
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()
            current_time = datetime.now()

            cursor.execute('''
                SELECT tokens_generated_count, window_start
                FROM download_rate_limits
                WHERE user_id = %s
            ''', (user_id,))

            result = cursor.fetchone()

            if result:
                count, window_start = result
                # Check if window expired
                if (current_time - window_start).total_seconds() > window_seconds:
                    # Reset window
                    cursor.execute('''
                        UPDATE download_rate_limits
                        SET tokens_generated_count = 1,
                            window_start = %s,
                            last_token_at = %s
                        WHERE user_id = %s
                    ''', (current_time, current_time, user_id))
                    conn.commit()
                    return (True, None)
                elif count >= max_tokens:
                    # Rate limit exceeded
                    return (False, f"Rate limit exceeded: {count}/{max_tokens} tokens used")
                else:
                    # Increment counter
                    cursor.execute('''
                        UPDATE download_rate_limits
                        SET tokens_generated_count = tokens_generated_count + 1,
                            last_token_at = %s
                        WHERE user_id = %s
                    ''', (current_time, user_id))
                    conn.commit()
                    return (True, None)
            else:
                # First token for this user
                cursor.execute('''
                    INSERT INTO download_rate_limits (user_id, tokens_generated_count, window_start, last_token_at)
                    VALUES (%s, 1, %s, %s)
                ''', (user_id, current_time, current_time))
                conn.commit()
                return (True, None)

        finally:
            put_connection(conn)

    @staticmethod
    def verify_order_ownership(order_id: str, user_id: int) -> Optional[Tuple[str, str, float]]:
        """
        Verifie qu'un user possede un order

        Returns:
            (main_file_url, title, file_size_mb) ou None
        """
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.main_file_url, p.title, p.file_size_mb
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                WHERE o.order_id = %s
                  AND o.buyer_user_id = %s
                  AND o.payment_status = 'completed'
                LIMIT 1
            ''', (order_id, user_id))

            return cursor.fetchone()

        finally:
            put_connection(conn)

    @staticmethod
    def create_download_token(user_id: int, order_id: str, product_id: str, expires_minutes: int = 5) -> str:
        """
        Cree un token de telechargement

        Returns:
            token UUID
        """
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()

            token = str(uuid.uuid4())
            current_time = datetime.now()
            expires_at = current_time + timedelta(minutes=expires_minutes)

            cursor.execute('''
                INSERT INTO download_tokens (
                    token, user_id, order_id, product_id, created_at, expires_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            ''', (token, user_id, order_id, product_id, current_time, expires_at))

            conn.commit()
            return token

        finally:
            put_connection(conn)

    @staticmethod
    def get_and_validate_token(token: str) -> Optional[Tuple[int, str, str]]:
        """
        Recupere et valide un token
        Marque comme utilise si valide

        Returns:
            (user_id, order_id, product_id) ou None
        """
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()

            # Get token info
            cursor.execute('''
                SELECT user_id, order_id, product_id, expires_at, used_at
                FROM download_tokens
                WHERE token = %s
            ''', (token,))

            result = cursor.fetchone()

            if not result:
                return None

            user_id, order_id, product_id, expires_at, used_at = result

            # Check if already used
            if used_at:
                return None

            # Check expiration
            if datetime.now() > expires_at:
                # Delete expired token
                cursor.execute('DELETE FROM download_tokens WHERE token = %s', (token,))
                conn.commit()
                return None

            # Mark as used (one-time)
            cursor.execute('''
                UPDATE download_tokens
                SET used_at = %s
                WHERE token = %s
            ''', (datetime.now(), token))
            conn.commit()

            return (user_id, order_id, product_id)

        finally:
            put_connection(conn)

    @staticmethod
    def increment_download_count(order_id: str):
        """Incremente le compteur de telechargements"""
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders
                SET download_count = COALESCE(download_count, 0) + 1,
                    last_download_at = CURRENT_TIMESTAMP
                WHERE order_id = %s
            ''', (order_id,))
            conn.commit()

        finally:
            put_connection(conn)

    @staticmethod
    def cleanup_expired_tokens(older_than_hours: int = 24):
        """Nettoie les tokens expires (cron job)"""
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()
            cutoff = datetime.now() - timedelta(hours=older_than_hours)

            cursor.execute('''
                DELETE FROM download_tokens
                WHERE expires_at < %s
            ''', (cutoff,))

            deleted_count = cursor.rowcount
            conn.commit()

            return deleted_count

        finally:
            put_connection(conn)
