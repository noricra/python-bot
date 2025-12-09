"""
Seller Service - Business logic for seller account management
"""
import psycopg2
import psycopg2.extras
import logging
from typing import Dict, Any, Optional
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
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

    def __init__(self):
        pass

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
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT user_id, seller_name FROM users WHERE email = %s AND seller_name LIKE %s', (email, '[SUSPENDED]%'))
            suspended_user = cursor.fetchone()

            if suspended_user:
                put_connection(conn)
                logger.warning(f"Blocked account creation for suspended user email: {email}")
                return {'success': False, 'error': 'Cet email appartient à un compte suspendu. Contactez le support.'}

            # Check if email already in use by another seller
            cursor.execute('SELECT user_id FROM users WHERE email = %s AND user_id != %s', (email, user_id))
            existing_email = cursor.fetchone()
            if existing_email:
                put_connection(conn)
                return {'success': False, 'error': 'Cet email est déjà utilisé par un autre vendeur'}

            # Vérifier si l'utilisateur est suspendu
            cursor.execute("SELECT seller_name FROM users WHERE user_id = %s", (user_id,))
            user_check = cursor.fetchone()
            if user_check and user_check.get('seller_name') and user_check['seller_name'].startswith('[SUSPENDED]'):
                put_connection(conn)
                logger.warning(f"Suspended user {user_id} tried to re-register as seller")
                return {'success': False, 'error': 'Votre compte est suspendu. Contactez l\'administration.'}

            try:
                # Ensure user exists in database
                self._ensure_user_exists(cursor, user_id)

                # Create simplified seller account (no password, no bio)
                cursor.execute('''
                    UPDATE users
                    SET is_seller = TRUE,
                        seller_name = %s,
                        seller_bio = NULL,
                        email = %s,
                        seller_solana_address = %s,
                        password_salt = NULL,
                        password_hash = NULL
                    WHERE user_id = %s
                ''', (seller_name, email, solana_address, user_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    put_connection(conn)
                    logger.info(f"✅ Simplified seller account created for user {user_id} ({seller_name})")
                    return {'success': True}
                else:
                    put_connection(conn)
                    return {'success': False, 'error': 'Échec mise à jour'}

            except psycopg2.Error as e:
                logger.error(f"❌ Database error creating simplified seller: {e}")
                put_connection(conn)
                return {'success': False, 'error': 'Erreur interne'}

        except (psycopg2.Error, Exception) as e:
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
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT user_id, seller_name FROM users WHERE email = %s AND seller_name LIKE %s', (email, '[SUSPENDED]%'))
            suspended_user = cursor.fetchone()

            if suspended_user:
                put_connection(conn)
                logger.warning(f"Blocked account creation for suspended user email: {email}")
                return {'success': False, 'error': 'Cet email appartient à un compte suspendu. Contactez le support.'}

            put_connection(conn)

            # Generate salt and hash password
            salt = generate_salt()
            pwd_hash = hash_password(raw_password, salt)

            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
                    put_connection(conn)
                    logger.info(f"✅ Seller account created for user {user_id}")
                    return {'success': True}
                else:
                    put_connection(conn)
                    return {'success': False, 'error': 'Échec mise à jour'}

            except psycopg2.Error as e:
                logger.error(f"❌ Database error creating seller: {e}")
                put_connection(conn)
                return {'success': False, 'error': 'Erreur interne'}

        except (psycopg2.Error, Exception) as e:
            logger.error(f"❌ Error creating seller account: {e}")
            return {'success': False, 'error': str(e)}

    # Address checking removed - no longer needed

    def _ensure_user_exists(self, cursor, user_id: int):
        """Ensure user exists in database, create if not"""
        try:
            cursor.execute('SELECT COUNT(*) as count FROM users WHERE user_id = %s', (user_id,))
            if cursor.fetchone()['count'] == 0:
                # Create user first
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, language_code)
                    VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                ''', (user_id, f'user_{user_id}', 'Unknown', 'fr'))
                logger.debug(f"✅ Created base user record for {user_id}")
        except psycopg2.Error as e:
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
                    seller_name = %s,
                    seller_bio = %s,
                    email = %s,
                    seller_solana_address = %s,
                    password_salt = %s,
                    password_hash = %s
                WHERE user_id = %s
            ''', (seller_name, seller_bio, email, solana_address, salt, pwd_hash, user_id))

            return cursor.rowcount > 0
        except psycopg2.Error as e:
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
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT is_seller FROM users WHERE user_id = %s', (user_id,))
            row = cursor.fetchone()
            put_connection(conn)
            return bool(row and row['is_seller'])
        except psycopg2.Error as e:
            logger.error(f"❌ Error authenticating seller: {e}")
            return False

    def validate_seller_password(self, user_id: int, password: str) -> bool:
        """Validate seller password"""
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT password_salt, password_hash, is_seller FROM users WHERE user_id = %s', (user_id,))
            row = cursor.fetchone()
            put_connection(conn)

            if not row or not row['is_seller']:  # not a seller
                return False

            stored_salt, stored_hash = row['password_salt'], row['password_hash']
            if not stored_salt or not stored_hash:
                return False

            # Hash provided password with stored salt
            computed_hash = hash_password(password, stored_salt)
            return computed_hash == stored_hash

        except psycopg2.Error as e:
            logger.error(f"❌ Error validating seller password: {e}")
            return False

    def get_seller_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get seller information"""
        try:
            conn = get_postgresql_connection()
            # PostgreSQL uses RealDictCursor
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('''
                SELECT seller_name, seller_bio,
                       seller_rating, total_sales, total_revenue, email
                FROM users
                WHERE user_id = %s AND is_seller = TRUE
            ''', (user_id,))

            row = cursor.fetchone()
            put_connection(conn)

            return row if row else None
        except psycopg2.Error as e:
            logger.error(f"❌ Error getting seller info: {e}")
            return None

    # Solana address management removed - simplified seller system
