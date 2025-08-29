import logging
import sqlite3

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.core import settings as core_settings


logger = logging.getLogger(__name__)


async def admin_command(bot, update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != core_settings.ADMIN_USER_ID:
        await update.message.reply_text("❌ Accès non autorisé")
        return
    await admin_menu_display(bot, update)


async def admin_menu_display(bot, update):
    keyboard = [[InlineKeyboardButton("💰 Commissions à payer", callback_data='admin_commissions')],
                [InlineKeyboardButton("📊 Stats marketplace", callback_data='admin_marketplace_stats')],
                [InlineKeyboardButton("👥 Gestion utilisateurs", callback_data='admin_users')],
                [InlineKeyboardButton("📦 Gestion produits", callback_data='admin_products')],
                [InlineKeyboardButton("🎫 Tickets support", callback_data='admin_tickets')]]
    await update.message.reply_text(
        "🔧 **PANEL ADMIN MARKETPLACE**\n\nChoisissez une option :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def admin_menu(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    keyboard = [[InlineKeyboardButton("💰 Commissions à payer", callback_data='admin_commissions')],
                [InlineKeyboardButton("📊 Stats marketplace", callback_data='admin_marketplace_stats')],
                [InlineKeyboardButton("👥 Gestion utilisateurs", callback_data='admin_users')],
                [InlineKeyboardButton("📦 Gestion produits", callback_data='admin_products')],
                [InlineKeyboardButton("🎫 Tickets support", callback_data='admin_tickets')]]
    await query.edit_message_text(
        "🔧 **PANEL ADMIN MARKETPLACE**\n\nChoisissez une option :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def admin_payouts_handler(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT p.id, p.seller_user_id, p.total_amount_sol, u.seller_name, u.seller_solana_address
            FROM seller_payouts p
            JOIN users u ON p.seller_user_id = u.user_id
            WHERE p.payout_status = 'pending'
            ORDER BY p.created_at ASC
        ''')
        pending_payouts = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération payouts en attente (admin): {e}")
        conn.close()
        return
    if not pending_payouts:
        text = "💸 **PAYOUTS VENDEURS**\n\n✅ Aucun payout en attente !"
    else:
        text = f"💸 **PAYOUTS VENDEURS** ({len(pending_payouts)} en attente)\n\n"
        total_sol = 0
        for payout_id, seller_id, amount_sol, name, address in pending_payouts:
            total_sol += amount_sol
            text += f"💰 **{name}** (ID: {seller_id})\n   📍 `{address}`\n   💎 {amount_sol:.4f} SOL\n\n"
        text += f"💎 **Total à payer : {total_sol:.4f} SOL**"
    keyboard = [[InlineKeyboardButton("✅ Marquer tous comme payés", callback_data='admin_mark_all_payouts_paid')],
                [InlineKeyboardButton("📊 Export CSV", callback_data='admin_export_payouts')],
                [InlineKeyboardButton("🔙 Admin panel", callback_data='admin_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def admin_mark_all_payouts_paid(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    try:
        from app.services.payout_service import PayoutService
        ok = PayoutService(bot.db_path).mark_all_pending_as_completed()
        if ok:
            await query.edit_message_text("✅ Tous les payouts en attente ont été marqués comme payés.")
        else:
            await query.edit_message_text("❌ Erreur lors du marquage des payouts.")
    except Exception as e:
        logger.error(f"Erreur mark payouts paid: {e}")
        await query.edit_message_text("❌ Erreur lors du marquage des payouts.")


async def admin_export_payouts(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.seller_user_id, p.total_amount_sol, p.payout_status, p.created_at, p.processed_at,
                   u.seller_name, u.seller_solana_address
            FROM seller_payouts p
            JOIN users u ON u.user_id = p.seller_user_id
            ORDER BY p.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        csv_lines = ["id,seller_user_id,total_amount_sol,payout_status,created_at,processed_at,seller_name,seller_solana_address"]
        for r in rows:
            csv_lines.append(','.join([str(x).replace(',', ' ') for x in r]))
        data = '\n'.join(csv_lines)
        await query.message.reply_document(document=bytes(data, 'utf-8'), filename='payouts.csv')
    except Exception as e:
        logger.error(f"Erreur export payouts: {e}")
        await query.edit_message_text("❌ Erreur export payouts.")


async def admin_users_handler(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_seller = TRUE')
        total_sellers = cursor.fetchone()[0]
        cursor.execute('''
            SELECT user_id, first_name, is_seller, is_partner, registration_date
            FROM users 
            ORDER BY registration_date DESC 
            LIMIT 10
        ''')
        recent_users = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération stats/utilisateurs (admin): {e}")
        conn.close()
        return
    text = f"""👥 **GESTION UTILISATEURS**

📊 **Statistiques :**
 - Total : {total_users:,}
 - Vendeurs : {total_sellers:,}

👥 **Derniers inscrits :**
"""
    for user in recent_users:
        status = []
        if user[2]:
            status.append("Vendeur")
        if user[3]:
            status.append("Partenaire")
        status_str = " | ".join(status) if status else "Acheteur"
        text += f"• {user[1]} (ID: {user[0]}) - {status_str}\n"
    keyboard = [[InlineKeyboardButton("🔍 Rechercher utilisateur", callback_data='admin_search_user')],
                [InlineKeyboardButton("📊 Export utilisateurs", callback_data='admin_export_users')],
                [InlineKeyboardButton("🔙 Admin panel", callback_data='admin_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def admin_export_users(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, is_seller, is_partner, partner_code, registration_date
            FROM users ORDER BY registration_date DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        csv_lines = ["user_id,username,first_name,is_seller,is_partner,partner_code,registration_date"]
        for r in rows:
            csv_lines.append(','.join([str(x).replace(',', ' ') for x in r]))
        data = '\n'.join(csv_lines)
        await query.message.reply_document(document=bytes(data, 'utf-8'), filename='users.csv')
    except Exception as e:
        logger.error(f"Erreur export users: {e}")
        await query.edit_message_text("❌ Erreur export utilisateurs.")


async def admin_search_user(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    bot.memory_cache[query.from_user.id] = {'admin_search_user': True}
    await query.edit_message_text("🔎 Entrez un user_id ou un partner_code à rechercher:")


async def admin_products_handler(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM products WHERE status = "active"')
        active_products = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM products')
        total_products = cursor.fetchone()[0]
        cursor.execute('''
            SELECT p.product_id, p.title, p.price_eur, p.sales_count, u.seller_name, p.status
            FROM products p
            JOIN users u ON p.seller_user_id = u.user_id
            ORDER BY p.created_at DESC
            LIMIT 8
        ''')
        recent_products = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération stats/produits (admin): {e}")
        conn.close()
        return
    text = f"""📦 **GESTION PRODUITS**

📊 **Statistiques :**
 - Total : {total_products:,}
 - Actifs : {active_products:,}

📦 **Derniers produits :**
"""
    for product in recent_products:
        status_icon = "✅" if product[5] == "active" else "⏸️"
        text += f"{status_icon} `{product[0]}` - {product[1][:30]}...\n   💰 {product[2]}€ • 🛒 {product[3]} ventes • 👤 {product[4]}\n\n"
    keyboard = [[InlineKeyboardButton("🔍 Rechercher produit", callback_data='admin_search_product')],
                [InlineKeyboardButton("⛔ Suspendre produit", callback_data='admin_suspend_product')],
                [InlineKeyboardButton("📊 Export produits", callback_data='admin_export_products')],
                [InlineKeyboardButton("🔙 Admin panel", callback_data='admin_menu')]]
    await query.edit_message_text(text[:4000], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def admin_export_products(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.product_id, p.title, p.price_eur, p.status, u.seller_name, p.created_at
            FROM products p
            JOIN users u ON p.seller_user_id = u.user_id
            ORDER BY p.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        header = "product_id,title,price_eur,status,seller_name,created_at"
        csv_lines = [header]
        for r in rows:
            csv_lines.append(','.join([str(x).replace(',', ' ') for x in r]))
        await query.message.reply_document(document=bytes('\n'.join(csv_lines), 'utf-8'), filename='products.csv')
    except Exception as e:
        logger.error(f"Erreur export produits: {e}")
        await query.edit_message_text("❌ Erreur export produits.")


async def admin_commissions_handler(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT o.order_id, o.partner_code, o.partner_commission, o.created_at,
                   u.first_name, p.title
            FROM orders o
            LEFT JOIN users u ON u.partner_code = o.partner_code
            LEFT JOIN products p ON p.product_id = o.product_id
            WHERE o.payment_status = 'completed' 
            AND o.commission_paid = FALSE
            AND o.partner_commission > 0
            ORDER BY o.created_at DESC
        ''')
        unpaid = cursor.fetchall()
        cursor.execute('''
            SELECT SUM(partner_commission) 
            FROM orders 
            WHERE payment_status = 'completed' 
            AND commission_paid = FALSE
        ''')
        total_due = cursor.fetchone()[0] or 0
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération commissions (admin): {e}")
        conn.close()
        return
    if not unpaid:
        text = "💰 **COMMISSIONS**\n\n✅ Aucune commission en attente !"
    else:
        text = f"💰 **COMMISSIONS À PAYER**\n\n💸 **Total à payer : {total_due:.2f}€**\n\n"
        for comm in unpaid:
            text += f"📋 **Commande :** `{comm[0]}`\n👤 **Partenaire :** {comm[4] or 'Anonyme'} (`{comm[1]}`)\n📦 **Produit :** {comm[5]}\n💰 **Commission :** {comm[2]:.2f}€\n📅 **Date :** {comm[3][:10]}\n---\n"
    keyboard = [[InlineKeyboardButton("✅ Marquer comme payées", callback_data='admin_mark_paid')],
                [InlineKeyboardButton("🔙 Retour admin", callback_data='admin_menu')]]
    await query.edit_message_text(text[:4000], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def admin_marketplace_stats(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_seller = TRUE')
        total_sellers = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM products WHERE status = "active"')
        total_products = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM orders WHERE payment_status = "completed"')
        total_sales = cursor.fetchone()[0]
        cursor.execute('SELECT COALESCE(SUM(product_price_eur), 0) FROM orders WHERE payment_status = "completed"')
        total_volume = cursor.fetchone()[0]
        cursor.execute('SELECT COALESCE(SUM(platform_commission), 0) FROM orders WHERE payment_status = "completed"')
        platform_revenue = cursor.fetchone()[0]
        cursor.execute('SELECT COALESCE(SUM(partner_commission), 0) FROM orders WHERE payment_status = "completed" AND commission_paid = FALSE')
        pending_commissions = cursor.fetchone()[0]
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération stats (admin): {e}")
        conn.close()
        return
    stats_text = f"""📊 **STATISTIQUES ADMIN MARKETPLACE**

👥 **Utilisateurs :** {total_users:,}
🏪 **Vendeurs :** {total_sellers:,}
📦 **Produits actifs :** {total_products:,}
🛒 **Ventes totales :** {total_sales:,}

💰 **Finances :**
• Volume total : {total_volume:,.2f}€
• Revenus plateforme : {platform_revenue:.2f}€
• Commissions en attente : {pending_commissions:.2f}€
"""
    keyboard = [[InlineKeyboardButton("💰 Traiter commissions", callback_data='admin_commissions')],
                [InlineKeyboardButton("📦 Gérer produits", callback_data='admin_products')],
                [InlineKeyboardButton("🔙 Panel admin", callback_data='admin_menu')]]
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def admin_search_product(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    bot.memory_cache[query.from_user.id] = {'admin_search_product': True}
    await query.edit_message_text("🔎 Entrez un product_id exact à rechercher:")


async def admin_suspend_product(bot, query):
    if query.from_user.id != core_settings.ADMIN_USER_ID:
        return
    bot.memory_cache[query.from_user.id] = {'admin_suspend_product': True}
    await query.edit_message_text("⛔ Entrez un product_id à suspendre:")

