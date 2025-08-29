import sqlite3
from typing import List, Optional

from app.core import get_sqlite_connection, settings as core_settings


class ReferralRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def list_default_codes(self) -> List[str]:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT code FROM default_referral_codes WHERE is_active = TRUE')
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def list_partner_codes(self) -> List[str]:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT partner_code FROM users WHERE is_partner = TRUE AND partner_code IS NOT NULL')
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def set_user_partner_code(self, user_id: int, partner_code: str) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('UPDATE users SET is_partner = TRUE, partner_code = ? WHERE user_id = ?', (partner_code, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

