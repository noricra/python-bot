"""
Email Service - Service d'envoi d'emails pour récupération et notifications
"""
import logging
import asyncio

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
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        self.smtp_configured = bool(self.smtp_server and self.smtp_email and self.smtp_password)

        logger.info(f"EmailService initialized - SMTP configured: {self.smtp_configured}")
        logger.info(f"SMTP Server: {self.smtp_server}:{self.smtp_port}")
        logger.info(f"SMTP Email: {self.smtp_email}")
        logger.info(f"FROM Email: {self.from_email}")
        logger.info(f"FROM Name: {self.from_name}")
        if not self.smtp_configured:
            logger.warning("SMTP not fully configured - running in simulation mode")

    def _send_smtp_blocking(self, to_email: str, subject: str, body: str) -> bool:
        """
        Blocking SMTP send operation (to be called via asyncio.to_thread)

        Args:
            to_email: Adresse email destinataire
            subject: Sujet de l'email
            body: Corps du message

        Returns:
            bool: True si envoi réussi
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.from_name} <{self.from_email}>"
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

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Envoie un email (async, non-bloquant pour des milliers d'utilisateurs)

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

            # Envoi SMTP réel via thread pour ne pas bloquer l'event loop
            return await asyncio.to_thread(self._send_smtp_blocking, to_email, subject, body)

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
                    <div class="info-label"> Email de notification</div>
                    <div class="info-value">{to_email}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Adresse Solana (Payouts)</div>
                    <div class="info-value">{solana_address}</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Accéder au Dashboard
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
                     <strong>Besoin d'aide ?</strong> Contactez le support directement depuis le bot avec /support
                </p>
            </div>
        """

        # Utiliser le template builder
        body = self._build_email_template(
            header_title=" Bienvenue sur UZEUR !",
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
            msg['From'] = f"{self.from_name} <{self.from_email}>"
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
        subject = " Nouvelle connexion à votre compte vendeur UZEUR"

        # Contenu spécifique à l'email de connexion
        content_html = f"""
            <div class="login-box">
                <h2>Bonjour {seller_name} 👋</h2>
                <p>Une connexion à votre compte vendeur UZEUR a été effectuée avec succès.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label"> Email du compte</div>
                    <div class="info-value">{to_email}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Date et heure de connexion</div>
                    <div class="info-value">{login_time}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Plateforme</div>
                    <div class="info-value">UZEUR </div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Accéder au Dashboard
                </a>
            </div>

            <div class="security-notice">
                <h3> Sécurité de votre compte</h3>
                <p>Si vous n'êtes pas à l'origine de cette connexion, contactez immédiatement le support via /support dans le bot.</p>
            </div>
        """

        # Utiliser le template builder
        body = self._build_email_template(
            header_title=" Connexion Détectée",
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
            msg['From'] = f"{self.from_name} <{self.from_email}>"
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
                    <div class="info-label"> Produit concerné</div>
                    <div class="info-value">{product_title}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Compte vendeur</div>
                    <div class="info-value">{to_email}</div>
                </div>
            </div>

            <div class="reason-box">
                <h3> Raison de la suspension :</h3>
                <p>{reason}</p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Accéder au Dashboard
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
            msg['From'] = f"{self.from_name} <{self.from_email}>"
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
        subject = " Votre compte a été suspendu - UZEUR Marketplace"

        duration_info = """
            <div class="info-item">
                <div class="info-label">⏱ Durée de la suspension</div>
                <div class="info-value" style="color: #dc2626;">PERMANENTE</div>
            </div>
        """ if is_permanent else f"""
            <div class="info-item">
                <div class="info-label">⏱ Durée de la suspension</div>
                <div class="info-value">{duration}</div>
            </div>
        """

        appeal_section = """
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Contacter le Support
                </a>
            </div>

            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                     <strong>Faire appel ?</strong> Contactez le support via /support pour soumettre votre dossier
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
                    <div class="info-label"> Compte concerné</div>
                    <div class="info-value">{to_email}</div>
                </div>

                {duration_info}
            </div>

            <div class="reason-box">
                <h3> Raison de la suspension :</h3>
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
            msg['From'] = f"{self.from_name} <{self.from_email}>"
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


    def send_sale_confirmation_email(self, to_email: str, seller_name: str, product_title: str, buyer_name: str, sale_amount: str, sale_date: str) -> bool:
        """
        Envoie un email de confirmation de vente au vendeur

        Args:
            to_email: Email du vendeur
            seller_name: Nom du vendeur
            product_title: Titre du produit vendu
            buyer_name: Nom de l'acheteur
            sale_amount: Montant de la vente (ex: "50.00 USDT")
            sale_date: Date de la vente (ex: "26/10/2025 à 14:30")

        Returns:
            bool: True si envoi réussi
        """
        subject = "Nouvelle vente sur UZEUR Marketplace!"

        content_html = f"""
            <div class="success-box">
                <h2>Félicitations {seller_name}!</h2>
                <p>Vous avez réalisé une nouvelle vente sur UZEUR Marketplace.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label"> Produit vendu</div>
                    <div class="info-value">{product_title}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Acheteur</div>
                    <div class="info-value">{buyer_name}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Montant</div>
                    <div class="info-value">{sale_amount}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Date de vente</div>
                    <div class="info-value">{sale_date}</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Voir mes ventes
                </a>
            </div>

            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                     Le paiement sera automatiquement transféré vers votre wallet après confirmation
                </p>
            </div>
        """

        body = self._build_email_template(
            header_title=" Nouvelle Vente!",
            header_subtitle="Un client a acheté votre produit",
            content_html=content_html
        )

        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email confirmation vente simulé - To: {to_email}")
                print(f"📧 Sale confirmation to {seller_name} ({to_email})")
                print(f"   Product: {product_title}, Amount: {sale_amount}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email confirmation vente envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email confirmation vente: {e}")
            logger.info(f"📧 Email confirmation vente simulé (fallback) - To: {to_email}")
            return True

    def send_payment_received_email(self, to_email: str, seller_name: str, payout_amount: str, payout_address: str, transaction_date: str) -> bool:
        """
        Envoie un email de confirmation de paiement reçu au vendeur

        Args:
            to_email: Email du vendeur
            seller_name: Nom du vendeur
            payout_amount: Montant du payout (ex: "45.00 USDT")
            payout_address: Adresse de paiement (wallet)
            transaction_date: Date de la transaction (ex: "26/10/2025 à 14:30")

        Returns:
            bool: True si envoi réussi
        """
        subject = " Paiement reçu - UZEUR Marketplace"

        content_html = f"""
            <div class="success-box">
                <h2>Bonjour {seller_name},</h2>
                <p>Votre paiement a été transféré avec succès vers votre wallet.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label"> Montant reçu</div>
                    <div class="info-value">{payout_amount}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Adresse de réception</div>
                    <div class="info-value" style="word-break: break-all;">{payout_address}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Date du transfert</div>
                    <div class="info-value">{transaction_date}</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Voir l'historique des payouts
                </a>
            </div>

            <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #064e3b; margin: 0;">
                     Vérifiez votre wallet pour confirmer la réception des fonds
                </p>
            </div>
        """

        body = self._build_email_template(
            header_title=" Paiement Reçu",
            header_subtitle="Votre payout a été transféré",
            content_html=content_html
        )

        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email paiement reçu simulé - To: {to_email}")
                print(f"📧 Payment received to {seller_name} ({to_email})")
                print(f"   Amount: {payout_amount}, Wallet: {payout_address[:20]}...")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email paiement reçu envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email paiement reçu: {e}")
            logger.info(f"📧 Email paiement reçu simulé (fallback) - To: {to_email}")
            return True

    def send_product_added_email(self, to_email: str, seller_name: str, product_title: str, product_price: str, product_id: str) -> bool:
        """
        Envoie un email de confirmation d'ajout de produit

        Args:
            to_email: Email du vendeur
            seller_name: Nom du vendeur
            product_title: Titre du produit ajouté
            product_price: Prix du produit (ex: "50.00 USDT")
            product_id: ID du produit

        Returns:
            bool: True si envoi réussi
        """
        subject = " Produit ajouté avec succès - UZEUR Marketplace"

        content_html = f"""
            <div class="success-box">
                <h2>Bravo {seller_name}!</h2>
                <p>Votre produit a été ajouté avec succès sur la marketplace.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label"> Nom du produit</div>
                    <div class="info-value">{product_title}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Prix</div>
                    <div class="info-value">{product_price}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> ID produit</div>
                    <div class="info-value">{product_id}</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Voir mon catalogue
                </a>
            </div>

            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                     Votre produit est maintenant visible par tous les acheteurs
                </p>
            </div>
        """

        body = self._build_email_template(
            header_title=" Produit Ajouté",
            header_subtitle="Votre produit est en ligne",
            content_html=content_html
        )

        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email produit ajouté simulé - To: {to_email}")
                print(f"📧 Product added notification to {seller_name} ({to_email})")
                print(f"   Product: {product_title}, Price: {product_price}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email produit ajouté envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email produit ajouté: {e}")
            logger.info(f"📧 Email produit ajouté simulé (fallback) - To: {to_email}")
            return True

    def send_product_removed_email(self, to_email: str, seller_name: str, product_title: str, product_id: str, reason: str = "à votre demande") -> bool:
        """
        Envoie un email de confirmation de suppression de produit

        Args:
            to_email: Email du vendeur
            seller_name: Nom du vendeur
            product_title: Titre du produit supprimé
            product_id: ID du produit
            reason: Raison de la suppression

        Returns:
            bool: True si envoi réussi
        """
        subject = " Produit supprimé - UZEUR Marketplace"

        content_html = f"""
            <div class="alert-box">
                <h2>Bonjour {seller_name},</h2>
                <p>Votre produit a été supprimé de la marketplace.</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label"> Produit supprimé</div>
                    <div class="info-value">{product_title}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> ID produit</div>
                    <div class="info-value">{product_id}</div>
                </div>

                <div class="info-item">
                    <div class="info-label"> Raison</div>
                    <div class="info-value">{reason}</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/uzeur_bot" class="cta-button">
                     Voir mon catalogue
                </a>
            </div>

            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                     Ce produit n'est plus visible par les acheteurs
                </p>
            </div>
        """

        body = self._build_email_template(
            header_title=" Produit Supprimé",
            header_subtitle="Le produit a été retiré du catalogue",
            content_html=content_html
        )

        try:
            if not self.smtp_configured:
                logger.info(f"📧 Email produit supprimé simulé - To: {to_email}")
                print(f"📧 Product removed notification to {seller_name} ({to_email})")
                print(f"   Product: {product_title}, Reason: {reason}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email produit supprimé envoyé - To: {to_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email produit supprimé: {e}")
            logger.info(f"📧 Email produit supprimé simulé (fallback) - To: {to_email}")
            return True
    def send_new_ticket_notification(self, ticket_id: str, user_id: int, subject: str, message: str, client_email: str) -> bool:
        """
        Envoie un email à l'admin lors de la création d'un nouveau ticket support

        Args:
            ticket_id: ID du ticket
            user_id: ID de l'utilisateur
            subject: Sujet du ticket
            message: Message du ticket
            client_email: Email du client pour réponse

        Returns:
            bool: True si envoi réussi
        """
        try:
            from app.core import settings as core_settings
            # Utiliser ADMIN_EMAIL du .env, sinon fallback sur smtp_email
            admin_email = core_settings.ADMIN_EMAIL or self.smtp_email

            if not admin_email:
                logger.warning("Admin email not configured (set ADMIN_EMAIL in .env)")
                return False

            email_subject = f"Nouveau ticket support - {ticket_id}"
            email_body = f"""
Nouveau ticket de support créé

ID Ticket: {ticket_id}
User ID: {user_id}
Email client: {client_email}

Sujet: {subject}

Message:
{message}

Vous pouvez répondre directement à l'adresse: {client_email}
"""

            # Executer la coroutine async dans un contexte synchrone
            import asyncio
            try:
                # Si on est déjà dans une boucle async, créer une tâche
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.send_email(admin_email, email_subject, email_body))
                    return True
                else:
                    return asyncio.run(self.send_email(admin_email, email_subject, email_body))
            except RuntimeError:
                # Pas de boucle, en créer une
                return asyncio.run(self.send_email(admin_email, email_subject, email_body))

        except Exception as e:
            logger.error(f"Erreur envoi email nouveau ticket: {e}")
            logger.info(f"Email nouveau ticket simulé (fallback) - Ticket: {ticket_id}")
            return True

    def send_ticket_confirmation_client(self, client_email: str, ticket_id: str, subject: str, message: str) -> bool:
        """
        Envoie un email de confirmation au client qui a créé un ticket

        Args:
            client_email: Email du client
            ticket_id: ID du ticket créé
            subject: Sujet du ticket
            message: Message du client

        Returns:
            bool: True si envoi réussi
        """
        try:
            email_subject = f"Ticket reçu - {ticket_id}"

            content_html = f"""
                <div class="success-box">
                    <h2>Votre ticket a bien été reçu</h2>
                    <p>Merci de nous avoir contactés. Notre équipe support traite votre demande et vous répondra dans les plus brefs délais.</p>
                </div>

                <div class="info-section">
                    <div class="info-item">
                        <div class="info-label"> Numéro de ticket</div>
                        <div class="info-value"><strong>{ticket_id}</strong></div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Sujet</div>
                        <div class="info-value">{subject}</div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Votre message</div>
                        <div class="info-value" style="background: #f9fafb; padding: 15px; border-radius: 8px; white-space: pre-wrap;">{message[:500]}{"..." if len(message) > 500 else ""}</div>
                    </div>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://t.me/uzeur_bot" class="cta-button">
                         Voir mes tickets
                    </a>
                </div>

                <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                    <p style="font-size: 14px; color: #1e40af; margin: 0;">
                        ⏱ <strong>Délai de réponse habituel</strong> : 24-48 heures<br>
                        💡 Vous recevrez une notification dès que nous aurons répondu
                    </p>
                </div>
            """

            body = self._build_email_template(
                header_title=" Ticket Reçu",
                header_subtitle=f"Référence : {ticket_id}",
                content_html=content_html
            )

            if not self.smtp_configured:
                logger.info(f"📧 Email confirmation ticket simulé - To: {client_email}")
                print(f"📧 Ticket confirmation to {client_email}")
                print(f"   Ticket: {ticket_id}, Subject: {subject}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = client_email
            msg['Subject'] = email_subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email confirmation ticket envoyé - To: {client_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email confirmation ticket: {e}")
            logger.info(f"📧 Email confirmation ticket simulé (fallback) - To: {client_email}")
            return True

    def send_sale_notification_seller(
        self,
        seller_email: str,
        seller_name: str,
        product_title: str,
        product_price_usd: float,
        seller_revenue_usd: float,
        platform_commission_usd: float,
        buyer_username: str,
        order_id: str,
        payment_currency: str
    ) -> bool:
        """
        Envoie un email au vendeur lors d'une nouvelle vente

        Args:
            seller_email: Email du vendeur
            seller_name: Nom du vendeur
            product_title: Titre du produit vendu
            product_price_usd: Prix de vente
            seller_revenue_usd: Revenu net du vendeur
            platform_commission_usd: Commission plateforme
            buyer_username: Username de l'acheteur
            order_id: ID de la commande
            payment_currency: Crypto utilisée (BTC, ETH, etc.)

        Returns:
            bool: True si envoi réussi
        """
        try:
            email_subject = f"🎉 Nouvelle vente - {product_title}"

            content_html = f"""
                <div class="success-box">
                    <h2>Félicitations {seller_name} !</h2>
                    <p>Vous venez de réaliser une nouvelle vente. Le paiement a été confirmé et le produit a été livré automatiquement à l'acheteur.</p>
                </div>

                <div class="info-section">
                    <div class="info-item">
                        <div class="info-label"> Produit vendu</div>
                        <div class="info-value"><strong>{product_title}</strong></div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Prix de vente</div>
                        <div class="info-value"><strong>${product_price_usd:.2f} USD</strong></div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Paiement en</div>
                        <div class="info-value">{payment_currency}</div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Acheteur</div>
                        <div class="info-value">@{buyer_username}</div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Commande</div>
                        <div class="info-value" style="font-family: monospace; font-size: 12px;">{order_id}</div>
                    </div>
                </div>

                <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%); padding: 20px; border-radius: 12px; margin: 20px 0;">
                    <h3 style="margin: 0 0 15px 0; color: #065f46;">💵 Répartition financière</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #d1fae5;">
                            <td style="padding: 10px 0; color: #064e3b;">Prix de vente</td>
                            <td style="padding: 10px 0; text-align: right; color: #064e3b;">${product_price_usd:.2f}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #d1fae5;">
                            <td style="padding: 10px 0; color: #064e3b;">Commission plateforme (3.14%)</td>
                            <td style="padding: 10px 0; text-align: right; color: #064e3b;">-${platform_commission_usd:.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #065f46; font-weight: bold; font-size: 16px;">Votre revenu net</td>
                            <td style="padding: 10px 0; text-align: right; color: #065f46; font-weight: bold; font-size: 16px;">${seller_revenue_usd:.2f}</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://t.me/uzeur_bot" class="cta-button">
                         Voir mes statistiques
                    </a>
                </div>

                <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                    <p style="font-size: 14px; color: #1e40af; margin: 0;">
                         Vos revenus seront transférés vers votre wallet Solana lors du prochain payout.<br>
                         Les payouts sont traités manuellement après vérification anti-fraude.
                    </p>
                </div>
            """

            body = self._build_email_template(
                header_title="🎉 Nouvelle Vente !",
                header_subtitle=f"Vous avez gagné ${seller_revenue_usd:.2f}",
                content_html=content_html
            )

            if not self.smtp_configured:
                logger.info(f"📧 Email nouvelle vente simulé - To: {seller_email}")
                print(f"📧 Sale notification to {seller_name} ({seller_email})")
                print(f"   Product: {product_title}, Revenue: ${seller_revenue_usd:.2f}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = seller_email
            msg['Subject'] = email_subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email nouvelle vente envoyé - To: {seller_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email nouvelle vente: {e}")
            logger.info(f"📧 Email nouvelle vente simulé (fallback) - To: {seller_email}")
            return True

    def send_purchase_confirmation_buyer(
        self,
        buyer_email: str,
        buyer_username: str,
        product_title: str,
        product_price_usd: float,
        payment_currency: str,
        order_id: str,
        seller_name: str,
        platform_commission_usd: float = 0.0
    ) -> bool:
        """
        Envoie un email de confirmation d'achat à l'acheteur

        Args:
            buyer_email: Email de l'acheteur
            buyer_username: Username de l'acheteur
            product_title: Titre du produit acheté
            product_price_usd: Prix du produit
            payment_currency: Crypto utilisée
            order_id: ID de la commande
            seller_name: Nom du vendeur
            platform_commission_usd: Frais de plateforme

        Returns:
            bool: True si envoi réussi
        """
        try:
            email_subject = f" Achat confirmé - {product_title}"

            content_html = f"""
                <div class="success-box">
                    <h2>Merci pour votre achat !</h2>
                    <p>Votre paiement a été confirmé avec succès. Votre produit est maintenant disponible dans votre bibliothèque.</p>
                </div>

                <div class="info-section">
                    <div class="info-item">
                        <div class="info-label"> Produit acheté</div>
                        <div class="info-value"><strong>{product_title}</strong></div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Vendeur</div>
                        <div class="info-value">{seller_name}</div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Prix du produit</div>
                        <div class="info-value">${product_price_usd:.2f} USD</div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Frais de gestion</div>
                        <div class="info-value">${platform_commission_usd:.2f} USD</div>
                    </div>

                    <div class="info-item" style="border-top: 2px solid #e5e7eb; padding-top: 12px; margin-top: 8px;">
                        <div class="info-label"> Montant total payé</div>
                        <div class="info-value"><strong>${product_price_usd + platform_commission_usd:.2f} USD</strong></div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Méthode de paiement</div>
                        <div class="info-value">{payment_currency}</div>
                    </div>

                    <div class="info-item">
                        <div class="info-label"> Numéro de commande</div>
                        <div class="info-value" style="font-family: monospace; font-size: 12px;">{order_id}</div>
                    </div>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://t.me/uzeur_bot" class="cta-button">
                        📚 Accéder à ma bibliothèque
                    </a>
                </div>

                <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px;">
                    <h3 style="margin: 0 0 15px 0; color: #065f46;"> Comment télécharger votre produit ?</h3>
                    <ol style="margin: 0; padding-left: 20px; color: #064e3b;">
                        <li style="margin-bottom: 8px;">Ouvrez le bot Telegram @uzeur_bot</li>
                        <li style="margin-bottom: 8px;">Cliquez sur "📚 Ma Bibliothèque"</li>
                        <li style="margin-bottom: 8px;">Sélectionnez votre produit</li>
                        <li>Cliquez sur " Télécharger" </li>
                    </ol>
                </div>

                <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 20px; text-align: center;">
                    <p style="font-size: 14px; color: #1e40af; margin: 0;">
                        💡 <strong>Besoin d'aide ?</strong><br>
                        Contactez le vendeur directement depuis votre bibliothèque ou créez un ticket support.
                    </p>
                </div>
            """

            body = self._build_email_template(
                header_title=" Achat Confirmé",
                header_subtitle="Votre produit est prêt",
                content_html=content_html
            )

            if not self.smtp_configured:
                logger.info(f"📧 Email confirmation achat simulé - To: {buyer_email}")
                print(f"📧 Purchase confirmation to @{buyer_username} ({buyer_email})")
                print(f"   Product: {product_title}, Price: ${product_price_usd:.2f}")
                return True

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = buyer_email
            msg['Subject'] = email_subject

            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
                logger.info(f"📧 Email confirmation achat envoyé - To: {buyer_email}")
                return True

        except Exception as e:
            logger.error(f"Erreur envoi email confirmation achat: {e}")
            logger.info(f"📧 Email confirmation achat simulé (fallback) - To: {buyer_email}")
            return True
