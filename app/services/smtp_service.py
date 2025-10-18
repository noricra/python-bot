import smtplib
import logging
import random
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core import settings as core_settings

logger = logging.getLogger(__name__)


class SMTPService:
    """Service SMTP pour l'envoi d'emails de récupération"""

    def __init__(self):
        self.smtp_server = core_settings.SMTP_SERVER
        self.smtp_port = core_settings.SMTP_PORT
        self.smtp_username = core_settings.SMTP_USERNAME
        self.smtp_password = core_settings.SMTP_PASSWORD
        self.from_email = core_settings.FROM_EMAIL

    def generate_recovery_code(self) -> str:
        """Génère un code de récupération à 6 chiffres"""
        return str(random.randint(100000, 999999))

    def hash_recovery_code(self, code: str) -> str:
        """Hash le code de récupération pour stockage sécurisé"""
        return hashlib.sha256(code.encode()).hexdigest()

    def send_recovery_email(self, email: str, recovery_code: str) -> bool:
        """Envoie l'email de récupération avec le code"""
        try:
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Code de récupération - Marketplace Bot"
            msg['From'] = self.from_email
            msg['To'] = email

            # Corps de l'email en HTML
            html_content = f"""
            <html>
                <head></head>
                <body>
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; text-align: center; color: white;">
                            <h1 style="margin: 0; font-size: 28px;">🔐 Code de Récupération</h1>
                        </div>

                        <div style="background: #f8f9fa; padding: 30px; border-radius: 10px; margin: 20px 0;">
                            <p style="font-size: 16px; color: #333; margin-bottom: 20px;">
                                Bonjour,
                            </p>
                            <p style="font-size: 16px; color: #333; margin-bottom: 20px;">
                                Vous avez demandé la récupération de votre mot de passe pour votre compte Marketplace Bot.
                            </p>
                            <p style="font-size: 16px; color: #333; margin-bottom: 30px;">
                                Voici votre code de récupération :
                            </p>

                            <div style="background: #fff; border: 2px dashed #667eea; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                                <h2 style="font-size: 32px; color: #667eea; margin: 0; letter-spacing: 8px; font-weight: bold;">
                                    {recovery_code}
                                </h2>
                            </div>

                            <p style="font-size: 14px; color: #666; text-align: center; margin: 20px 0;">
                                ⏰ Ce code expire dans 15 minutes
                            </p>
                            <p style="font-size: 14px; color: #666; text-align: center;">
                                🔒 Ne partagez jamais ce code avec personne
                            </p>
                        </div>

                        <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                            <p>Si vous n'avez pas demandé cette récupération, ignorez cet email.</p>
                            <p>© 2024 Marketplace Bot - Service de récupération automatique</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            # Version texte simple
            text_content = f"""
            🔐 CODE DE RÉCUPÉRATION - MARKETPLACE BOT

            Bonjour,

            Vous avez demandé la récupération de votre mot de passe.

            Votre code de récupération : {recovery_code}

            ⏰ Ce code expire dans 15 minutes
            🔒 Ne partagez jamais ce code avec personne

            Si vous n'avez pas demandé cette récupération, ignorez cet email.

            © 2024 Marketplace Bot
            """

            # Attacher les versions HTML et texte
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')

            msg.attach(part1)
            msg.attach(part2)

            # Envoyer l'email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Recovery email sent successfully to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send recovery email to {email}: {e}")
            return False

    def validate_email_format(self, email: str) -> bool:
        """Valide le format de l'email"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def send_suspension_notification(self, email: str, user_name: str) -> bool:
        """Envoie l'email de notification de suspension"""
        try:
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Compte suspendu - Marketplace Bot"
            msg['From'] = self.from_email
            msg['To'] = email

            # Corps de l'email en HTML
            html_content = f"""
            <html>
            <body>
                <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0;">🚫 Compte Suspendu</h1>
                    </div>

                    <div style="padding: 30px; background-color: #f8f9fa;">
                        <p>Bonjour {user_name},</p>

                        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; border-radius: 5px;">
                            <h3 style="color: #856404; margin-top: 0;">⚠️ Votre compte a été suspendu</h3>
                            <p style="color: #856404; margin-bottom: 0;">
                                Votre compte vendeur sur le Marketplace Bot a été temporairement suspendu.
                                Tous vos produits ont été retirés du marché.
                            </p>
                        </div>

                        <h3>🔍 Que faire maintenant ?</h3>
                        <ul>
                            <li><strong>Contactez le support :</strong> Utilisez la fonction support du bot</li>
                            <li><strong>Expliquez votre situation :</strong> Décrivez les circonstances</li>
                            <li><strong>Attendez la réponse :</strong> Notre équipe examinera votre cas</li>
                        </ul>

                        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; margin: 20px 0; border-radius: 5px;">
                            <p style="color: #0c5460; margin: 0;">
                                💬 <strong>Support disponible 24/7</strong><br>
                                Utilisez le bouton "Support" dans le bot Telegram pour nous contacter.
                            </p>
                        </div>

                        <p style="margin-top: 30px;">
                            Cordialement,<br>
                            <strong>L'équipe Marketplace Bot</strong>
                        </p>
                    </div>

                    <div style="background-color: #f1f3f4; padding: 20px; text-align: center; font-size: 12px; color: #6c757d;">
                        <p style="margin: 0;">Cet email a été généré automatiquement. Ne pas répondre.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Version texte
            text_content = f"""
Bonjour {user_name},

COMPTE SUSPENDU

Votre compte vendeur sur le Marketplace Bot a été temporairement suspendu.
Tous vos produits ont été retirés du marché.

Que faire maintenant ?
- Contactez le support via le bot Telegram
- Expliquez votre situation
- Attendez la réponse de notre équipe

Support disponible 24/7 via le bouton "Support" dans le bot.

Cordialement,
L'équipe Marketplace Bot

---
Cet email a été généré automatiquement. Ne pas répondre.
            """

            # Attacher les deux versions
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(text_part)
            msg.attach(html_part)

            # Envoyer l'email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Suspension notification email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send suspension notification to {email}: {e}")
            return False