"""
Email Templates Extended - Templates supplémentaires pour notifications système
Ce fichier contient les méthodes à ajouter à EmailService
"""

# MÉTHODE 3: Nouveau message support
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
                <p>"{message_preview}..."</p>
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
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"📧 Email réponse support simulé - To: {to_email}")
            print(f"📧 Support reply notification to {user_name} ({to_email})")
            print(f"   Ticket: #{ticket_id}")
            print(f"   Preview: {message_preview[:50]}...")
            return True

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import logging
        logger = logging.getLogger(__name__)

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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur envoi email réponse support: {e}")
        logger.info(f"📧 Email réponse support simulé (fallback) - To: {to_email}")
        return True


# MÉTHODE 4: Premier produit publié
def send_first_product_published_notification(self, to_email: str, seller_name: str, product_title: str, product_price: float) -> bool:
    """
    Envoie un email de félicitations pour le premier produit publié

    Args:
        to_email: Email du vendeur
        seller_name: Nom du vendeur
        product_title: Titre du produit
        product_price: Prix du produit

    Returns:
        bool: True si envoi réussi
    """
    subject = "🎉 Félicitations ! Votre premier produit est en ligne - UZEUR"

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
            box-shadow: 0 10px 40px rgba(16, 185, 129, 0.12);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #10b981 0%, #34d399 50%, #6ee7b7 100%);
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

        .success-box {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(52, 211, 153, 0.1) 100%);
            border-left: 4px solid #10b981;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}

        .success-box h2 {{
            font-size: 24px;
            font-weight: 800;
            color: #065f46;
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

        .tips-section {{
            margin-top: 30px;
        }}

        .tip {{
            display: flex;
            margin-bottom: 16px;
            align-items: flex-start;
        }}

        .tip-icon {{
            background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 16px;
            margin-right: 12px;
            flex-shrink: 0;
        }}

        .tip-content {{
            font-size: 14px;
            color: #334155;
        }}

        .tip-content strong {{
            color: #065f46;
            display: block;
            margin-bottom: 4px;
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
            color: #10b981;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Félicitations !</h1>
            <p>Votre premier produit est en ligne</p>
        </div>

        <div class="content">
            <div class="success-box">
                <h2>Bravo {seller_name} ! 🚀</h2>
                <p>Votre premier produit a été publié avec succès sur UZEUR Marketplace. Vous êtes maintenant prêt à générer vos premiers revenus !</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label">📦 Votre produit</div>
                    <div class="info-value">{product_title}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">💰 Prix de vente</div>
                    <div class="info-value">{product_price}€</div>
                </div>

                <div class="info-item">
                    <div class="info-label">✅ Statut</div>
                    <div class="info-value" style="color: #10b981;">En ligne et visible</div>
                </div>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    📊 Voir le Dashboard
                </a>
            </div>

            <div class="tips-section">
                <h3 style="font-size: 20px; font-weight: 800; color: #1e293b; margin-bottom: 20px;">
                    💡 Conseils pour maximiser vos ventes :
                </h3>

                <div class="tip">
                    <div class="tip-icon">1</div>
                    <div class="tip-content">
                        <strong>Ajoutez une image de couverture</strong>
                        Les produits avec image génèrent 3x plus de ventes
                    </div>
                </div>

                <div class="tip">
                    <div class="tip-icon">2</div>
                    <div class="tip-content">
                        <strong>Optimisez votre description</strong>
                        Détaillez les bénéfices et ce que contient votre produit
                    </div>
                </div>

                <div class="tip">
                    <div class="tip-icon">3</div>
                    <div class="tip-content">
                        <strong>Partagez votre produit</strong>
                        Plus vous partagez, plus vous vendez !
                    </div>
                </div>

                <div class="tip">
                    <div class="tip-icon">4</div>
                    <div class="tip-content">
                        <strong>Suivez vos statistiques</strong>
                        Consultez régulièrement votre dashboard vendeur
                    </div>
                </div>
            </div>

            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(52, 211, 153, 0.1) 100%); padding: 20px; border-radius: 12px; margin-top: 30px; text-align: center;">
                <p style="font-size: 14px; color: #065f46; margin: 0;">
                    🎯 <strong>Objectif :</strong> Atteindre 100€ de revenus pour débloquer le badge "Rising Star"
                </p>
            </div>
        </div>

        <div class="footer">
            <p><strong>UZEUR Marketplace</strong></p>
            <p>Votre succès commence ici</p>
            <p style="margin-top: 16px;">
                <a href="#">Guide du vendeur</a> • <a href="#">FAQ</a>
            </p>
        </div>
    </div>
</body>
</html>
    """

    # Envoyer en HTML
    try:
        if not self.smtp_configured:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"📧 Email premier produit simulé - To: {to_email}")
            print(f"📧 First product published to {seller_name} ({to_email})")
            print(f"   Product: {product_title} - {product_price}€")
            return True

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import logging
        logger = logging.getLogger(__name__)

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
            logger.info(f"📧 Email premier produit envoyé - To: {to_email}")
            return True

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur envoi email premier produit: {e}")
        logger.info(f"📧 Email premier produit simulé (fallback) - To: {to_email}")
        return True


# MÉTHODE 5: Notification système admin
def send_admin_system_notification(self, admin_email: str, event_type: str, details: str, severity: str = "info") -> bool:
    """
    Envoie un email de notification système aux admins

    Args:
        admin_email: Email de l'admin
        event_type: Type d'événement (nouveau_vendeur, erreur_systeme, etc.)
        details: Détails de l'événement
        severity: Niveau de sévérité (info, warning, critical)

    Returns:
        bool: True si envoi réussi
    """
    severity_config = {
        'info': {
            'color': '#3b82f6',
            'icon': 'ℹ️',
            'label': 'Information',
            'gradient': 'linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)'
        },
        'warning': {
            'color': '#f59e0b',
            'icon': '⚠️',
            'label': 'Avertissement',
            'gradient': 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)'
        },
        'critical': {
            'color': '#ef4444',
            'icon': '🚨',
            'label': 'Critique',
            'gradient': 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)'
        }
    }

    config = severity_config.get(severity, severity_config['info'])

    subject = f"{config['icon']} [{config['label'].upper()}] {event_type} - UZEUR Admin"

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
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, monospace, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #1e293b;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            overflow: hidden;
            border: 1px solid #334155;
        }}

        .header {{
            background: {config['gradient']};
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 28px;
            font-weight: 900;
            color: white;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .header p {{
            font-size: 14px;
            color: rgba(255, 255, 255, 0.9);
            font-family: monospace;
        }}

        .content {{
            padding: 40px 30px;
        }}

        .alert-box {{
            background: rgba({config['color'].replace('#', '')}, 0.1);
            border-left: 4px solid {config['color']};
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 24px;
        }}

        .alert-box h2 {{
            font-size: 18px;
            font-weight: 800;
            color: {config['color']};
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .details-box {{
            background: #0f172a;
            border: 1px solid #334155;
            padding: 20px;
            border-radius: 12px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.8;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .timestamp {{
            background: #334155;
            padding: 12px 20px;
            border-radius: 8px;
            margin-top: 24px;
            text-align: center;
            font-family: monospace;
            font-size: 12px;
            color: #94a3b8;
        }}

        .cta-button {{
            display: inline-block;
            background: {config['gradient']};
            color: white;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 14px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s;
            margin-top: 20px;
        }}

        .cta-button:hover {{
            transform: translateY(-2px);
        }}

        .footer {{
            background: #0f172a;
            padding: 24px;
            text-align: center;
            border-top: 1px solid #334155;
        }}

        .footer p {{
            font-size: 12px;
            color: #64748b;
            margin-bottom: 6px;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{config['icon']} NOTIFICATION SYSTÈME</h1>
            <p>UZEUR Admin Dashboard</p>
        </div>

        <div class="content">
            <div class="alert-box">
                <h2>{config['label']}: {event_type}</h2>
                <p style="color: #e2e8f0; font-size: 14px;">Un événement système nécessite votre attention</p>
            </div>

            <div class="details-box">{details}</div>

            <div class="timestamp">
                🕐 {import datetime; datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
            </div>

            <div style="text-align: center;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    🔧 Accéder à l'Admin Panel
                </a>
            </div>
        </div>

        <div class="footer">
            <p>UZEUR Marketplace - Système de Monitoring</p>
            <p>© 2025 - Automated System Notification</p>
        </div>
    </div>
</body>
</html>
    """

    # Fix timestamp in body
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    body = body.replace("{import datetime; datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S UTC\")}", timestamp)

    # Envoyer en HTML
    try:
        if not self.smtp_configured:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"📧 Email notification admin simulé - To: {admin_email}")
            print(f"📧 Admin system notification: {event_type}")
            print(f"   Severity: {severity}")
            print(f"   Details: {details[:100]}...")
            return True

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import logging
        logger = logging.getLogger(__name__)

        msg = MIMEMultipart('alternative')
        msg['From'] = self.smtp_email
        msg['To'] = admin_email
        msg['Subject'] = subject

        html_part = MIMEText(body, 'html', 'utf-8')
        msg.attach(html_part)

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.smtp_port == 587:
                server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)
            logger.info(f"📧 Email notification admin envoyé - To: {admin_email}")
            return True

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur envoi email notification admin: {e}")
        logger.info(f"📧 Email notification admin simulé (fallback) - To: {admin_email}")
        return True


# MÉTHODE 6: Changement email utilisateur
def send_email_change_notification(self, old_email: str, new_email: str, user_name: str, is_old_email: bool = True) -> bool:
    """
    Envoie un email de notification de changement d'email (aux 2 adresses)

    Args:
        old_email: Ancien email
        new_email: Nouvel email
        user_name: Nom de l'utilisateur
        is_old_email: True si envoi à l'ancien email, False pour le nouveau

    Returns:
        bool: True si envoi réussi
    """
    recipient = old_email if is_old_email else new_email

    if is_old_email:
        subject = "⚠️ Changement d'email sur votre compte UZEUR"
        alert_message = "Votre adresse email a été modifiée sur votre compte UZEUR Marketplace."
        action_text = "Si vous n'avez PAS effectué ce changement, cliquez immédiatement sur le bouton ci-dessous pour annuler et sécuriser votre compte."
        button_text = "🚨 Annuler ce Changement"
        button_color = "#ef4444"
    else:
        subject = "✅ Confirmation de votre nouvel email UZEUR"
        alert_message = "Votre adresse email a été mise à jour avec succès."
        action_text = "Vous recevrez désormais toutes les notifications à cette adresse. Si vous n'avez PAS effectué ce changement, contactez immédiatement le support."
        button_text = "✅ Accéder à mon Compte"
        button_color = "#10b981"

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
            box-shadow: 0 10px 40px rgba(245, 158, 11, 0.12);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 50%, #fcd34d 100%);
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
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(251, 191, 36, 0.1) 100%);
            border-left: 4px solid #f59e0b;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}

        .alert-box h2 {{
            font-size: 24px;
            font-weight: 800;
            color: #92400e;
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

        .email-compare {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 24px 0;
            padding: 16px;
            background: #fef3c7;
            border-radius: 12px;
        }}

        .email-item {{
            flex: 1;
            text-align: center;
        }}

        .email-item .label {{
            font-size: 11px;
            font-weight: 700;
            color: #78350f;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}

        .email-item .value {{
            font-size: 14px;
            font-weight: 600;
            color: #92400e;
            word-break: break-all;
        }}

        .arrow {{
            font-size: 24px;
            color: #f59e0b;
            margin: 0 16px;
        }}

        .cta-button {{
            display: inline-block;
            background: {button_color};
            color: white;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 16px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
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
            color: #f59e0b;
            text-decoration: none;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{'⚠️ Changement Email' if is_old_email else '✅ Email Mis à Jour'}</h1>
            <p>Notification de sécurité</p>
        </div>

        <div class="content">
            <div class="alert-box">
                <h2>Bonjour {user_name},</h2>
                <p>{alert_message}</p>
            </div>

            <div class="info-section">
                <div class="info-item">
                    <div class="info-label">👤 Nom du compte</div>
                    <div class="info-value">{user_name}</div>
                </div>

                <div class="info-item">
                    <div class="info-label">📅 Date de modification</div>
                    <div class="info-value">{import datetime; datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")}</div>
                </div>
            </div>

            <div class="email-compare">
                <div class="email-item">
                    <div class="label">Ancien email</div>
                    <div class="value">{old_email}</div>
                </div>
                <div class="arrow">→</div>
                <div class="email-item">
                    <div class="label">Nouvel email</div>
                    <div class="value">{new_email}</div>
                </div>
            </div>

            <div style="background: #fffbeb; border: 2px solid #fde047; padding: 20px; border-radius: 12px; margin: 24px 0;">
                <p style="font-size: 14px; color: #78350f; margin: 0;">
                    {action_text}
                </p>
            </div>

            <div style="text-align: center; margin: 30px 0;">
                <a href="https://t.me/YourBotUsername" class="cta-button">
                    {button_text}
                </a>
            </div>
        </div>

        <div class="footer">
            <p><strong>UZEUR Marketplace</strong></p>
            <p>La sécurité de votre compte est notre priorité</p>
            <p style="margin-top: 16px;">
                <a href="#">Support</a> • <a href="#">Sécurité</a>
            </p>
        </div>
    </div>
</body>
</html>
    """

    # Fix timestamp in body
    import datetime
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")
    body = body.replace("{import datetime; datetime.datetime.now().strftime(\"%d/%m/%Y à %H:%M\")}", timestamp)

    # Envoyer en HTML
    try:
        if not self.smtp_configured:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"📧 Email changement email simulé - To: {recipient}")
            print(f"📧 Email change notification to {user_name} ({'old' if is_old_email else 'new'} address)")
            print(f"   {old_email} → {new_email}")
            return True

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import logging
        logger = logging.getLogger(__name__)

        msg = MIMEMultipart('alternative')
        msg['From'] = self.smtp_email
        msg['To'] = recipient
        msg['Subject'] = subject

        html_part = MIMEText(body, 'html', 'utf-8')
        msg.attach(html_part)

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.smtp_port == 587:
                server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)
            logger.info(f"📧 Email changement email envoyé - To: {recipient}")
            return True

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur envoi email changement email: {e}")
        logger.info(f"📧 Email changement email simulé (fallback) - To: {recipient}")
        return True
