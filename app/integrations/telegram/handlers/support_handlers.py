from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.messaging_service import MessagingService
from app.core import settings as core_settings


def contact_seller_start(bot, query, product_id: str, lang: str) -> None:
    buyer_id = query.from_user.id
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT o.order_id, p.seller_user_id, p.title
            FROM orders o
            JOIN products p ON p.product_id = o.product_id
            WHERE o.buyer_user_id = ? AND o.product_id = ? AND o.payment_status = 'completed'
            ORDER BY o.completed_at DESC LIMIT 1
            ''', (buyer_id, product_id)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            query.edit_message_text("❌ Vous devez avoir acheté ce produit pour contacter le vendeur.")
            return
        order_id, seller_user_id, title = row
    except Exception:
        query.edit_message_text("❌ Erreur lors de l'initiation du contact.")
        return

    ticket_id = MessagingService(bot.db_path).start_or_get_ticket(buyer_id, order_id, seller_user_id, f"Contact vendeur: {title}")
    if not ticket_id:
        query.edit_message_text("❌ Impossible de créer le ticket.")
        return
    bot.reset_conflicting_states(buyer_id, keep={'waiting_reply_ticket_id'})
    bot.update_user_state(buyer_id, waiting_reply_ticket_id=ticket_id)
    query.edit_message_text(
        f"📨 Contact vendeur pour `{title}`\n\n✍️ Écrivez votre message:",
        parse_mode='Markdown'
    )


def process_messaging_reply(bot, update, message_text: str) -> None:
    user_id = update.effective_user.id
    state = bot.get_user_state(user_id)
    ticket_id = state.get('waiting_reply_ticket_id')
    if not ticket_id:
        update.message.reply_text("❌ Session expirée. Relancez le contact vendeur depuis votre bibliothèque.")
        return
    msg = message_text.strip()
    if not msg:
        update.message.reply_text("❌ Message vide.")
        return
    ok = MessagingService(bot.db_path).post_user_message(ticket_id, user_id, msg)
    if not ok:
        update.message.reply_text("❌ Erreur lors de l'envoi du message.")
        return
    state.pop('waiting_reply_ticket_id', None)
    bot.memory_cache[user_id] = state
    messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 5)
    thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
    keyboard = [[
        InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
        InlineKeyboardButton("🚀 Escalader", callback_data=f'escalate_ticket_{ticket_id}')
    ]]
    update.message.reply_text(f"✅ Message envoyé.\n\n🧵 Derniers messages:\n{thread}", reply_markup=InlineKeyboardMarkup(keyboard))


def view_ticket(bot, query, ticket_id: str) -> None:
    messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 10)
    if not messages:
        query.edit_message_text("🎫 Aucun message dans ce ticket.")
        return
    thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
    keyboard = [[
        InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
        InlineKeyboardButton("🚀 Escalader", callback_data=f'escalate_ticket_{ticket_id}')
    ]]
    query.edit_message_text(f"🧵 Thread ticket `{ticket_id}`:\n\n{thread}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def reply_ticket_prepare(bot, query, ticket_id: str) -> None:
    bot.reset_conflicting_states(query.from_user.id, keep={'waiting_reply_ticket_id'})
    bot.update_user_state(query.from_user.id, waiting_reply_ticket_id=ticket_id)
    query.edit_message_text("✍️ Écrivez votre réponse:")


def escalate_ticket(bot, query, ticket_id: str) -> None:
    admin_id = core_settings.ADMIN_USER_ID or query.from_user.id
    ok = MessagingService(bot.db_path).escalate(ticket_id, admin_id)
    if not ok:
        query.edit_message_text("❌ Impossible d'escalader ce ticket.")
        return
    query.edit_message_text("🚀 Ticket escaladé au support.")


def admin_tickets(bot, query) -> None:
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    rows = MessagingService(bot.db_path).list_recent_tickets(10)
    if not rows:
        query.edit_message_text("🎫 Aucun ticket.")
        return
    text = "🎫 Tickets récents:\n\n"
    keyboard = []
    for t in rows:
        text += f"• {t['ticket_id']} — {t['subject']} — {t['status']}\n"
        keyboard.append([
            InlineKeyboardButton("👁️ Voir", callback_data=f"view_ticket_{t['ticket_id']}"),
            InlineKeyboardButton("↩️ Répondre", callback_data=f"admin_reply_ticket_{t['ticket_id']}")
        ])
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


def admin_reply_prepare(bot, query, ticket_id: str) -> None:
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    bot.reset_conflicting_states(query.from_user.id, keep={'waiting_admin_reply_ticket_id'})
    bot.update_user_state(query.from_user.id, waiting_admin_reply_ticket_id=ticket_id)
    query.edit_message_text("✍️ Écrivez votre réponse admin:")


def process_admin_reply(bot, update, message_text: str) -> None:
    admin_id = update.effective_user.id
    if admin_id != core_settings.ADMIN_USER_ID:
        return
    state = bot.get_user_state(admin_id)
    ticket_id = state.get('waiting_admin_reply_ticket_id')
    if not ticket_id:
        update.message.reply_text("❌ Session expirée.")
        return
    msg = message_text.strip()
    if not msg:
        update.message.reply_text("❌ Message vide.")
        return
    ok = MessagingService(bot.db_path).post_admin_message(ticket_id, admin_id, msg)
    if not ok:
        update.message.reply_text("❌ Erreur lors de l'envoi.")
        return
    state.pop('waiting_admin_reply_ticket_id', None)
    bot.memory_cache[admin_id] = state
    messages = MessagingService(bot.db_path).list_recent_messages(ticket_id, 10)
    thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
    update.message.reply_text(f"✅ Réponse envoyée.\n\n🧵 Derniers messages:\n{thread}")

