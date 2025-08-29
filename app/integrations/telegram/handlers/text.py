import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)


async def text_message_handler(bot_controller, update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text

    if user_id not in bot_controller.memory_cache:
        await update.message.reply_text(
            "💬 Utilisez le menu principal pour naviguer.",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("🏠 Menu principal",
                                     callback_data='back_main')
            ]]))
        return

    user_state = bot_controller.memory_cache[user_id]

    # === RECHERCHE PRODUIT ===
    if user_state.get('waiting_for_product_id'):
        await bot_controller.process_product_search(update, message_text)

    # === CRÉATION VENDEUR ===
    elif user_state.get('creating_seller'):
        await bot_controller.process_seller_creation(update, message_text)

    # === CONNEXION VENDEUR ===
    elif user_state.get('seller_login'):
        await bot_controller.process_seller_login(update, message_text)

    # === AJOUT PRODUIT ===
    elif user_state.get('adding_product'):
        await bot_controller.process_product_addition(update, message_text)

    # === SAISIE CODE PARRAINAGE ===
    elif user_state.get('waiting_for_referral'):
        await bot_controller.process_referral_input(update, message_text)

    # === CRÉATION TICKET SUPPORT ===
    elif user_state.get('creating_ticket'):
        await bot_controller.process_support_ticket(update, message_text)

    # === RÉCUPÉRATION PAR EMAIL ===
    elif user_state.get('waiting_for_recovery_email'):
        await bot_controller.process_recovery_email(update, message_text)

    # === RÉCUPÉRATION CODE ===
    elif user_state.get('waiting_for_recovery_code'):
        await bot_controller.process_recovery_code(update, message_text)

    # === CONNEXION (email + code fourni lors de la création) ===
    elif user_state.get('login_wait_email'):
        await bot_controller.process_login_email(update, message_text)
    elif user_state.get('login_wait_code'):
        await bot_controller.process_login_code(update, message_text)

    # === PARAMÈTRES VENDEUR ===
    elif user_state.get('editing_settings'):
        await bot_controller.process_seller_settings(update, message_text)
    # === ÉDITION PRODUIT ===
    elif user_state.get('editing_product'):
        step = user_state.get('step')
        product_id = user_state.get('product_id')
        if step == 'edit_title_input':
            new_title = message_text.strip()[:100]
            try:
                conn = bot_controller.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE products SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (new_title, product_id, user_id))
                conn.commit()
                conn.close()
                bot_controller.memory_cache.pop(user_id, None)
                await update.message.reply_text("✅ Titre mis à jour.")
            except Exception as e:
                logger.error(f"Erreur maj titre produit: {e}")
                await update.message.reply_text("❌ Erreur mise à jour titre.")
        elif step == 'edit_price_input':
            try:
                price = float(message_text.replace(',', '.'))
                if price < 1 or price > 5000:
                    raise ValueError("Prix hors limites")
                conn = bot_controller.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE products SET price_eur = ?, price_usd = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (price, price * bot_controller.get_exchange_rate(), product_id, user_id))
                conn.commit()
                conn.close()
                bot_controller.memory_cache.pop(user_id, None)
                await update.message.reply_text("✅ Prix mis à jour.")
            except Exception as e:
                logger.error(f"Erreur maj prix produit: {e}")
                await update.message.reply_text("❌ Prix invalide ou erreur mise à jour.")
        else:
            await update.message.reply_text("💬 Choisissez l'action d'édition depuis le menu.")
    # === ADMIN RECHERCHES/SUSPENSIONS ===
    elif user_state.get('admin_search_user'):
        await bot_controller.process_admin_search_user(update, message_text)
    elif user_state.get('admin_search_product'):
        await bot_controller.process_admin_search_product(update, message_text)
    elif user_state.get('admin_suspend_product'):
        await bot_controller.process_admin_suspend_product(update, message_text)

    # === DÉFAUT ===
    else:
        await update.message.reply_text(
            "💬 Pour nous contacter, utilisez le système de support.",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("🎫 Créer un ticket",
                                     callback_data='create_ticket'),
                InlineKeyboardButton("🏠 Menu principal",
                                     callback_data='back_main')
            ]]))

