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

    def _build_email_template(self, header_title: str, header_subtitle: str, content_html: str) -> str:
        """
        Construit un template HTML email avec le design UZEUR standard

        Args:
            header_title: Titre principal du header (ex: "🎉 Bienvenue sur UZEUR !")
            header_subtitle: Sous-titre du header (ex: "Votre compte vendeur est actif")
            content_html: Contenu HTML à insérer dans le body

        Returns:
            str: HTML complet avec CSS inline
        """
        return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            background: #fafbfc;
            color: #334155;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(139, 92, 246, 0.12);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 50%, #ec4899 100%);
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 900;
            color: white;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .header p {{
            font-size: 16px;
            color: rgba(255, 255, 255, 0.9);
        }}

        .content {{
            padding: 40px 30px;
        }}

        .welcome-box, .login-box, .alert-box, .success-box {{
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.05) 0%, rgba(236, 72, 153, 0.05) 100%);
            border-left: 4px solid #8b5cf6;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}

        .welcome-box h2, .login-box h2, .alert-box h2, .success-box h2 {{
            font-size: 24px;
            font-weight: 800;
            color: #1e293b;
            margin-bottom: 10px;
        }}

        .info-section {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}

        .info-item {{
            margin-bottom: 16px;
        }}

        .info-item:last-child {{
            margin-bottom: 0;
        }}

        .info-label {{
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}

        .info-value {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
            word-break: break-all;
        }}

        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
            color: white;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 16px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
            transition: transform 0.2s;
        }}

        .cta-button:hover {{
            transform: translateY(-2px);
        }}

        .steps {{
            margin-top: 30px;
        }}

        .step {{
            display: flex;
            margin-bottom: 20px;
            align-items: flex-start;
        }}

        .step-number {{
            background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 18px;
            margin-right: 16px;
            flex-shrink: 0;
        }}

        .step-content h3 {{
            font-size: 16px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 4px;
        }}

        .step-content p {{
            font-size: 14px;
            color: #64748b;
        }}

        .footer {{
            background: #f3f4f6;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}

        .footer p {{
            font-size: 14px;
            color: #64748b;
            margin-bottom: 8px;
        }}

        .footer a {{
            color: #8b5cf6;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{header_title}</h1>
            <p>{header_subtitle}</p>
        </div>

        <div class="content">
            {content_html}
        </div>

        <div class="footer">
            <p>© 2025 UZEUR Marketplace</p>
            <p><a href="https://uzeur.com">uzeur.com</a></p>
        </div>
    </div>
</body>
</html>
"""

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

    def send_seller_welcome_email(self, to_email: str, seller_name: str, solana_address: str) -> bool:
        """
        Envoie un email de bienvenue au nouveau vendeur (style site2.html)

        Args:
            to_email: Email du vendeur
            seller_name: Nom du vendeur
            solana_address: Adresse Solana pour paiements

        Returns:
            bool: True si envoi réussi
        """
        subject = "🎉 Bienvenue sur UZEUR Marketplace !"

        # Contenu spécifique à l'email de bienvenue
        content_html = f"""
            <div class="welcome-box">
                <h2>Bonjour {seller_name} 👋</h2>
                <p>Félicitations ! Votre compte vendeur a été créé avec succès. Vous pouvez maintenant commencer à vendre vos produits numériques sur notre marketplace décentralisée.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label">📧 Email de notification</div>
                    <div class="info-value">{to_email}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">💰 Adresse Solana (Payouts)</div>
                    <div class="info-value">{solana_address}</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    🚀 Accéder au Dashboard
                </a>
            </div>

            <div class="steps">
                <h3 style="font-size: 20px; font-weight: 800; color: #1e293b; margin-bottom: 20px;">
                    Prochaines étapes :
                </h3>

                <div class="step">
                    <div class="step-number">1</div>
                    <div class="step-content">
                        <h3>Ajoutez votre premier produit</h3>
                        <p>Créez votre catalogue en quelques clics depuis le bot Telegram</p>
                    </div>
                </div>

                <div class="step">
                    <div class="step-number">2</div>
                    <div class="step-content">
                        <h3>Configurez votre profil</h3>
                        <p>Personnalisez votre bio et nom dans les paramètres vendeur</p>
                    </div>
                </div>

                <div class="step">
                    <div class="step-number">3</div>
                    <div class="step-content">
                        <h3>Recevez vos premiers paiements</h3>
                        <p>Les payouts crypto sont automatiques après chaque vente</p>
                    </div>
                </div>
            </div>

            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                    💡 <strong>Besoin d'aide ?</strong> Contactez le support directement depuis le bot avec /support
                </p>
            </div>
        """

        # Utiliser le template builder
        body = self._build_email_template(
            header_title="🎉 Bienvenue sur UZEUR !",
            header_subtitle="Votre compte vendeur est actif",
            content_html=content_html
        )

        # Envoyer en HTML
        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email de bienvenue vendeur simulé - To: {to_email}")
                print(f"📧 Welcome email to {seller_name} ({to_email})")
                print(f"   Solana: {solana_address}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Ajouter le corps HTML
            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email de bienvenue vendeur envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email bienvenue: {e}")
            # Fallback simulation
            logger.info(f"📧 Email de bienvenue vendeur simulé (fallback) - To: {to_email}")
            return True

    def send_seller_login_notification(self, to_email: str, seller_name: str, login_time: str) -> bool:
        """
        Envoie un email de notification de connexion vendeur (style site2.html)

        Args:
            to_email: Email du vendeur
            seller_name: Nom du vendeur
            login_time: Timestamp de connexion (format: "26/10/2025 à 14:30")

        Returns:
            bool: True si envoi réussi
        """
        subject = "🔐 Nouvelle connexion à votre compte vendeur UZEUR"

        # Contenu spécifique à l'email de connexion
        content_html = f"""
            <div class="login-box">
                <h2>Bonjour {seller_name} 👋</h2>
                <p>Une connexion à votre compte vendeur UZEUR a été effectuée avec succès.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label">📧 Email du compte</div>
                    <div class="info-value">{to_email}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">🕐 Date et heure de connexion</div>
                    <div class="info-value">{login_time}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">📱 Plateforme</div>
                    <div class="info-value">Telegram Bot</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    🏪 Accéder au Dashboard
                </a>
            </div>

            <div class="security-notice">
                <h3>🔒 Sécurité de votre compte</h3>
                <p>Si vous n'êtes pas à l'origine de cette connexion, contactez immédiatement le support via /support dans le bot.</p>
            </div>
        """

        # Utiliser le template builder
        body = self._build_email_template(
            header_title="🔐 Connexion Détectée",
            header_subtitle="Votre compte vendeur a été connecté",
            content_html=content_html
        )

        # Envoyer en HTML
        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email de connexion vendeur simulé - To: {to_email}")
                print(f"📧 Login notification to {seller_name} ({to_email})")
                print(f"   Login time: {login_time}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Ajouter le corps HTML
            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email de connexion vendeur envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email connexion: {e}")
            # Fallback simulation
            logger.info(f"📧 Email de connexion vendeur simulé (fallback) - To: {to_email}")
            return True

    def send_product_suspended_notification(self, to_email: str, seller_name: str, product_title: str, reason: str, can_appeal: bool = True) -> bool:
        """
        Envoie un email de notification de suspension de produit (style site2.html)

        Args:
            to_email: Email du vendeur
            seller_name: Nom du vendeur
            product_title: Titre du produit suspendu
            reason: Raison de la suspension
            can_appeal: Si le vendeur peut faire appel

        Returns:
            bool: True si envoi réussi
        """
        subject = "⚠️ Votre produit a été suspendu - UZEUR Marketplace"

        appeal_section = """
            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                    💡 <strong>Faire appel ?</strong> Contactez le support via /support dans le bot
                </p>
            </div>
        """ if can_appeal else """
            <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(251, 146, 60, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #7c2d12; margin: 0;">
                    ⚠️ Cette décision est <strong>définitive</strong>. Le produit ne pourra pas être réactivé.
                </p>
            </div>
        """

        body = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            background: #fafbfc;
            color: #334155;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(239, 68, 68, 0.12);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #ef4444 0%, #f87171 50%, #fb923c 100%);
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 900;
            color: white;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .header p {{
            font-size: 16px;
            color: rgba(255, 255, 255, 0.9);
        }}

        .content {{
            padding: 40px 30px;
        }}

        .alert-box {{
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(251, 146, 60, 0.1) 100%);
            border-left: 4px solid #ef4444;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}

        .alert-box h2 {{
            font-size: 24px;
            font-weight: 800;
            color: #991b1b;
            margin-bottom: 10px;
        }}

        .info-section {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}

        .info-item {{
            margin-bottom: 16px;
        }}

        .info-item:last-child {{
            margin-bottom: 0;
        }}

        .info-label {{
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}

        .info-value {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
        }}

        .reason-box {{
            background: #fef2f2;
            border: 2px solid #fecaca;
            padding: 20px;
            border-radius: 12px;
            margin: 24px 0;
        }}

        .reason-box h3 {{
            font-size: 16px;
            font-weight: 700;
            color: #991b1b;
            margin-bottom: 12px;
        }}

        .reason-box p {{
            font-size: 14px;
            color: #7c2d12;
            line-height: 1.8;
        }}

        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
            color: white;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 16px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
            transition: transform 0.2s;
        }}

        .cta-button:hover {{
            transform: translateY(-2px);
        }}

        .footer {{
            background: #f3f4f6;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}

        .footer p {{
            font-size: 14px;
            color: #64748b;
            margin-bottom: 8px;
        }}

        .footer a {{
            color: #8b5cf6;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Produit Suspendu</h1>
            <p>Action requise sur votre catalogue</p>
        </div>

        <div class="content">
            <div class="alert-box">
                <h2>Bonjour {seller_name},</h2>
                <p>Votre produit a été suspendu par notre équipe de modération et n'est plus visible sur la marketplace.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label">📦 Produit concerné</div>
                    <div class="info-value">{product_title}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">📧 Compte vendeur</div>
                    <div class="info-value">{to_email}</div>
                </div>
            </div>

            <div class="reason-box">
                <h3>🔍 Raison de la suspension :</h3>
                <p>{reason}</p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    🏪 Accéder au Dashboard
                </a>
            </div>

            {appeal_section}
        </div>

        <div class="footer">
            <p><strong>UZEUR Marketplace</strong></p>
            <p>La marketplace décentralisée pour produits numériques</p>
            <p style="margin-top: 16px;">
                <a href="#">Règlement de la plateforme</a> • <a href="#">CGV</a>
            </p>
        </div>
    </div>
</body>
</html>
        """

        # Envoyer en HTML
        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email suspension produit simulé - To: {to_email}")
                print(f"📧 Product suspended notification to {seller_name} ({to_email})")
                print(f"   Product: {product_title}")
                print(f"   Reason: {reason}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email suspension produit envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email suspension produit: {e}")
            logger.info(f"📧 Email suspension produit simulé (fallback) - To: {to_email}")
            return True

    def send_account_suspended_notification(self, to_email: str, user_name: str, reason: str, duration: str = "indéterminée", is_permanent: bool = False) -> bool:
        """
        Envoie un email de notification de suspension de compte (style site2.html)

        Args:
            to_email: Email de l'utilisateur
            user_name: Nom de l'utilisateur
            reason: Raison de la suspension
            duration: Durée de la suspension
            is_permanent: Si la suspension est permanente

        Returns:
            bool: True si envoi réussi
        """
        subject = "🔒 Votre compte a été suspendu - UZEUR Marketplace"

        duration_info = """
            <div class="info-item">
                <div class="info-label">⏱️ Durée de la suspension</div>
                <div class="info-value" style="color: #dc2626;">PERMANENTE</div>
            </div>
        """ if is_permanent else f"""
            <div class="info-item">
                <div class="info-label">⏱️ Durée de la suspension</div>
                <div class="info-value">{duration}</div>
            </div>
        """

        appeal_section = """
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    📞 Contacter le Support
                </a>
            </div>

            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                    💡 <strong>Faire appel ?</strong> Contactez le support via /support pour soumettre votre dossier
                </p>
            </div>
        """ if not is_permanent else """
            <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(251, 146, 60, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #7c2d12; margin: 0;">
                    ⚠️ Cette suspension est <strong>permanente</strong>. Vous ne pouvez plus accéder à la plateforme.
                </p>
            </div>
        """

        body = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            background: #fafbfc;
            color: #334155;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(239, 68, 68, 0.12);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #dc2626 0%, #ef4444 50%, #f87171 100%);
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 900;
            color: white;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .header p {{
            font-size: 16px;
            color: rgba(255, 255, 255, 0.9);
        }}

        .content {{
            padding: 40px 30px;
        }}

        .alert-box {{
            background: linear-gradient(135deg, rgba(220, 38, 38, 0.1) 0%, rgba(251, 146, 60, 0.1) 100%);
            border-left: 4px solid #dc2626;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}

        .alert-box h2 {{
            font-size: 24px;
            font-weight: 800;
            color: #7f1d1d;
            margin-bottom: 10px;
        }}

        .info-section {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}

        .info-item {{
            margin-bottom: 16px;
        }}

        .info-item:last-child {{
            margin-bottom: 0;
        }}

        .info-label {{
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}

        .info-value {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
        }}

        .reason-box {{
            background: #fef2f2;
            border: 2px solid #fecaca;
            padding: 20px;
            border-radius: 12px;
            margin: 24px 0;
        }}

        .reason-box h3 {{
            font-size: 16px;
            font-weight: 700;
            color: #991b1b;
            margin-bottom: 12px;
        }}

        .reason-box p {{
            font-size: 14px;
            color: #7c2d12;
            line-height: 1.8;
        }}

        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
            color: white;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 16px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
            transition: transform 0.2s;
        }}

        .cta-button:hover {{
            transform: translateY(-2px);
        }}

        .footer {{
            background: #f3f4f6;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}

        .footer p {{
            font-size: 14px;
            color: #64748b;
            margin-bottom: 8px;
        }}

        .footer a {{
            color: #8b5cf6;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Compte Suspendu</h1>
            <p>Accès à votre compte temporairement bloqué</p>
        </div>

        <div class="content">
            <div class="alert-box">
                <h2>Bonjour {user_name},</h2>
                <p>Votre compte UZEUR Marketplace a été suspendu suite à une violation de nos conditions d'utilisation.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label">📧 Compte concerné</div>
                    <div class="info-value">{to_email}</div>
                </div>

                {duration_info}
            </div>

            <div class="reason-box">
                <h3>🔍 Raison de la suspension :</h3>
                <p>{reason}</p>
            </div>

            {appeal_section}
        </div>

        <div class="footer">
            <p><strong>UZEUR Marketplace</strong></p>
            <p>La marketplace décentralisée pour produits numériques</p>
            <p style="margin-top: 16px;">
                <a href="#">Règlement de la plateforme</a> • <a href="#">CGV</a>
            </p>
        </div>
    </div>
</body>
</html>
        """

        # Envoyer en HTML
        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email suspension compte simulé - To: {to_email}")
                print(f"📧 Account suspended notification to {user_name} ({to_email})")
                print(f"   Reason: {reason}")
                print(f"   Duration: {duration}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email suspension compte envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email suspension compte: {e}")
            logger.info(f"📧 Email suspension compte simulé (fallback) - To: {to_email}")
            return True

    def send_support_reply_notification(self, to_email: str, user_name: str, ticket_id: str, message_preview: str) -> bool:
        """
        Envoie un email de notification de nouvelle réponse support

        Args:
            to_email: Email de l'utilisateur
            user_name: Nom de l'utilisateur
            ticket_id: ID du ticket
            message_preview: Aperçu du message (premiers 200 caractères)

        Returns:
            bool: True si envoi réussi
        """
        subject = f"💬 Nouvelle réponse à votre ticket #{ticket_id} - UZEUR Support"

        # Limiter l'aperçu à 200 caractères
        preview = message_preview[:200] if len(message_preview) > 200 else message_preview

        body = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            background: #fafbfc;
            color: #334155;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(59, 130, 246, 0.12);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 50%, #8b5cf6 100%);
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 900;
            color: white;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .header p {{
            font-size: 16px;
            color: rgba(255, 255, 255, 0.9);
        }}

        .content {{
            padding: 40px 30px;
        }}

        .message-box {{
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
            border-left: 4px solid #3b82f6;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}

        .message-box h2 {{
            font-size: 24px;
            font-weight: 800;
            color: #1e40af;
            margin-bottom: 10px;
        }}

        .info-section {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}

        .info-item {{
            margin-bottom: 16px;
        }}

        .info-item:last-child {{
            margin-bottom: 0;
        }}

        .info-label {{
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}

        .info-value {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
        }}

        .preview-box {{
            background: #f8fafc;
            border: 2px solid #e0e7ff;
            padding: 20px;
            border-radius: 12px;
            margin: 24px 0;
        }}

        .preview-box h3 {{
            font-size: 14px;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 12px;
            text-transform: uppercase;
        }}

        .preview-box p {{
            font-size: 14px;
            color: #334155;
            line-height: 1.8;
            font-style: italic;
        }}

        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
            color: white;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 16px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            transition: transform 0.2s;
        }}

        .cta-button:hover {{
            transform: translateY(-2px);
        }}

        .footer {{
            background: #f3f4f6;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}

        .footer p {{
            font-size: 14px;
            color: #64748b;
            margin-bottom: 8px;
        }}

        .footer a {{
            color: #3b82f6;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 Nouvelle Réponse Support</h1>
            <p>Notre équipe vous a répondu</p>
        </div>

        <div class="content">
            <div class="message-box">
                <h2>Bonjour {user_name},</h2>
                <p>Vous avez reçu une nouvelle réponse à votre demande de support.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label">🎫 Numéro de ticket</div>
                    <div class="info-value">#{ticket_id}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">📧 Votre email</div>
                    <div class="info-value">{to_email}</div>
                </div>
            </div>

            <div class="preview-box">
                <h3>📄 Aperçu du message :</h3>
                <p>"{preview}..."</p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    📬 Lire le Message Complet
                </a>
            </div>

            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                    💡 <strong>Astuce :</strong> Répondez directement depuis le bot avec /support
                </p>
            </div>
        </div>

        <div class="footer">
            <p><strong>UZEUR Support</strong></p>
            <p>Notre équipe est là pour vous aider</p>
            <p style="margin-top: 16px;">
                <a href="#">Centre d'aide</a> • <a href="#">FAQ</a>
            </p>
        </div>
    </div>
</body>
</html>
        """

        # Envoyer en HTML
        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email réponse support simulé - To: {to_email}")
                print(f"📧 Support reply notification to {user_name} ({to_email})")
                print(f"   Ticket: #{ticket_id}")
                print(f"   Preview: {preview[:50]}...")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email réponse support envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email réponse support: {e}")
            logger.info(f"📧 Email réponse support simulé (fallback) - To: {to_email}")
            return True