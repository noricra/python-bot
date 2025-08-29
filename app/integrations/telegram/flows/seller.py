import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


logger = logging.getLogger(__name__)


async def sell_menu(bot, query, lang):
    user_data = bot.get_user(query.from_user.id)
    if user_data and user_data['is_seller']:
        await seller_dashboard(bot, query, lang)
        return

    keyboard = [
        [InlineKeyboardButton("🚀 Devenir vendeur", callback_data='create_seller')],
        [InlineKeyboardButton("📋 Conditions & avantages", callback_data='seller_info')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
    ]

    sell_text = """📚 **VENDRE VOS FORMATIONS**

🎯 **Valorisez votre expertise**

💰 **Avantages vendeur :**
• 95% des revenus pour vous (5% commission plateforme)
• Paiements automatiques en crypto
• Wallet intégré sécurisé
• Gestion complète de vos produits
• Support marketing inclus

🔐 **Sécurité**
• Récupération via email + code
• Adresse Solana de paiement à votre nom
• Contrôle total de vos fonds

Prêt à commencer ?"""

    await query.edit_message_text(
        sell_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def create_seller_prompt(bot, query, lang):
    bot.memory_cache[query.from_user.id] = {
        'creating_seller': True,
        'step': 'name',
        'lang': lang
    }
    await query.edit_message_text(
        """🚀 **CRÉATION COMPTE VENDEUR**

Pour créer votre compte vendeur sécurisé, nous avons besoin de quelques informations.

👤 **Étape 1/2 : Nom public**

Saisissez le nom qui apparaîtra sur vos formations :""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler", callback_data='sell_menu')]]),
        parse_mode='Markdown')


async def seller_dashboard(bot, query, lang):
    user_data = bot.get_user(query.from_user.id)
    if not user_data or not user_data['is_seller']:
        await query.edit_message_text(
            "❌ Accès non autorisé.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
        )
        return
    if not bot.is_seller_logged_in(query.from_user.id):
        keyboard = [
            [InlineKeyboardButton("🔐 Se connecter", callback_data='seller_login')],
            [InlineKeyboardButton("🚀 Créer un compte vendeur", callback_data='create_seller')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]
        await query.edit_message_text("🔑 Connexion vendeur\n\nConnectez-vous avec votre email et votre code de récupération.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT COUNT(*) FROM products 
            WHERE seller_user_id = ? AND status = 'active'
        ''', (query.from_user.id, ))
        active_products = cursor.fetchone()[0]
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération produits actifs: {e}")
        active_products = 0
    try:
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(seller_revenue), 0)
            FROM orders 
            WHERE seller_user_id = ? AND payment_status = 'completed'
            AND datetime(created_at) >= datetime('now', 'start of month')
        ''', (query.from_user.id, ))
        month_stats = cursor.fetchone()
        month_sales = month_stats[0]
        month_revenue = month_stats[1]
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération ventes mois: {e}")
        month_sales = 0
        month_revenue = 0
    conn.close()

    dashboard_text = f"""🏪 **DASHBOARD VENDEUR**

👋 Bienvenue **{user_data['seller_name']}** !

📊 **Statistiques :**
• 📦 Produits actifs : {active_products}
• 🛒 Ventes ce mois : {month_sales}
• 💰 Revenus ce mois : {month_revenue:.2f}€
• ⭐ Note moyenne : {user_data['seller_rating']:.1f}/5

💸 **Payouts / Adresse :** {'✅ Configurée' if user_data['seller_solana_address'] else '❌ À configurer'}"""

    keyboard = [[InlineKeyboardButton("➕ Ajouter un produit", callback_data='add_product')],
                [InlineKeyboardButton("📦 Mes produits", callback_data='my_products')],
                [InlineKeyboardButton("💸 Payouts / Adresse", callback_data='my_wallet')],
                [InlineKeyboardButton("📊 Analytics détaillées", callback_data='seller_analytics')],
                [InlineKeyboardButton("⚙️ Paramètres", callback_data='seller_settings')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]]

    await query.edit_message_text(
        dashboard_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def add_product_prompt(bot, query, lang):
    user_data = bot.get_user(query.from_user.id)
    if not user_data or not user_data['is_seller'] or not bot.is_seller_logged_in(query.from_user.id):
        await query.edit_message_text(
            "❌ Connectez-vous d'abord (email + code)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
        )
        return
    bot.update_user_state(query.from_user.id, adding_product=True, step='title', product_data={}, lang=lang)
    await query.edit_message_text(
        """➕ **AJOUTER UN NOUVEAU PRODUIT**

📝 **Étape 1/5 : Titre**

Saisissez le titre de votre formation :

💡 **Conseil :** Soyez précis et accrocheur
*Exemple : "Guide Complet Trading Crypto 2025"*""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Annuler", callback_data='seller_dashboard')]]),
        parse_mode='Markdown')


async def show_my_products(bot, query, lang):
    user_data = bot.get_user(query.from_user.id)
    if not user_data or not user_data['is_seller'] or not bot.is_seller_logged_in(query.from_user.id):
        await query.edit_message_text(
            "❌ Connectez-vous d'abord (email + code)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
        )
        return
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT product_id, title, price_eur, sales_count, status, created_at
            FROM products 
            WHERE seller_user_id = ?
            ORDER BY created_at DESC
        ''', (query.from_user.id, ))
        products = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération produits vendeur: {e}")
        conn.close()
        return

    if not products:
        products_text = """📦 **MES PRODUITS**

Aucun produit créé pour le moment.

Commencez dès maintenant à monétiser votre expertise !"""
        keyboard = [[InlineKeyboardButton("➕ Créer mon premier produit", callback_data='add_product')],
                    [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')]]
    else:
        products_text = f"📦 **MES PRODUITS** ({len(products)})\n\n"
        keyboard = []
        for product in products[:10]:
            status_icon = {
                "active": "✅",
                "inactive": "⏸️",
                "banned": "❌"
            }.get(product[4], "❓")
            products_text += f"{status_icon} `{product[0]}`\n"
            products_text += f"💰 {product[2]}€ • 🛒 {product[3]} ventes\n\n"
            keyboard.append([
                InlineKeyboardButton(f"✏️ Modifier", callback_data=f'edit_product_{product[0]}'),
                InlineKeyboardButton("🗑️ Supprimer", callback_data=f'delete_product_{product[0]}')
            ])
        keyboard.extend([[InlineKeyboardButton("➕ Nouveau produit", callback_data='add_product')],
                         [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')],
                         [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])

    await query.edit_message_text(
        products_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def show_wallet(bot, query, lang):
    user_data = bot.get_user(query.from_user.id)
    if not user_data or not user_data['is_seller'] or not bot.is_seller_logged_in(query.from_user.id):
        await query.edit_message_text(
            "❌ Connectez-vous d'abord (email + code)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
        )
        return
    if not user_data['seller_solana_address']:
        await query.edit_message_text(
            """💳 **WALLET NON CONFIGURÉ**

    Pour avoir un wallet, vous devez d'abord devenir vendeur.

    Votre adresse Solana sera configurée lors de l'inscription.""",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Devenir vendeur", callback_data='create_seller')], [InlineKeyboardButton("🔙 Retour", callback_data='back_main')]])
        )
        return

    solana_address = user_data['seller_solana_address']
    try:
        from bot_mlt import get_solana_balance_display  # type: ignore
        balance = get_solana_balance_display(solana_address)
    except Exception:
        balance = 0.0

    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT COALESCE(SUM(total_amount_sol), 0) 
            FROM seller_payouts 
            WHERE seller_user_id = ? AND payout_status = 'pending'
        ''', (query.from_user.id,))
        pending_amount = cursor.fetchone()[0]
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération payouts en attente: {e}")
        conn.close()
        pending_amount = 0

    wallet_text = f"""💸 **PAYOUTS / ADRESSE DE RETRAIT**

    📍 **Adresse :** `{solana_address}`

    💎 **Solde actuel :** {balance:.6f} SOL
    ⏳ **Payout en attente :** {pending_amount:.6f} SOL

    💡 **Infos payouts :**
    - Traités quotidiennement
    - 95% de vos ventes
    - Commission plateforme : 5%"""

    keyboard = [[InlineKeyboardButton("📊 Historique payouts", callback_data='payout_history')],
                [InlineKeyboardButton("📋 Copier adresse", callback_data='copy_address')],
                [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')]]

    await query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def payout_history(bot, query):
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, total_amount_sol, payout_status, created_at, processed_at
            FROM seller_payouts
            WHERE seller_user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (query.from_user.id,))
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur payouts: {e}")
        await query.edit_message_text("❌ Erreur récupération payouts.")
        return

    if not rows:
        await query.edit_message_text("💸 Aucun payout pour le moment.")
        return

    text = "💸 Vos payouts:\n\n"
    for r in rows:
        text += f"• #{r[0]} — {r[1]:.6f} SOL — {r[2]} — {str(r[3])[:19]}\n"
    await query.edit_message_text(text)


async def seller_analytics(bot, query, lang):
    try:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(seller_revenue), 0)
            FROM orders
            WHERE seller_user_id = ? AND payment_status = 'completed'
        ''', (query.from_user.id,))
        total = cursor.fetchone()
        cursor.execute('''
            SELECT p.title, COALESCE(COUNT(o.id),0) as sales
            FROM products p
            LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status='completed'
            WHERE p.seller_user_id = ?
            GROUP BY p.product_id
            ORDER BY sales DESC
            LIMIT 5
        ''', (query.from_user.id,))
        top = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur analytics: {e}")
        await query.edit_message_text("❌ Erreur analytics.")
        return

    text = f"""📊 Analytics vendeur

Ventes totales: {total[0]}\nRevenus totaux: {total[1]:.2f}€\n
Top produits:\n"""
    for t in top:
        text += f"• {t[0]} — {t[1]} ventes\n"
    await query.edit_message_text(text)


async def seller_settings(bot, query, lang):
    bot.update_user_state(query.from_user.id, editing_settings=True, step='menu')
    keyboard = [
        [InlineKeyboardButton("✏️ Modifier nom", callback_data='edit_seller_name')],
        [InlineKeyboardButton("📝 Modifier bio", callback_data='edit_seller_bio')],
        [InlineKeyboardButton("💸 Payouts / Adresse", callback_data='my_wallet')],
        [InlineKeyboardButton("🚪 Se déconnecter", callback_data='seller_logout')],
        [InlineKeyboardButton("🗑️ Supprimer le compte vendeur", callback_data='delete_seller')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
    ]
    await query.edit_message_text("Paramètres vendeur:", reply_markup=InlineKeyboardMarkup(keyboard))


async def copy_address(bot, query):
    await query.answer("Adresse copiée", show_alert=False)

