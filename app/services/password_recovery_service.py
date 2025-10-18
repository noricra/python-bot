import time
import logging
from typing import Dict
import hashlib

from app.services.smtp_service import SMTPService
from app.domain.repositories.user_repo import UserRepository
from app.services.seller_service import generate_salt, hash_password

logger = logging.getLogger(__name__)


class PasswordRecoveryService:
    """Service for handling password recovery with email verification"""

    def __init__(self, db_path: str = None):
        self.smtp_service = SMTPService()
        self.user_repo = UserRepository(db_path)

    def start_recovery_process(self, email: str) -> Dict[str, any]:
        """Initiate password recovery process by sending email with code"""
        try:
            # Validate email format
            if not self.smtp_service.validate_email_format(email):
                return {"success": False, "error": "recovery_invalid_email"}

            # Check if user exists
            user = self.user_repo.get_user_by_email(email)
            if not user:
                return {"success": False, "error": "recovery_no_account"}

            # Check if user is suspended
            seller_name = user.get('seller_name', '') or ''
            if seller_name.startswith('[SUSPENDED]'):
                logger.warning(f"Blocked password recovery for suspended user email: {email}")
                return {"success": False, "error": "recovery_account_suspended"}

            # Generate recovery code
            recovery_code = self.smtp_service.generate_recovery_code()
            code_hash = self.smtp_service.hash_recovery_code(recovery_code)

            # Store code hash and expiry in database (15 minutes)
            expiry_timestamp = int(time.time() + (15 * 60))
            if not self.user_repo.set_recovery_code(email, code_hash, expiry_timestamp):
                return {"success": False, "error": "Erreur lors de la sauvegarde du code"}

            # Send email
            if self.smtp_service.send_recovery_email(email, recovery_code):
                logger.info(f"Recovery email sent to {email}")
                return {
                    "success": True,
                    "message": "Code de récupération envoyé par email",
                    "email": email
                }
            else:
                return {"success": False, "error": "Erreur lors de l'envoi de l'email"}

        except Exception as e:
            logger.error(f"Error in recovery process for {email}: {e}")
            return {"success": False, "error": "Erreur interne"}

    def validate_recovery_code(self, email: str, code: str) -> Dict[str, any]:
        """Validate recovery code and check expiration"""
        try:
            # Check if code is valid format
            if not code.isdigit() or len(code) != 6:
                return {"success": False, "error": "recovery_invalid_code"}

            # Validate code and expiration in database
            code_hash = self.smtp_service.hash_recovery_code(code)
            current_timestamp = int(time.time())

            if self.user_repo.validate_recovery_code(email, code_hash, current_timestamp):
                return {
                    "success": True,
                    "message": "Code validé avec succès",
                    "email": email
                }
            else:
                # Code either incorrect or expired
                return {"success": False, "error": "recovery_code_incorrect"}

        except Exception as e:
            logger.error(f"Error validating recovery code for {email}: {e}")
            return {"success": False, "error": "Erreur interne"}

    def set_new_password(self, email: str, new_password: str) -> Dict[str, any]:
        """Set new password after successful code validation"""
        try:
            # Validate password
            if len(new_password) < 8:
                return {"success": False, "error": "recovery_password_too_short"}

            # Generate salt and hash
            salt = generate_salt()
            pwd_hash = hash_password(new_password, salt)

            # Update password in database (also clears recovery code)
            if self.user_repo.update_password_by_email(email, salt, pwd_hash):
                logger.info(f"Password updated successfully for {email}")
                return {
                    "success": True,
                    "message": "Mot de passe mis à jour avec succès"
                }
            else:
                return {"success": False, "error": "Erreur lors de la mise à jour"}

        except Exception as e:
            logger.error(f"Error setting new password for {email}: {e}")
            return {"success": False, "error": "Erreur interne"}

    def cleanup_expired_codes(self):
        """Clean up expired recovery codes from database"""
        try:
            # Expiration is now handled in database queries
            # This method can be used for periodic cleanup if needed
            logger.debug("Recovery code expiration handled via database queries")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")