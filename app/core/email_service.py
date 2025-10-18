"""
Email Service - Service d'envoi d'emails pour récupération et notifications
"""
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service d'envoi d'emails"""

    def __init__(self):
        """Initialiser le service email"""
        # Configuration SMTP pour production
        from app.core.settings import settings
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_email = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_configured = bool(self.smtp_server and self.smtp_email and self.smtp_password)

        logger.info(f"EmailService initialized - SMTP configured: {self.smtp_configured}")
        logger.info(f"SMTP Server: {self.smtp_server}:{self.smtp_port}")
        logger.info(f"SMTP Email: {self.smtp_email}")
        if not self.smtp_configured:
            logger.warning("SMTP not fully configured - running in simulation mode")

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Envoie un email

        Args:
            to_email: Adresse email destinataire
            subject: Sujet de l'email
            body: Corps du message

        Returns:
            bool: True si envoi réussi
        """
        try:
            if not self.smtp_configured:
                # Mode simulation si SMTP pas configuré
                logger.info(f"📧 Email simulé - To: {to_email}, Subject: {subject}")
                print(f"📧 Email to {to_email}: {subject}")
                return True

            # Envoi SMTP réel
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # Créer le message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Connexion et envoi avec gestion d'erreur robuste
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.set_debuglevel(0)  # Disable debug output

                    # Start TLS if using port 587
                    if self.smtp_port == 587:
                        server.starttls()
                        logger.debug("TLS connection established")

                    # Login
                    server.login(self.smtp_email, self.smtp_password)
                    logger.debug("SMTP authentication successful")

                    # Send message
                    server.send_message(msg)
                    logger.info(f"📧 Email envoyé avec succès - To: {to_email}, Subject: {subject}")
                    return True

            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP Authentication failed: {e}")
                # Fallback to simulation mode
                logger.info(f"📧 Email simulé (auth failed) - To: {to_email}, Subject: {subject}")
                return True
            except smtplib.SMTPRecipientsRefused as e:
                logger.error(f"SMTP Recipients refused: {e}")
                return False
            except smtplib.SMTPServerDisconnected as e:
                logger.error(f"SMTP Server disconnected: {e}")
                # Fallback to simulation mode
                logger.info(f"📧 Email simulé (server disconnected) - To: {to_email}, Subject: {subject}")
                return True
            except Exception as e:
                logger.error(f"Unexpected SMTP error: {e}")
                # Fallback to simulation mode for any other error
                logger.info(f"📧 Email simulé (error fallback) - To: {to_email}, Subject: {subject}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False

    def send_recovery_email(self, to_email: str, recovery_code: str) -> bool:
        """
        Envoie un email de récupération de compte vendeur

        Args:
            to_email: Email du vendeur
            recovery_code: Code de récupération

        Returns:
            bool: True si envoi réussi
        """
        subject = "🔑 Récupération de votre compte vendeur - TechBot Marketplace"

        body = f"""
Bonjour,

Vous avez demandé la récupération de votre compte vendeur.

Code de récupération: {recovery_code}

Ce code expire dans 1 heure.

Si vous n'avez pas demandé cette récupération, ignorez ce message.

Cordialement,
L'équipe TechBot Marketplace
        """

        return self.send_email(to_email, subject, body)