import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


logger = logging.getLogger(__name__)


async def download_product(bot, query, context, product_id: str, lang: str):
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM orders
            WHERE buyer_user_id = ? AND product_id = ? AND payment_status = 'completed'
        ''', (query.from_user.id, product_id))
        ok = cursor.fetchone()[0] > 0
        if not ok:
            conn.close()
            await query.edit_message_text("❌ Accès refusé. Achetez d'abord ce produit.")
            return
        cursor.execute('SELECT main_file_path FROM products WHERE product_id = ?', (product_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            await query.edit_message_text("❌ Fichier introuvable.")
            return
        file_path = row[0]
        conn.close()

        if not os.path.exists(file_path):
            await query.edit_message_text("❌ Fichier manquant sur le serveur.")
            return

        try:
            conn = bot.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE orders SET download_count = download_count + 1 WHERE product_id = ? AND buyer_user_id = ?', (product_id, query.from_user.id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Maj compteur download échouée: {e}")

        await query.message.reply_document(document=open(file_path, 'rb'))
    except Exception as e:
        logger.error(f"Erreur download: {e}")
        await query.edit_message_text("❌ Erreur lors du téléchargement.")


async def show_my_library(bot, query, lang: str):
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.product_id, p.title, p.price_eur
            FROM orders o
            JOIN products p ON p.product_id = o.product_id
            WHERE o.buyer_user_id = ? AND o.payment_status = 'completed'
            ORDER BY o.completed_at DESC
        ''', (query.from_user.id,))
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur bibliothèque: {e}")
        await query.edit_message_text("❌ Erreur lors de la récupération de votre bibliothèque.")
        return

    if not rows:
        await query.edit_message_text("📚 Votre bibliothèque est vide.")
        return

    text = "📚 Vos achats:\n\n"
    keyboard = []
    for product_id, title, price in rows[:10]:
        text += f"• {title} — {price}€\n"
        keyboard.append([InlineKeyboardButton("📥 Télécharger", callback_data=f'download_product_{product_id}')])

    keyboard.append([InlineKeyboardButton("🏠 Accueil", callback_data='back_main')])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

