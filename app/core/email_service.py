"""
Email Service - Version API Mailjet (Contourne les blocages SMTP Railway)
Utilise le port 443 (HTTPS) qui est toujours ouvert.
"""
import logging
import asyncio
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

class EmailService:
    """Service d'envoi d'emails via API"""

    def __init__(self):
        """Initialiser le service email avec les clés API"""
        try:
            # Import différé pour éviter les cycles d'import
            from app.core.settings import settings
            
            # Chez Mailjet : SMTP_USERNAME = API Key, SMTP_PASSWORD = Secret Key
            self.api_key = settings.SMTP_USERNAME
            self.api_secret = settings.SMTP_PASSWORD
            self.from_email = settings.FROM_EMAIL
            self.from_name = settings.FROM_NAME
            
            # On vérifie qu'on a bien les credentials
            self.configured = bool(self.api_key and self.api_secret and self.from_email)

            if self.configured:
                logger.info("✅ EmailService (API Mode) initialisé avec succès.")
            else:
                logger.warning("⚠️ Credentials Email manquants. Mode simulation activé.")

        except Exception as e:
            logger.error(f"Erreur configuration EmailService: {e}")
            self.configured = False

    def _send_smtp_blocking(self, to_email: str, subject: str, body: str) -> bool:
        """
        Envoi bloquant via l'API Mailjet v3.1 (HTTP POST).
        Cette fonction est exécutée dans un thread séparé.
        """
        if not self.configured:
            logger.info(f"📧 [SIMULATION] Email vers {to_email} : {subject}")
            return True

        url = "https://api.mailjet.com/v3.1/send"
        
        # Structure JSON spécifique à Mailjet
        payload = {
            "Messages": [
                {
                    "From": {
                        "Email": self.from_email,
                        "Name": self.from_name
                    },
                    "To": [
                        {
                            "Email": to_email
                        }
                    ],
                    "Subject": subject,
                    "HTMLPart": body,
                    "TextPart": "Veuillez activer l'HTML pour voir ce message."
                }
            ]
        }

        try:
            # Envoi de la requête HTTP (Port 443 - Jamais bloqué)
            response = requests.post(
                url,
                auth=HTTPBasicAuth(self.api_key, self.api_secret),
                json=payload,
                timeout=10 # Timeout de 10s pour ne pas bloquer si Mailjet rame
            )

            if response.status_code == 200:
                logger.info(f"✅ Email API envoyé avec succès à {to_email}")
                return True
            else:
                # Log l'erreur exacte renvoyée par Mailjet
                logger.error(f"❌ Erreur API Mailjet ({response.status_code}): {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Exception critique envoi API: {e}")
            return False

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Envoie un email (wrapper async pour ne pas bloquer le serveur)
        
        Args:
            to_email: Adresse email destinataire
            subject: Sujet de l'email
            body: Corps du message

        Returns:
            bool: True si envoi réussi
        """
        try:
            if not self.configured:
                logger.info(f"📧 Email simulé - To: {to_email}, Subject: {subject}")
                return True

            # On utilise run_in_executor pour que la requête HTTP (qui prend 0.5s)
            # ne bloque pas les autres utilisateurs du bot
            return await asyncio.to_thread(self._send_smtp_blocking, to_email, subject, body)

        except Exception as e:
            logger.error(f"Erreur envoi email (Async): {e}")
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

    async def send_seller_welcome_email(self, to_email: str, seller_name: str, solana_address: str) -> bool:
        """
        Envoie un email de bienvenue au nouveau vendeur
        """
        subject = "🎉 Bienvenue sur UZEUR Marketplace !"

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

        body = self._build_email_template(
            header_title=" Bienvenue sur UZEUR !",
            header_subtitle="Votre compte vendeur est actif",
            content_html=content_html
        )

        # Utilisation de la nouvelle méthode API async
        return await self.send_email(to_email, subject, body)

    async def send_seller_login_notification(self, to_email: str, seller_name: str, login_time: str) -> bool:
        """
        Envoie un email de notification de connexion vendeur
        """
        subject = " Nouvelle connexion à votre compte vendeur UZEUR"

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

        body = self._build_email_template(
            header_title=" Connexion Détectée",
            header_subtitle="Votre compte vendeur a été connecté",
            content_html=content_html
        )

        return await self.send_email(to_email, subject, body)

    async def send_product_suspended_notification(self, to_email: str, seller_name: str, product_title: str, reason: str, can_appeal: bool = True) -> bool:
        """
        Envoie un email de notification de suspension de produit
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
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: sans-serif; background: #fafbfc; color: #334155; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 16px; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #ef4444 0%, #f87171 50%, #fb923c 100%); padding: 40px 30px; text-align: center; }}
        .header h1 {{ font-size: 32px; color: white; margin-bottom: 8px; }}
        .header p {{ color: rgba(255, 255, 255, 0.9); }}
        .content {{ padding: 40px 30px; }}
        .alert-box {{ background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .info-section {{ background: #f3f4f6; padding: 20px; border-radius: 12px; margin-bottom: 24px; }}
        .info-item {{ margin-bottom: 16px; }}
        .info-label {{ font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; }}
        .info-value {{ font-size: 16px; font-weight: 600; color: #1e293b; }}
        .reason-box {{ background: #fef2f2; border: 2px solid #fecaca; padding: 20px; border-radius: 12px; margin: 24px 0; }}
        .cta-button {{ display: inline-block; background: #8b5cf6; color: white; padding: 16px 32px; border-radius: 12px; text-decoration: none; }}
        .footer {{ background: #f3f4f6; padding: 30px; text-align: center; }}
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
                <p>Votre produit a été suspendu par notre équipe de modération.</p>
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
                <a href="https://t.me/uzeur_bot" class="cta-button">Accéder au Dashboard</a>
            </div>
            {appeal_section}
        </div>
        <div class="footer">
            <p><strong>UZEUR Marketplace</strong></p>
        </div>
    </div>
</body>
</html>
        """
        
        return await self.send_email(to_email, subject, body)

    async def send_account_suspended_notification(self, to_email: str, user_name: str, reason: str, duration: str = "indéterminée", is_permanent: bool = False) -> bool:
        """
        Envoie un email de notification de suspension de compte
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
            <div style="background: rgba(139, 92, 246, 0.1); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #64748b; margin: 0;">
                     <strong>Faire appel ?</strong> Contactez le support via /support
                </p>
            </div>
        """ if not is_permanent else """
            <div style="background: rgba(239, 68, 68, 0.1); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #7c2d12; margin: 0;">
                    ⚠️ Cette suspension est <strong>permanente</strong>.
                </p>
            </div>
        """

        body = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: sans-serif; background: #fafbfc; color: #334155; }}
        .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 16px; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #dc2626 0%, #ef4444 50%, #f87171 100%); padding: 40px 30px; text-align: center; color: white; }}
        .content {{ padding: 40px 30px; }}
        .alert-box {{ background: rgba(220, 38, 38, 0.1); border-left: 4px solid #dc2626; padding: 20px; margin-bottom: 30px; }}
        .info-section {{ background: #f3f4f6; padding: 20px; border-radius: 12px; margin-bottom: 24px; }}
        .info-item {{ margin-bottom: 10px; }}
        .reason-box {{ background: #fef2f2; border: 2px solid #fecaca; padding: 20px; border-radius: 12px; }}
        .cta-button {{ display: inline-block; background: #8b5cf6; color: white; padding: 16px 32px; border-radius: 12px; text-decoration: none; }}
        .footer {{ background: #f3f4f6; padding: 30px; text-align: center; }}
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
        </div>
    </div>
</body>
</html>
        """

        return await self.send_email(to_email, subject, body)

    async def send_sale_confirmation_email(self, to_email: str, seller_name: str, product_title: str, buyer_name: str, sale_amount: str, sale_date: str) -> bool:
        """
        Envoie un email de confirmation de vente au vendeur
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

        return await self.send_email(to_email, subject, body)

    async def send_payment_received_email(self, to_email: str, seller_name: str, payout_amount: str, payout_address: str, transaction_date: str) -> bool:
        """
        Envoie un email de confirmation de paiement reçu au vendeur
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

        return await self.send_email(to_email, subject, body)

    async def send_product_added_email(self, to_email: str, seller_name: str, product_title: str, product_price: str, product_id: str) -> bool:
        """
        Envoie un email de confirmation d'ajout de produit
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

        return await self.send_email(to_email, subject, body)

    async def send_product_removed_email(self, to_email: str, seller_name: str, product_title: str, product_id: str, reason: str = "à votre demande") -> bool:
        """
        Envoie un email de confirmation de suppression de produit
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

        return await self.send_email(to_email, subject, body)

    async def send_new_ticket_notification(self, ticket_id: str, user_id: int, subject: str, message: str, client_email: str) -> bool:
        """
        Envoie un email à l'admin lors de la création d'un nouveau ticket support
        """
        try:
            from app.core import settings as core_settings
            admin_email = core_settings.ADMIN_EMAIL or self.smtp_email

            if not admin_email:
                logger.warning("Admin email not configured")
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
            # Pas besoin de template HTML complexe pour l'admin, texte brut (wrap dans HTML pour Mailjet)
            return await self.send_email(admin_email, email_subject, f"<pre>{email_body}</pre>")

        except Exception as e:
            logger.error(f"Erreur envoi email nouveau ticket: {e}")
            return False

    async def send_ticket_confirmation_client(self, client_email: str, ticket_id: str, subject: str, message: str) -> bool:
        """
        Envoie un email de confirmation au client qui a créé un ticket
        """
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

        return await self.send_email(client_email, email_subject, body)

    async def send_sale_notification_seller(
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
        """
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

        return await self.send_email(seller_email, email_subject, body)

    async def send_purchase_confirmation_buyer(
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
        """
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

        return await self.send_email(buyer_email, email_subject, body)
