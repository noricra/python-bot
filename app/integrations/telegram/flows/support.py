from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def show_support_menu(bot_controller, query, lang):
    keyboard = [
        [InlineKeyboardButton("FAQ", callback_data='faq')],
        [InlineKeyboardButton("Créer un ticket", callback_data='create_ticket')],
        [InlineKeyboardButton("Mes tickets", callback_data='my_tickets')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
    ]

    support_text = """Assistance et support

Comment pouvons-nous vous aider ?"""

    await query.edit_message_text(
        support_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def show_faq(bot_controller, query, lang):
    faq_text = """**FAQ**

Q: Comment acheter une formation ?
R: Parcourez les catégories ou recherchez par ID.

Q: Comment vendre une formation ?
R: Devenez vendeur et ajoutez vos produits.

Q: Comment récupérer mon compte ?
R: Utilisez l'email de récupération."""

    keyboard = [[InlineKeyboardButton("Retour", callback_data='support_menu')]]

    await query.edit_message_text(
        faq_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def create_ticket(bot_controller, query, lang):
    bot_controller.memory_cache[query.from_user.id] = {
        'creating_ticket': True,
        'step': 'subject',
        'lang': lang
    }
    await query.edit_message_text(
        "🆘 Nouveau ticket\n\nEntrez un sujet pour votre demande:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='support_menu')]])
    )


async def show_my_tickets(bot_controller, query, lang):
    try:
        from app.services.support_service import SupportService
        rows = SupportService(bot_controller.db_path).list_user_tickets(query.from_user.id, 10)
    except Exception as e:
        await query.edit_message_text("❌ Erreur récupération tickets.")
        return

    if not rows:
        await query.edit_message_text("🎫 Aucun ticket.")
        return

    text = "🎫 Vos tickets:\n\n"
    for t in rows:
        text += f"• {t['ticket_id']} — {t['subject']} — {t['status']}\n"
    await query.edit_message_text(text)

