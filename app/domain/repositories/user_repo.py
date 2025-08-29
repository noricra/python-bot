import sqlite3
from typing import Optional, Dict

from app.core import get_sqlite_connection, settings as core_settings


class UserRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def add_user(self, user_id: int, username: str, first_name: str, language_code: str = 'fr') -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, language_code)
                VALUES (?, ?, ?, ?)
                ''',
                (user_id, username, first_name, language_code),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

