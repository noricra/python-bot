"""
SQLite implementation of UserRepositoryInterface.
"""

import sqlite3
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.entities import User
from app.application.interfaces import UserRepositoryInterface
from app.core import get_sqlite_connection, settings


class SqliteUserRepository(UserRepositoryInterface):
    """SQLite implementation of user repository."""
    
    def __init__(self, database_path: Optional[str] = None):
        self.database_path = database_path or settings.DATABASE_PATH
    
    async def create(self, user: User) -> bool:
        """Create a new user."""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, language_code, is_seller, is_partner,
                 partner_code, seller_name, seller_bio, seller_solana_address,
                 seller_rating, seller_sales_count, referral_code, referral_earnings_eur,
                 email, registration_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.user_id, user.username, user.first_name, user.language_code,
                user.is_seller, user.is_partner, user.partner_code, user.seller_name,
                user.seller_bio, user.seller_solana_address, float(user.seller_rating),
                user.seller_sales_count, user.referral_code, float(user.referral_earnings_eur),
                user.email, user.registration_date or datetime.utcnow()
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error creating user: {e}")
            return False
        finally:
            conn.close()
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return User(
                    user_id=row['user_id'],
                    username=row['username'],
                    first_name=row['first_name'],
                    language_code=row['language_code'],
                    is_seller=bool(row['is_seller']),
                    is_partner=bool(row['is_partner']),
                    partner_code=row['partner_code'],
                    seller_name=row['seller_name'],
                    seller_bio=row['seller_bio'],
                    seller_solana_address=row['seller_solana_address'],
                    seller_rating=Decimal(str(row['seller_rating'] or 0)),
                    seller_sales_count=row['seller_sales_count'] or 0,
                    referral_code=row['referral_code'],
                    referral_earnings_eur=Decimal(str(row['referral_earnings_eur'] or 0)),
                    email=row['email'],
                    registration_date=datetime.fromisoformat(row['registration_date']) if row['registration_date'] else None
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            conn.close()
    
    async def get_by_partner_code(self, partner_code: str) -> Optional[User]:
        """Get user by partner code."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE partner_code = ?', (partner_code,))
            row = cursor.fetchone()
            if row:
                return await self.get_by_id(row['user_id'])
            return None
        except sqlite3.Error as e:
            print(f"Error getting user by partner code: {e}")
            return None
        finally:
            conn.close()
    
    async def update(self, user: User) -> bool:
        """Update user."""
        return await self.create(user)  # Use REPLACE behavior
    
    async def delete(self, user_id: int) -> bool:
        """Delete user."""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting user: {e}")
            return False
        finally:
            conn.close()
    
    async def get_all_sellers(self) -> List[User]:
        """Get all sellers."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE is_seller = 1')
            rows = cursor.fetchall()
            users = []
            for row in rows:
                user = await self.get_by_id(row['user_id'])
                if user:
                    users.append(user)
            return users
        except sqlite3.Error as e:
            print(f"Error getting sellers: {e}")
            return []
        finally:
            conn.close()
    
    async def is_solana_address_taken(self, address: str, exclude_user_id: int = None) -> bool:
        """Check if Solana address is already taken."""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            if exclude_user_id:
                cursor.execute(
                    'SELECT COUNT(*) FROM users WHERE seller_solana_address = ? AND user_id != ?',
                    (address, exclude_user_id)
                )
            else:
                cursor.execute(
                    'SELECT COUNT(*) FROM users WHERE seller_solana_address = ?',
                    (address,)
                )
            count = cursor.fetchone()[0]
            return count > 0
        except sqlite3.Error as e:
            print(f"Error checking Solana address: {e}")
            return True  # Assume taken on error for safety
        finally:
            conn.close()