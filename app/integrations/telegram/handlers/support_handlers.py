"""Support Handlers - Support and ticket management functions with dependency injection"""

from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.services.messaging_service import MessagingService
from app.core import settings as core_settings
from app.integrations.telegram.keyboards import back_to_main_button


class SupportHandlers:
    def __init__(self, user_repo, product_repo, support_service):
        self.user_repo = user_repo
        self.product_repo = product_repo
        self.support_service = support_service

    async def support_command(self, bot, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Redirige vers la création de ticket de support directement."""
        user = update.effective_user
        user_data = self.user_repo.get_user(user.id)
        lang = user_data['language_code'] if user_data else (user.language_code or 'fr')
        # Ouvre directement la création de ticket
        class DummyQuery:
            def __init__(self, uid):
                self.from_user = type('u', (), {'id': uid})
            async def edit_message_text(self, *args, **kwargs):
                await update.message.reply_text(*args, **kwargs)
        await self.create_ticket_prompt(bot, DummyQuery(user.id), lang)

    async def contact_seller_start(self, bot, query, product_id: str, lang: str) -> None:
        buyer_id = query.from_user.id
        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT o.order_id, p.seller_user_id, p.title
                FROM orders o
                JOIN products p ON p.product_id = o.product_id
                WHERE o.buyer_user_id = %s AND o.product_id = %s AND o.payment_status = 'completed'
                ORDER BY o.completed_at DESC LIMIT 1
                ''', (buyer_id, product_id)
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                await query.edit_message_text("❌ Vous devez avoir acheté ce produit pour contacter le vendeur.")
                return
            order_id, seller_user_id, title = row
        except Exception:
            await query.edit_message_text("❌ Erreur lors de l'initiation du contact.")
            return

        ticket_id = MessagingService(bot.db_path).start_or_get_ticket(buyer_id, order_id, seller_user_id, f"Contact vendeur: {title}")
        if not ticket_id:
            await query.edit_message_text("❌ Impossible de créer le ticket.")
            return
        bot.reset_conflicting_states(buyer_id, keep={'waiting_reply_ticket_id'})
        bot.state_manager.update_state(buyer_id, waiting_reply_ticket_id=ticket_id)
        safe_title = bot.escape_markdown(title)
        await query.edit_message_text(
            f"📨 Contact vendeur pour `{safe_title}`\n\n✍️ Écrivez votre message:",
            parse_mode='Markdown'
        )

    async def process_messaging_reply(self, bot, update, message_text: str) -> None:
        user_id = update.effective_user.id
        state = bot.get_user_state(user_id)
        ticket_id = state.get('waiting_reply_ticket_id')
        if not ticket_id:
            await update.message.reply_text("❌ Session expirée. Relancez le contact vendeur depuis votre bibliothèque.")
            return
        msg = message_text.strip()
        if not msg:
            await update.message.reply_text("❌ Message vide.")
            return
        ok = MessagingService(bot.db_path).post_user_message(ticket_id, user_id, msg)
        if not ok:
            await update.message.reply_text("❌ Erreur lors de l'envoi du message.")
            return
        state.pop('waiting_reply_ticket_id', None)
        bot.state_manager.update_state(user_id, **state)
        messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 5)
        thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
        keyboard = [[
            InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
            InlineKeyboardButton("🚀 Escalader", callback_data=f'escalate_ticket_{ticket_id}')
        ]]
        await update.message.reply_text(f"✅ Message envoyé.\n\n🧵 Derniers messages:\n{thread}", reply_markup=InlineKeyboardMarkup(keyboard))

    async def view_ticket(self, bot, query, ticket_id: str) -> None:
        messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 10)
        if not messages:
            await query.edit_message_text("🎫 Aucun message dans ce ticket.")
            return
        thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
        keyboard = [[
            InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
            InlineKeyboardButton(" Escalader", callback_data=f'escalate_ticket_{ticket_id}')
        ]]
        await query.edit_message_text(f" Thread ticket `{ticket_id}`:\n\n{thread}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def reply_ticket_prepare(self, bot, query, ticket_id: str) -> None:
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_reply_ticket_id'})
        bot.state_manager.update_state(query.from_user.id, waiting_reply_ticket_id=ticket_id)
        await query.edit_message_text("✍️ Écrivez votre réponse:")

    async def escalate_ticket(self, bot, query, ticket_id: str) -> None:
        admin_id = core_settings.ADMIN_USER_ID or query.from_user.id
        ok = MessagingService(bot.db_path).escalate(ticket_id, admin_id)
        if not ok:
            await query.edit_message_text("❌ Impossible d'escalader ce ticket.")
            return
        await query.edit_message_text(" Ticket escaladé au support.")

    async def admin_tickets(self, bot, query) -> None:
        if core_settings.ADMIN_USER_ID is None or query.from_user.id != core_settings.ADMIN_USER_ID:
            await query.edit_message_text("❌ Accès non autorisé.")
            return
        rows = MessagingService(bot.db_path).list_recent_tickets(10)
        if not rows:
            await query.edit_message_text(" Aucun ticket.")
            return
        text = " Tickets récents:\n\n"
        keyboard = []
        for t in rows:
            text += f"• {t['ticket_id']} — {t['subject']} — {t['status']}\n"
            keyboard.append([
                InlineKeyboardButton("👁️ Voir", callback_data=f"view_ticket_{t['ticket_id']}"),
                InlineKeyboardButton("↩️ Répondre", callback_data=f"admin_reply_ticket_{t['ticket_id']}")
            ])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_reply_prepare(self, bot, query, ticket_id: str) -> None:
        if core_settings.ADMIN_USER_ID is None or query.from_user.id != core_settings.ADMIN_USER_ID:
            await query.edit_message_text("❌ Accès non autorisé.")
            return
        bot.reset_conflicting_states(query.from_user.id, keep={'waiting_admin_reply_ticket_id'})
        bot.state_manager.update_state(query.from_user.id, waiting_admin_reply_ticket_id=ticket_id)
        await query.edit_message_text("✍️ Écrivez votre réponse admin:")

    async def process_admin_reply(self, bot, update, message_text: str) -> None:
        admin_id = update.effective_user.id
        if admin_id != core_settings.ADMIN_USER_ID:
            return
        state = bot.get_user_state(admin_id)
        ticket_id = state.get('waiting_admin_reply_ticket_id')
        if not ticket_id:
            await update.message.reply_text("❌ Session expirée.")
            return
        msg = message_text.strip()
        if not msg:
            await update.message.reply_text("❌ Message vide.")
            return
        ok = MessagingService(bot.db_path).post_admin_message(ticket_id, admin_id, msg)
        if not ok:
            await update.message.reply_text("❌ Erreur lors de l'envoi.")
            return
        state.pop('waiting_admin_reply_ticket_id', None)
        bot.state_manager.update_state(admin_id, **state)
        messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 10)
        thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
        await update.message.reply_text(f"✅ Réponse envoyée.\n\n🧵 Derniers messages:\n{thread}")

    # Support UI Methods - Extracted from bot_mlt.py
    async def support_menu(self, bot, query, lang):
        """Main support menu"""
        # Reset conflicting states when entering support workflow
        if hasattr(query, 'from_user'):
            bot.reset_conflicting_states(query.from_user.id, keep={'lang'})

        await self.show_faq(query, lang)

    async def show_faq(self, query, lang):
        """FAQ display with comprehensive information"""
        if lang == 'fr':
            faq_text = """📋 **FAQ - Questions Fréquentes**

🛒 **ACHETER UN PRODUIT**

**Q: Comment acheter ? (Guide débutant)**
A: **Étape 1:** Menu "Acheter" > Parcourir catégories ou rechercher par ID
   **Étape 2:** Cliquer sur le produit souhaité
   **Étape 3:** Cliquer "Acheter" puis choisir votre crypto (BTC, ETH, USDT...)
   **Étape 4:** Le bot affiche une adresse crypto + QR code
   **Étape 5:** Ouvrir votre wallet crypto (Binance, Trust Wallet, Coinbase...)
   **Étape 6:** Envoyer le montant exact à l'adresse fournie
   **Étape 7:** Attendre confirmation (5-30 min selon la crypto)
   **Étape 8:** Réception automatique du produit dans "Ma bibliothèque"

**Q: Dois-je fournir mes données personnelles ?**
A: **NON. Aucun KYC requis.** Plateforme axée sur la confidentialité.

 **VENDRE VOS PRODUITS**

**Q: Avantages vendeur ?**
A:  **0% de commission** - Recevez 100% du prix de vente
    **Aucun KYC requis** - Plateforme axée sur la confidentialité
    **Paiements crypto directs** - Contrôle total de vos gains
    **Portée internationale** - Vendez partout sans restrictions

**Q: Comment devenir vendeur ?**
A: Menu "Vendre" > Compte vendeur > Adresse Solana > Publier

**Q: Quand suis-je payé ?**
A: Après vérification manuelle anti-fraude, paiement direct sur votre wallet Solana.

🔧 **SUPPORT**

**Q: Problème avec un achat ?**
A: Système de tickets 24/7."""
        else:
            faq_text = """📋 **FAQ - Frequently Asked Questions**

 **BUYING A PRODUCT**

**Q: How to buy? (Beginner's guide)**
A: **Step 1:** Menu "Buy" > Browse categories or search by ID
   **Step 2:** Click on desired product
   **Step 3:** Click "Buy" then choose your crypto (BTC, ETH, USDT...)
   **Step 4:** Bot displays crypto address + QR code
   **Step 5:** Open your crypto wallet (Binance, Trust Wallet, Coinbase...)
   **Step 6:** Send exact amount to provided address
   **Step 7:** Wait for confirmation (5-30 min depending on crypto)
   **Step 8:** Automatic delivery to "My Library"

**Q: Do I need to provide personal data?**
A: **NO. No KYC required.** Privacy-focused platform.

 **SELLING YOUR PRODUCTS**

**Q: Seller advantages?**
A:  **0% commission** - Receive 100% of sale price
    **No KYC required** - Privacy-focused platform
    **Direct crypto payments** - Full control of your earnings
    **Global reach** - Sell anywhere without restrictions

**Q: How to become a seller?**
A: Menu "Sell" > Seller account > Solana address > Publish

**Q: When do I get paid?**
A: After manual anti-fraud verification, direct payment to your Solana wallet.

🔧 **SUPPORT**

**Q: Problem with a purchase?**
A: 24/7 ticket system."""

        keyboard = [
            [
                InlineKeyboardButton(" Mes tickets" if lang == 'fr' else " My Tickets", callback_data='my_tickets')
            ],
            [
                InlineKeyboardButton(" Créer un ticket" if lang == 'fr' else " Create ticket", callback_data='create_ticket')
            ],
            [
                back_to_main_button(lang)
            ]
        ]

        await query.edit_message_text(faq_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def create_ticket_prompt(self, bot, query, lang):
        """Create ticket prompt"""
        user_id = query.from_user.id
        bot.reset_conflicting_states(user_id, keep={'creating_ticket'})
        bot.state_manager.update_state(user_id, creating_ticket=True, step='subject')

        await query.edit_message_text(
            "📝 Entrez le sujet de votre ticket:" if lang == 'fr' else "📝 Enter your ticket subject:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Annuler" if lang == 'fr' else "❌ Cancel", callback_data='back_main')
            ]]))

    async def my_tickets(self, query, lang):
        """Show user's tickets"""
        user_id = query.from_user.id
        tickets = self.support_service.list_user_tickets(user_id)

        if not tickets:
            await query.edit_message_text(
                " Aucun ticket trouvé." if lang == 'fr' else " No tickets found.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(" Créer un ticket" if lang == 'fr' else " Create ticket", callback_data='create_ticket'),
                    back_to_main_button(lang)
                ]])
            )
            return

        text = " Vos tickets:" if lang == 'fr' else " Your tickets:"
        keyboard = []
        for ticket in tickets[:5]:
            text += f"\n• {ticket['ticket_id']} - {ticket['status']}"
            keyboard.append([InlineKeyboardButton(f"👁️ {ticket['ticket_id']}", callback_data=f"view_ticket_{ticket['ticket_id']}")])

        keyboard.append([back_to_main_button(lang)])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def process_ticket_creation(self, bot, update, message_text: str):
        """Process ticket creation based on current step"""
        user_id = update.effective_user.id
        user_state = bot.state_manager.get_state(user_id)
        step = user_state.get('step', 'subject')
        lang = user_state.get('lang', 'fr')

        if step == 'subject':
            if len(message_text.strip()) < 3:
                await update.message.reply_text("❌ Le sujet doit contenir au moins 3 caractères.")
                return

            # Store subject and move to content step
            user_state['ticket_subject'] = message_text.strip()[:100]
            user_state['step'] = 'content'
            bot.state_manager.update_state(user_id, user_state)

            await update.message.reply_text(
                f"✅ **Sujet :** {bot.escape_markdown(message_text.strip())}\n\n📝 Maintenant, décrivez votre problème en détail :",
                parse_mode='Markdown'
            )

        elif step == 'content':
            if len(message_text.strip()) < 10:
                await update.message.reply_text("Le message doit contenir au moins 10 caractères." if lang == 'fr' else "Message must contain at least 10 characters.")
                return

            # Store content and move to email step
            user_state['ticket_content'] = message_text.strip()[:2000]
            user_state['step'] = 'email'
            bot.state_manager.update_state(user_id, user_state)

            await update.message.reply_text(
                "Veuillez entrer votre adresse email pour recevoir une réponse :" if lang == 'fr' else "Please enter your email address to receive a response:",
                parse_mode='Markdown'
            )

        elif step == 'email':
            # Validate email format
            email = message_text.strip()
            if '@' not in email or '.' not in email.split('@')[-1]:
                await update.message.reply_text("Adresse email invalide. Veuillez réessayer." if lang == 'fr' else "Invalid email address. Please try again.")
                return

            subject = user_state.get('ticket_subject', 'Support Request')
            content = user_state.get('ticket_content', '')

            # Create ticket using support service with email
            ticket_id = self.support_service.create_ticket(user_id, subject, content, client_email=email)

            if ticket_id:
                keyboard = [[InlineKeyboardButton("🏠 Menu principal" if lang == 'fr' else "🏠 Main menu", callback_data='back_main')]]
                await update.message.reply_text(
                    f"Ticket créé avec succès !\n\nID : {ticket_id}\n\nNotre équipe vous répondra à l'adresse : {email}" if lang == 'fr'
                    else f"Ticket created successfully!\n\nID: {ticket_id}\n\nOur team will respond to: {email}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("Erreur lors de la création du ticket. Veuillez réessayer." if lang == 'fr' else "Error creating ticket. Please try again.")

            # Reset state
            bot.reset_user_state(user_id)

    async def admin_reply_ticket_prompt(self, query, ticket_id: str):
        """Admin reply to ticket prompt"""
        if core_settings.ADMIN_USER_ID is None or query.from_user.id != core_settings.ADMIN_USER_ID:
            await query.edit_message_text("❌ Accès non autorisé.")
            return

        user_id = query.from_user.id
        # Using the admin_reply_prepare method that already exists
        await self.admin_reply_prepare(None, query, ticket_id)