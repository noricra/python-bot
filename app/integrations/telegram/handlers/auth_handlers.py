"""Auth Handlers - Authentication and recovery functions with dependency injection"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.core.i18n import t as i18n
from app.core.validation import validate_email

class AuthHandlers:
    def __init__(self, user_repo, email_service):
        self.user_repo = user_repo
        self.email_service = email_service
        # Note: Password recovery removed - authentication via email only

    async def account_recovery_menu(self, bot, query, lang):
        """Menu de récupération de compte"""
        # Reset conflicting states when entering recovery
        bot.reset_conflicting_states(query.from_user.id, keep=set())

        recovery_text = ("""🔐 **ACCOUNT RECOVERY**

Lost your seller account access? We can help you recover it.

**Recovery options:**
• Email recovery (if you provided recovery email)
• Contact support for manual verification

Choose your recovery method:""" if lang == 'en' else """🔐 **RÉCUPÉRATION DE COMPTE**

Vous avez perdu l'accès à votre compte vendeur ? Nous pouvons vous aider.

**Options de récupération :**
• Récupération par email (si vous avez fourni un email)
• Contacter le support pour vérification manuelle

Choisissez votre méthode :""")

        keyboard = [
            [InlineKeyboardButton(
                ("📧 Recover by email" if lang == 'en' else "📧 Récupération par email"),
                callback_data='recovery_by_email'
            )],
            [InlineKeyboardButton(
                ("📞 Contact support" if lang == 'en' else "📞 Contacter le support"),
                callback_data='support_menu'
            )],
            [InlineKeyboardButton(
                ("🔙 Back" if lang == 'en' else "🔙 Retour"),
                callback_data='back_main'
            )]
        ]

        await query.edit_message_text(
            recovery_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def recovery_by_email_prompt(self, bot, query, lang):
        """Prompt pour récupération par email"""
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_for_email'})
        bot.state_manager.update_state(query.from_user.id, waiting_for_email=True, lang=lang)

        prompt_text = ("""📧 **EMAIL RECOVERY**

Enter the email address you used when creating your seller account.

We'll send you a recovery code to regain access.""" if lang == 'en' else """📧 **RÉCUPÉRATION PAR EMAIL**

Entrez l'adresse email que vous avez utilisée lors de la création de votre compte vendeur.

Nous vous enverrons un code de récupération pour retrouver l'accès.""")

        await query.edit_message_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                    callback_data='account_recovery'
                )
            ]]),
            parse_mode='Markdown'
        )

    # Text processing methods
    async def process_recovery_email(self, bot, update, message_text: str):
        """Process récupération par email"""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        lang = bot.get_user_state(user_id).get('lang', 'fr')

        # Start recovery process using new service
        result = self.recovery_service.start_recovery_process(email)

        if result["success"]:
            # Store email for next step
            bot.state_manager.update_state(user_id,
                waiting_for_recovery_code=True,
                waiting_for_email=False,
                recovery_email=email,
                lang=lang
            )

            success_msg = f"{i18n(lang, 'recovery_email_sent')} {email}"
            prompt_msg = f"\n\n{i18n(lang, 'recovery_code_prompt')}"

            await update.message.reply_text(
                success_msg + prompt_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='account_recovery'
                    )
                ]])
            )
        else:
            error_key = result.get("error", "recovery_invalid_email")
            error_message = f"{i18n(lang, error_key)}\n\n📧 **Réessayez avec un email valide :**"
            await update.message.reply_text(
                error_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='account_recovery'
                    )
                ]])
            )
            # Keep waiting_for_email state - don't reset

    async def process_recovery_code(self, bot, update, message_text: str):
        """Process code de récupération"""
        user_id = update.effective_user.id
        user_state = bot.get_user_state(user_id)
        provided_code = message_text.strip()
        email = user_state.get('recovery_email')
        lang = user_state.get('lang', 'fr')

        if not email:
            await update.message.reply_text(i18n(lang, 'recovery_session_expired'))
            bot.reset_user_state_preserve_login(user_id)
            return

        # Validate code using recovery service
        result = self.recovery_service.validate_recovery_code(email, provided_code)

        if result["success"]:
            # Code correct - passer à la saisie du nouveau mot de passe
            bot.state_manager.update_state(user_id,
                waiting_for_recovery_code=False,
                waiting_new_password=True,
                recovery_email=email,
                lang=lang
            )

            await update.message.reply_text(
                i18n(lang, 'recovery_new_password_prompt'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='account_recovery'
                    )
                ]])
            )
        else:
            error_key = result.get("error", "recovery_invalid_code")
            await update.message.reply_text(
                i18n(lang, error_key),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                        callback_data='recovery_by_email'
                    ),
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )
            bot.reset_user_state_preserve_login(user_id)

    async def process_set_new_password(self, bot, update, message_text: str):
        """Définit un nouveau mot de passe après validation du code"""
        user_id = update.effective_user.id
        user_state = bot.get_user_state(user_id)
        new_password = message_text.strip()
        email = user_state.get('recovery_email')
        lang = user_state.get('lang', 'fr')

        if not email:
            await update.message.reply_text(i18n(lang, 'recovery_session_expired'))
            bot.reset_user_state_preserve_login(user_id)
            return

        # Set new password using recovery service
        result = self.recovery_service.set_new_password(email, new_password)

        if result["success"]:
            # Password updated successfully
            bot.reset_user_state_preserve_login(user_id)

            await update.message.reply_text(
                i18n(lang, 'recovery_success'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔐 Login" if lang == 'en' else "🔐 Connexion"),
                        callback_data='seller_login'
                    ),
                    InlineKeyboardButton(
                        ("🏠 Home" if lang == 'en' else "🏠 Accueil"),
                        callback_data='back_main'
                    )
                ]]),
                parse_mode='Markdown'
            )
        else:
            error_key = result.get("error", "recovery_password_too_short")
            await update.message.reply_text(
                i18n(lang, error_key),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )

    async def process_login_email(self, bot, update, message_text: str):
        """Process connexion par email"""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        lang = bot.get_user_state(user_id).get('lang', 'fr')

        if not validate_email(email):
            error_msg = "❌ Invalid email format" if lang == 'en' else "❌ Format email invalide"
            await update.message.reply_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                        callback_data='seller_login'
                    ),
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )
            return

        # Chercher utilisateur par email
        user = self.user_repo.get_user_by_email(email)
        if not user:
            error_msg = "❌ No account found with this email" if lang == 'en' else "❌ Aucun compte avec cet email"
            await update.message.reply_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                        callback_data='seller_login'
                    ),
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )
            bot.reset_user_state_preserve_login(user_id)
            return

        # Vérifier si le compte est suspendu
        seller_name = user.get('seller_name', '')
        if seller_name.startswith('[SUSPENDED]'):
            error_msg = "❌ This account is suspended. Contact support." if lang == 'en' else "❌ Ce compte est suspendu. Contactez le support."
            await update.message.reply_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("📞 Contact support" if lang == 'en' else "📞 Contacter le support"),
                        callback_data='support_menu'
                    ),
                    InlineKeyboardButton(
                        ("🔙 Home" if lang == 'en' else "🔙 Accueil"),
                        callback_data='back_main'
                    )
                ]])
            )
            bot.reset_user_state_preserve_login(user_id)
            return

        # Vérifier si c'est un vendeur
        if not user.get('is_seller'):
            error_msg = "❌ No seller account found with this email" if lang == 'en' else "❌ Aucun compte vendeur avec cet email"
            await update.message.reply_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                        callback_data='seller_login'
                    ),
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )
            bot.reset_user_state_preserve_login(user_id)
            return

        # Générer code de connexion
        import secrets
        login_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])

        bot.state_manager.update_state(user_id,
            login_wait_code=True,
            login_wait_email=False,
            login_code=login_code,
            login_target_user_id=user['user_id'],
            lang=lang
        )

        # Envoyer code par email
        try:
            subject = "Login Code" if lang == 'en' else "Code de Connexion"
            body = f"Your login code: {login_code}" if lang == 'en' else f"Votre code de connexion : {login_code}"

            success = self.email_service.send_email(email, subject, body)
            if success:
                success_msg = f"✅ Login code sent to {email}" if lang == 'en' else f"✅ Code envoyé à {email}"
                await update.message.reply_text(
                    success_msg,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                            callback_data='back_main'
                        )
                    ]])
                )
            else:
                error_msg = "❌ Failed to send email" if lang == 'en' else "❌ Échec envoi email"
                await update.message.reply_text(
                    error_msg,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                            callback_data='seller_login'
                        ),
                        InlineKeyboardButton(
                            ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                            callback_data='back_main'
                        )
                    ]])
                )
                bot.reset_user_state_preserve_login(user_id)
        except Exception:
            error_msg = "❌ Email service unavailable" if lang == 'en' else "❌ Service email indisponible"
            await update.message.reply_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                        callback_data='seller_login'
                    ),
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )
            bot.reset_user_state_preserve_login(user_id)

    async def process_login_code(self, bot, update, message_text: str):
        """Process code de connexion"""
        user_id = update.effective_user.id
        user_state = bot.get_user_state(user_id)
        provided_code = message_text.strip()
        stored_code = user_state.get('login_code')
        target_user_id = user_state.get('login_target_user_id')
        lang = user_state.get('lang', 'fr')

        if provided_code == stored_code and target_user_id:
            # Code correct - connexion réussie
            bot.reset_user_state_preserve_login(user_id)
            bot.login_seller(user_id)

            # Mettre à jour l'ID utilisateur si nécessaire
            if user_id != target_user_id:
                bot.update_user_mapping(user_id, target_user_id)

            success_msg = "✅ Login successful!" if lang == 'en' else "✅ Connexion réussie !"
            await update.message.reply_text(
                success_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🏪 Dashboard" if lang == 'en' else "🏪 Dashboard"),
                        callback_data='seller_dashboard'
                    )
                ]])
            )
        else:
            # Code incorrect
            error_msg = "❌ Invalid login code" if lang == 'en' else "❌ Code de connexion invalide"
            await update.message.reply_text(
                error_msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        ("🔄 Try again" if lang == 'en' else "🔄 Réessayer"),
                        callback_data='seller_login'
                    ),
                    InlineKeyboardButton(
                        ("❌ Cancel" if lang == 'en' else "❌ Annuler"),
                        callback_data='back_main'
                    )
                ]])
            )
            bot.reset_user_state_preserve_login(user_id)