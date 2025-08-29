import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def marketplace_stats(bot, query, lang):
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
        # Top catégories
        cursor.execute('''
            SELECT c.name, c.icon, COUNT(p.id) as product_count
            FROM categories c
            LEFT JOIN products p ON c.name = p.category
            GROUP BY c.name
            ORDER BY product_count DESC
            LIMIT 5
        ''')
        top_categories = cursor.fetchall()
        conn.close()
    except sqlite3.Error:
        conn.close()
        return

    stats_text = f"""📊 **STATISTIQUES MARKETPLACE**

🎯 **Vue d'ensemble :**
• 👥 Utilisateurs : {total_users:,}
• 🏪 Vendeurs actifs : {total_sellers:,}
• 📦 Formations disponibles : {total_products:,}
• 🛒 Ventes totales : {total_sales:,}
• 💰 Volume échangé : {total_volume:,.2f}€

🔥 **Top catégories :**"""
    for cat in top_categories:
        stats_text += f"\n{cat[1]} {cat[0]} : {cat[2]} formations"

    keyboard = [[InlineKeyboardButton("🔥 Meilleures ventes", callback_data='category_bestsellers')],
                [InlineKeyboardButton("🆕 Nouveautés", callback_data='category_new')],
                [InlineKeyboardButton("🏪 Devenir vendeur", callback_data='sell_menu')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]]
    await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

