"""
Seller Service - Business logic for seller account management
"""
import sqlite3
import logging
from typing import Dict, Any, Optional
from app.core import get_sqlite_connection
from app.core.validation import validate_solana_address

logger = logging.getLogger(__name__)

def generate_salt(length: int = 16) -> str:
    """Generate random salt for password hashing"""
    import os
    return os.urandom(length).hex()

def hash_password(password: str, salt: str) -> str:
    """Hash password with salt"""
    import hashlib
    try:
        base = f"{salt}:{password}".encode()
        return hashlib.sha256(base).hexdigest()
    except Exception:
        return ''

class SellerService:
    """Service for seller account operations"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def create_seller_account_simple(self, user_id: int, seller_name: str,
                                    email: str, solana_address: str) -> Dict[str, Any]:
        """
        Create simplified seller account (no password, no bio initially)

        Args:
            user_id: Telegram user ID
            seller_name: Name from Telegram (first_name or username)
            email: For notifications
            solana_address: For payments

        Returns:
            Dict with success status and error message if applicable
        """
        try:
            # Validate email
            if not email or '@' not in email:
                return {'success': False, 'error': 'Email invalide'}

            # Validate Solana address if provided
            if solana_address:
                if not validate_solana_address(solana_address):
                    return {'success': False, 'error': 'Adresse Solana invalide'}

            # Check if email belongs to a suspended user
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, seller_name FROM users WHERE email = ? AND seller_name LIKE "[SUSPENDED]%"', (email,))
            suspended_user = cursor.fetchone()

            if suspended_user:
                conn.close()
                logger.warning(f"Blocked account creation for suspended user email: {email}")
                return {'success': False, 'error': 'Cet email appartient à un compte suspendu. Contactez le support.'}

            # Check if email already in use by another seller
            cursor.execute('SELECT user_id FROM users WHERE email = ? AND user_id != ?', (email, user_id))
            existing_email = cursor.fetchone()
            if existing_email:
                conn.close()
                return {'success': False, 'error': 'Cet email est déjà utilisé par un autre vendeur'}

            try:
                # Ensure user exists in database
                self._ensure_user_exists(cursor, user_id)

                # Create simplified seller account (no password, no bio)
                cursor.execute('''
                    UPDATE users
                    SET is_seller = TRUE,
                        seller_name = ?,
                        seller_bio = NULL,
                        email = ?,
                        seller_solana_address = ?,
                        password_salt = NULL,
                        password_hash = NULL,
                        recovery_code_hash = NULL
                    WHERE user_id = ?
                ''', (seller_name, email, solana_address, user_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    conn.close()
                    logger.info(f"✅ Simplified seller account created for user {user_id} ({seller_name})")
                    return {'success': True}
                else:
                    conn.close()
                    return {'success': False, 'error': 'Échec mise à jour'}

            except sqlite3.Error as e:
                logger.error(f"❌ Database error creating simplified seller: {e}")
                conn.close()
                return {'success': False, 'error': 'Erreur interne'}

        except Exception as e:
            logger.error(f"❌ Error creating simplified seller account: {e}")
            return {'success': False, 'error': str(e)}

    def create_seller_account_with_recovery(self, user_id: int, seller_name: str,
                                         seller_bio: str, email: str,
                                         raw_password: str, solana_address: str = None) -> Dict[str, Any]:
        """
        Create seller account with email recovery system

        Args:
            user_id: Telegram user ID
            seller_name: Display name for seller
            seller_bio: Seller biography
            email: Recovery/contact email address
            raw_password: Plain text password
            solana_address: Solana wallet address for payouts

        Returns:
            Dict with success status and error message if applicable
        """
        try:
            # Validate password
            if not raw_password:
                return {'success': False, 'error': 'Mot de passe manquant'}

            # Validate email
            if not email or '@' not in email:
                return {'success': False, 'error': 'Email invalide'}

            # Check if email belongs to a suspended user
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, seller_name FROM users WHERE email = ? AND seller_name LIKE "[SUSPENDED]%"', (email,))
            suspended_user = cursor.fetchone()

            if suspended_user:
                conn.close()
                logger.warning(f"Blocked account creation for suspended user email: {email}")
                return {'success': False, 'error': 'Cet email appartient à un compte suspendu. Contactez le support.'}

            conn.close()

            # Generate salt and hash password
            salt = generate_salt()
            pwd_hash = hash_password(raw_password, salt)

            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()

            try:
                # Ensure user exists in database
                self._ensure_user_exists(cursor, user_id)

                # Create seller account
                success = self._update_user_as_seller(
                    cursor, user_id, seller_name, seller_bio,
                    email, salt, pwd_hash, solana_address
                )

                if success:
                    conn.commit()
                    conn.close()
                    logger.info(f"✅ Seller account created for user {user_id}")
                    return {'success': True}
                else:
                    conn.close()
                    return {'success': False, 'error': 'Échec mise à jour'}

            except sqlite3.Error as e:
                logger.error(f"❌ Database error creating seller: {e}")
                conn.close()
                return {'success': False, 'error': 'Erreur interne'}

        except Exception as e:
            logger.error(f"❌ Error creating seller account: {e}")
            return {'success': False, 'error': str(e)}

    # Address checking removed - no longer needed

    def _ensure_user_exists(self, cursor, user_id: int):
        """Ensure user exists in database, create if not"""
        try:
            cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
            if cursor.fetchone()[0] == 0:
                # Create user first
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, language_code)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, f'user_{user_id}', 'Unknown', 'fr'))
                logger.debug(f"✅ Created base user record for {user_id}")
        except sqlite3.Error as e:
            logger.error(f"❌ Error ensuring user exists: {e}")
            raise

    def _update_user_as_seller(self, cursor, user_id: int, seller_name: str,
                              seller_bio: str, email: str,
                              salt: str, pwd_hash: str, solana_address: str = None) -> bool:
        """Update user record with seller information"""
        try:
            cursor.execute('''
                UPDATE users
                SET is_seller = TRUE,
                    seller_name = ?,
                    seller_bio = ?,
                    email = ?,
                    seller_solana_address = ?,
                    recovery_code_hash = NULL,
                    password_salt = ?,
                    password_hash = ?
                WHERE user_id = ?
            ''', (seller_name, seller_bio, email, solana_address, salt, pwd_hash, user_id))

            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"❌ Error updating user as seller: {e}")
            raise

    def authenticate_seller(self, user_id: int) -> bool:
        """
        Authenticate seller account (simplified version)

        Note: The old seed phrase mechanism is no longer used.
        This validates that the user has an active seller account.
        Secure recovery is done via email + code.
        """
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT is_seller FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            return bool(row and row[0])
        except sqlite3.Error as e:
            logger.error(f"❌ Error authenticating seller: {e}")
            return False

    def validate_seller_password(self, user_id: int, password: str) -> bool:
        """Validate seller password"""
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT password_salt, password_hash, is_seller FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()

            if not row or not row[2]:  # not a seller
                return False

            stored_salt, stored_hash = row[0], row[1]
            if not stored_salt or not stored_hash:
                return False

            # Hash provided password with stored salt
            computed_hash = hash_password(password, stored_salt)
            return computed_hash == stored_hash

        except sqlite3.Error as e:
            logger.error(f"❌ Error validating seller password: {e}")
            return False

    def get_seller_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get seller information"""
        try:
            conn = get_sqlite_connection(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT seller_name, seller_bio,
                       seller_rating, total_sales, total_revenue, email
                FROM users
                WHERE user_id = ? AND is_seller = TRUE
            ''', (user_id,))

            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"❌ Error getting seller info: {e}")
            return None

    # Solana address management removed - simplified seller system