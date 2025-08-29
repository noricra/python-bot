import asyncio
import logging
import random
import re
import sqlite3
import uuid
from datetime import datetime
from io import BytesIO

import qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.core import settings as core_settings
from app.services.referral_service import ReferralService

# Pour l'inférence réseau, réutiliser la logique existante
from bot_mlt import infer_network_from_address  # type: ignore


logger = logging.getLogger(__name__)


async def buy_menu(bot, query, lang):
    keyboard = [
        [InlineKeyboardButton("🔍 Rechercher par ID produit", callback_data='search_product')],
        [InlineKeyboardButton("📂 Parcourir catégories", callback_data='browse_categories')],
        [InlineKeyboardButton("🔥 Meilleures ventes", callback_data='category_bestsellers')],
        [InlineKeyboardButton("🆕 Nouveautés", callback_data='category_new')],
        [InlineKeyboardButton("💸 Payouts / Adresse de retrait", callback_data='my_wallet')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
    ]

    buy_text = """🛒 **ACHETER UNE FORMATION**

Plusieurs façons de découvrir nos formations :

🔍 **Recherche directe** - Si vous avez un ID produit
📂 **Par catégories** - Explorez par domaine
🔥 **Tendances** - Les plus populaires
🆕 **Nouveautés** - Dernières publications

💰 **Paiement crypto sécurisé** avec votre wallet intégré"""

    await query.edit_message_text(
        buy_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def search_product_prompt(bot, query, lang):
    bot.memory_cache[query.from_user.id] = {
        'waiting_for_product_id': True,
        'lang': lang
    }
    await query.edit_message_text(
        """🔍 **RECHERCHE PAR ID PRODUIT**

Saisissez l'ID de la formation que vous souhaitez acheter.

💡 **Format attendu :** `TBF-2501-ABC123`

✍️ **Tapez l'ID produit :**""",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]),
        parse_mode='Markdown')


async def browse_categories(bot, query, lang):
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT name, icon, products_count FROM categories ORDER BY products_count DESC'
        )
        categories = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération catégories: {e}")
        conn.close()
        return

    keyboard = []
    for cat_name, cat_icon, products_count in categories:
        keyboard.append([
            InlineKeyboardButton(
                f"{cat_icon} {cat_name} ({products_count})",
                callback_data=f'category_{cat_name.replace(" ", "_").replace("&", "and")}'
            )
        ])
    keyboard.append([InlineKeyboardButton("🏠 Accueil", callback_data='back_main')])

    categories_text = """📂 **CATÉGORIES DE FORMATIONS**

Choisissez votre domaine d'intérêt :"""

    await query.edit_message_text(
        categories_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def show_category_products(bot, query, category_key, lang):
    if category_key == 'bestsellers':
        category_name = 'Meilleures ventes'
        base_query = '''
            SELECT p.product_id, p.title, p.price_eur, p.sales_count, p.rating, u.seller_name
            FROM products p
            JOIN users u ON p.seller_user_id = u.user_id
            WHERE p.status = 'active'
            ORDER BY p.sales_count DESC
        '''
        query_params = ()
    elif category_key == 'new':
        category_name = 'Nouveautés'
        base_query = '''
            SELECT p.product_id, p.title, p.price_eur, p.sales_count, p.rating, u.seller_name
            FROM products p
            JOIN users u ON p.seller_user_id = u.user_id
            WHERE p.status = 'active'
            ORDER BY p.created_at DESC
        '''
        query_params = ()
    else:
        category_name = category_key.replace('_', ' ').replace('and', '&')
        base_query = '''
            SELECT p.product_id, p.title, p.price_eur, p.sales_count, p.rating, u.seller_name
            FROM products p
            JOIN users u ON p.seller_user_id = u.user_id
            WHERE p.status = 'active' AND p.category = ?
            ORDER BY p.sales_count DESC
        '''
        query_params = (category_name,)

    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"{base_query} LIMIT 10", query_params)
        products = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération produits catégorie: {e}")
        conn.close()
        return

    if not products:
        products_text = f"""📂 **{category_name.upper()}**

Aucune formation disponible dans cette catégorie pour le moment.

Soyez le premier à publier dans ce domaine !"""
        keyboard = [
            [InlineKeyboardButton("🚀 Créer une formation", callback_data='sell_menu')],
            [InlineKeyboardButton("📂 Autres catégories", callback_data='browse_categories')],
        ]
    else:
        products_text = f"📂 **{category_name.upper()}** ({len(products)} formations)\n\n"
        keyboard = []
        for product in products:
            product_id, title, price, sales, rating, seller = product
            stars = "⭐" * int(rating) if rating > 0 else "⭐⭐⭐⭐⭐"
            products_text += f"📦 **{title}**\n"
            products_text += f"💰 {price}€ • 👤 {seller} • {stars} • 🛒 {sales} ventes\n\n"
            keyboard.append([
                InlineKeyboardButton(f"📖 {title[:40]}...", callback_data=f'product_{product_id}')
            ])
        keyboard.extend([
            [InlineKeyboardButton("📂 Autres catégories", callback_data='browse_categories')],
            [InlineKeyboardButton("🔙 Menu achat", callback_data='buy_menu')],
        ])

    await query.edit_message_text(
        products_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def show_product_details(bot, query, product_id, lang):
    product = bot.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text(
            f"❌ **Produit introuvable :** `{product_id}`\n\nVérifiez l'ID ou cherchez dans les catégories.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Rechercher", callback_data='search_product')],
                [InlineKeyboardButton("📂 Catégories", callback_data='browse_categories')],
            ]),
            parse_mode='Markdown')
        return

    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE products SET views_count = views_count + 1 WHERE product_id = ?', (product_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur mise à jour vues produit: {e}")
        conn.close()

    stars = "⭐" * int(product['rating']) if product['rating'] > 0 else "⭐⭐⭐⭐⭐"
    product_text = f"""📦 **{product['title']}**

👤 **Vendeur :** {product['seller_name']} ({product['seller_rating']:.1f}/5)
📂 **Catégorie :** {product['category']}
💰 **Prix :** {product['price_eur']}€

📖 **Description :**
{product['description'] or 'Aucune description disponible'}

📊 **Statistiques :**
• {stars} ({product['reviews_count']} avis)
• 👁️ {product['views_count']} vues
• 🛒 {product['sales_count']} ventes

📁 **Fichier :** {product['file_size_mb']:.1f} MB"""

    keyboard = [
        [InlineKeyboardButton("🛒 Acheter maintenant", callback_data=f'buy_product_{product_id}')],
        [InlineKeyboardButton("📂 Autres produits", callback_data='browse_categories')],
        [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')],
    ]

    await query.edit_message_text(
        product_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def buy_product_prompt(bot, query, product_id, lang):
    user_id = query.from_user.id
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT COUNT(*) FROM orders WHERE buyer_user_id = ? AND product_id = ? AND payment_status = "completed"',
            (user_id, product_id))
        if cursor.fetchone()[0] > 0:
            conn.close()
            await query.edit_message_text(
                "✅ **VOUS POSSÉDEZ DÉJÀ CE PRODUIT**\n\nAccédez-y depuis votre bibliothèque.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Ma bibliothèque", callback_data='my_library')],
                    [InlineKeyboardButton("🔙 Retour", callback_data=f'product_{product_id}')],
                ]))
            return
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Erreur vérification achat produit: {e}")
        conn.close()
        return

    bot.memory_cache[user_id] = {
        'buying_product_id': product_id,
        'lang': lang
    }

    keyboard = [
        [InlineKeyboardButton("✍️ Saisir mon code", callback_data='enter_referral_manual')],
        [InlineKeyboardButton("🎲 Choisir un code aléatoire", callback_data='choose_random_referral')],
        [InlineKeyboardButton("🚀 Devenir partenaire (10% commission!)", callback_data='become_partner')],
        [InlineKeyboardButton("🔙 Retour", callback_data=f'product_{product_id}')],
    ]

    referral_text = """🎯 **CODE DE PARRAINAGE OBLIGATOIRE**

⚠️ **IMPORTANT :** Un code de parrainage est requis pour acheter.

💡 **3 OPTIONS DISPONIBLES :**

1️⃣ **Vous avez un code ?** Saisissez-le !

2️⃣ **Pas de code ?** Choisissez-en un gratuitement !

3️⃣ **MEILLEURE OPTION :** Devenez partenaire !
   • ✅ Gagnez 10% sur chaque vente
   • ✅ Votre propre code de parrainage
   • ✅ Dashboard vendeur complet"""

    await query.edit_message_text(
        referral_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def enter_referral_manual(bot, query, lang):
    bot.memory_cache[query.from_user.id]['waiting_for_referral'] = True
    await query.edit_message_text(
        "✍️ **Veuillez saisir votre code de parrainage :**\n\nTapez le code exactement comme vous l'avez reçu.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]))


async def choose_random_referral(bot, query, lang):
    available_codes = ReferralService(bot.db_path).list_all_codes()
    if not available_codes:
        await query.edit_message_text(
            "❌ Aucun code disponible actuellement.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]))
        return

    random_codes = random.sample(available_codes, min(3, len(available_codes)))
    keyboard = [[InlineKeyboardButton(f"🎯 Utiliser {code}", callback_data=f'use_referral_{code}')]
                for code in random_codes]
    keyboard.extend([[InlineKeyboardButton("🔄 Autres codes", callback_data='choose_random_referral')],
                     [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]])

    codes_text = """🎲 **CODES DE PARRAINAGE DISPONIBLES**

Choisissez un code pour continuer votre achat :

💡 **Tous les codes sont équivalents**
🎁 **Votre parrain recevra sa commission**"""

    await query.edit_message_text(
        codes_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def validate_and_proceed(bot, query, referral_code, lang):
    if not bot.validate_referral_code(referral_code):
        await query.edit_message_text(
            f"❌ **Code invalide :** `{referral_code}`\n\nVeuillez réessayer avec un code valide.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]),
            parse_mode='Markdown')
        return

    user_cache = bot.memory_cache.get(query.from_user.id, {})
    user_cache['validated_referral'] = referral_code
    user_cache['lang'] = lang
    bot.memory_cache[query.from_user.id] = user_cache
    await query.edit_message_text(
        f"✅ **Code validé :** `{referral_code}`\n\nProcédons au paiement !",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Continuer vers le paiement", callback_data='proceed_to_payment'), InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]),
        parse_mode='Markdown')


async def show_crypto_options(bot, query, lang):
    user_id = query.from_user.id
    user_cache = bot.memory_cache.get(user_id, {})
    if 'validated_referral' not in user_cache:
        await query.edit_message_text("❌ Code de parrainage requis !",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Entrer un code", callback_data='buy_menu')]]))
        return
    product_id = user_cache.get('buying_product_id')
    if not product_id:
        await query.edit_message_text("❌ Produit non trouvé !",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Chercher produit", callback_data='search_product')]]))
        return
    product = bot.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ Produit indisponible !",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Chercher produit", callback_data='search_product')]]))
        return

    cryptos = bot.get_available_currencies()
    keyboard = []
    crypto_info = {
        'btc': ('₿ Bitcoin', '⚡ 10-30 min'),
        'eth': ('⟠ Ethereum', '⚡ 5-15 min'),
        'usdt': ('₮ Tether USDT', '⚡ 5-10 min'),
        'usdc': ('🟢 USD Coin', '⚡ 5-10 min'),
        'bnb': ('🟡 BNB', '⚡ 2-5 min'),
        'sol': ('◎ Solana', '⚡ 1-2 min'),
        'ltc': ('Ł Litecoin', '⚡ 10-20 min'),
        'xrp': ('✕ XRP', '⚡ 1-3 min')
    }
    for i in range(0, len(cryptos), 2):
        row = []
        for j in range(2):
            if i + j < len(cryptos):
                crypto = cryptos[i + j]
                name, speed = crypto_info.get(crypto, (crypto.upper(), '⚡ 5-15 min'))
                row.append(InlineKeyboardButton(f"{name} {speed}", callback_data=f'pay_{crypto}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')])

    crypto_text = f"""💳 **CHOISIR VOTRE CRYPTO**

📦 **Produit :** {product['title']}
💰 **Prix :** {product['price_eur']}€
🎯 **Code parrainage :** `{user_cache['validated_referral']}`

🔐 **Sélectionnez votre crypto préférée :**

✅ **Avantages :**
• Paiement 100% sécurisé et anonyme
• Confirmation automatique
• Livraison instantanée après paiement
• Support prioritaire 24/7"""

    await query.edit_message_text(
        crypto_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown')


async def process_payment(bot, query, crypto_currency, lang):
    user_id = query.from_user.id
    user_cache = bot.memory_cache.get(user_id, {})
    if 'validated_referral' not in user_cache or 'buying_product_id' not in user_cache:
        await query.edit_message_text("❌ Données de commande manquantes !",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Recommencer", callback_data='buy_menu')]]))
        return

    product_id = user_cache['buying_product_id']
    referral_code = user_cache['validated_referral']
    product = bot.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ Produit indisponible !")
        return

    await query.edit_message_text("⏳ Création de votre commande...")
    order_id = f"MP{datetime.now().strftime('%y%m%d')}{user_id}{uuid.uuid4().hex[:4].upper()}"

    product_price_eur = product['price_eur']
    rate = await asyncio.to_thread(bot.get_exchange_rate)
    product_price_usd = product_price_eur * rate

    platform_commission = product_price_eur * core_settings.PLATFORM_COMMISSION_RATE
    partner_commission = product_price_eur * core_settings.PARTNER_COMMISSION_RATE
    seller_revenue = product_price_eur - platform_commission - partner_commission

    payment_data = await asyncio.to_thread(
        bot.create_payment, product_price_usd, crypto_currency, order_id
    )

    if payment_data:
        conn = bot.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO orders 
                (order_id, buyer_user_id, product_id, seller_user_id,
                 product_price_eur, platform_commission, seller_revenue, partner_commission,
                 crypto_currency, crypto_amount, nowpayments_id, payment_address, partner_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, user_id, product_id, product['seller_user_id'],
                  product_price_eur, platform_commission, seller_revenue,
                  partner_commission, crypto_currency,
                  payment_data.get('pay_amount', 0), payment_data.get('payment_id'),
                  payment_data.get('pay_address', ''), referral_code))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur création commande: {e}")
            conn.close()
            return

        if user_id in bot.memory_cache:
            uc = bot.memory_cache.get(user_id, {})
            for k in ['buying_product_id', 'validated_referral', 'self_referral']:
                uc.pop(k, None)
            bot.memory_cache[user_id] = uc

        crypto_amount = payment_data.get('pay_amount', 0)
        payment_address = payment_data.get('pay_address', '')
        network_hint = infer_network_from_address(payment_address)

        payment_text = f"""💳 **PAIEMENT EN COURS**

📋 **Commande :** `{order_id}`
📦 **Produit :** {product['title']}
💰 **Montant exact :** `{crypto_amount}` {crypto_currency.upper()}

📍 **Adresse de paiement :**
`{payment_address}`
🧭 **Réseau détecté :** {network_hint}

⏰ **Validité :** 30 minutes
🔄 **Confirmations :** 1-3 selon réseau

⚠️ **IMPORTANT :**
• Envoyez **exactement** le montant indiqué
• Utilisez uniquement du {crypto_currency.upper()}
• La détection est automatique"""

        keyboard = [[InlineKeyboardButton("🔄 Vérifier paiement", callback_data=f'check_payment_{order_id}')],
                    [InlineKeyboardButton("💬 Support", callback_data='support_menu')],
                    [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]]

        try:
            qr_img = qrcode.make(payment_address)
            bio = BytesIO()
            qr_img.save(bio, format='PNG')
            bio.seek(0)
            caption = payment_text
            await query.message.reply_photo(photo=bio, caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.warning(f"QR code generation failed: {e}")
            await query.edit_message_text(
                payment_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
    else:
        await query.edit_message_text(
            "❌ Erreur lors de la création du paiement. Vérifiez la configuration NOWPayments.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Réessayer", callback_data='proceed_to_payment')]]))


async def check_payment_handler(bot, query, order_id, lang):
    await query.edit_message_text("🔍 Vérification en cours...")
    conn = bot.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id, ))
        order = cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"Erreur récupération commande: {e}")
        conn.close()
        return

    if not order:
        await query.edit_message_text("❌ Commande introuvable!")
        return

    payment_id = order[12]
    payment_status = await asyncio.to_thread(bot.check_payment_status, payment_id)

    if payment_status:
        status = payment_status.get('payment_status', 'waiting')
        if status in ['finished', 'confirmed']:
            try:
                cursor.execute('''
                    UPDATE orders 
                    SET payment_status = 'completed', 
                        completed_at = CURRENT_TIMESTAMP,
                        file_delivered = TRUE
                    WHERE order_id = ?
                ''', (order_id, ))
                cursor.execute('''
                    UPDATE products 
                    SET sales_count = sales_count + 1
                    WHERE product_id = ?
                ''', (order[3], ))
                cursor.execute('''
                    UPDATE users 
                    SET total_sales = total_sales + 1,
                        total_revenue = total_revenue + ?
                    WHERE user_id = ?
                ''', (order[7], order[4]))
                partner_code = order[14]
                if partner_code:
                    cursor.execute('''
                        UPDATE users 
                        SET total_commission = total_commission + ?
                        WHERE partner_code = ?
                    ''', (order[8], partner_code))
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur mise à jour après paiement: {e}")
                conn.rollback()
                conn.close()
                return

            try:
                payout_created = await bot.auto_create_seller_payout(order_id)
            except Exception as e:
                logger.error(f"Erreur auto payout: {e}")
                payout_created = False
            finally:
                conn.close()

            success_text = f"""🎉 **FÉLICITATIONS !**

✅ **Paiement confirmé** - Commande : {order_id}
{"✅ Payout vendeur créé automatiquement" if payout_created else "⚠️ Payout vendeur en attente"}

📚 **ACCÈS IMMÉDIAT À VOTRE FORMATION**"""
            keyboard = [[InlineKeyboardButton("📥 Télécharger maintenant", callback_data=f'download_product_{order[3]}')],
                        [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]]
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            conn.close()
            await query.edit_message_text(
                f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Les confirmations peuvent prendre 5-30 min",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Rafraîchir", callback_data=f'check_payment_{order_id}')]]))
    else:
        conn.close()
        await query.edit_message_text(
            "❌ Erreur de vérification. Réessayez.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Réessayer", callback_data=f'check_payment_{order_id}')]]))


async def process_product_search(bot, update, message_text):
    user_id = update.effective_user.id
    user_state = bot.memory_cache[user_id]
    product_id = message_text.strip().upper()
    if not re.match(r'^TBF-\d{4}-[A-HJ-NP-Z2-9]{6}$', product_id):
        await update.message.reply_text(
            f"❌ **Format ID invalide :** `{product_id}`\n\n💡 **Format attendu :** `TBF-2501-ABC123`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]),
            parse_mode='Markdown')
        return
    product = bot.get_product_by_id(product_id)
    if user_id in bot.memory_cache:
        state = bot.memory_cache.get(user_id, {})
        state.pop('waiting_for_product_id', None)
        bot.memory_cache[user_id] = state
    if product:
        await show_product_details_from_search(bot, update, product)
    else:
        await update.message.reply_text(
            f"❌ **Produit introuvable :** `{product_id}`\n\nVérifiez l'ID ou explorez les catégories.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Parcourir catégories", callback_data='browse_categories')], [InlineKeyboardButton("🔙 Menu achat", callback_data='buy_menu')]]),
            parse_mode='Markdown')


async def show_product_details_from_search(bot, update, product):
    stars = "⭐" * int(product['rating']) if product['rating'] > 0 else "⭐⭐⭐⭐⭐"
    product_text = f"""📦 **{product['title']}**

👤 **Vendeur :** {product['seller_name']} ({product['seller_rating']:.1f}/5)
📂 **Catégorie :** {product['category']}
💰 **Prix :** {product['price_eur']}€

📖 **Description :**
{product['description'] or 'Aucune description disponible'}

📊 **Statistiques :**
• {stars} ({product['reviews_count']} avis)
• 👁️ {product['views_count']} vues
• 🛒 {product['sales_count']} ventes

📁 **Fichier :** {product['file_size_mb']:.1f} MB"""

    keyboard = [[InlineKeyboardButton("🛒 Acheter maintenant", callback_data=f"buy_product_{product['product_id']}")],
                [InlineKeyboardButton("📂 Autres produits", callback_data='browse_categories')],
                [InlineKeyboardButton("🔙 Menu achat", callback_data='buy_menu')]]
    await update.message.reply_text(product_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def process_referral_input(bot, update, message_text):
    user_id = update.effective_user.id
    user_cache = bot.memory_cache.get(user_id, {})
    if bot.validate_referral_code(message_text.strip()):
        user_cache['validated_referral'] = message_text.strip()
        user_cache.pop('waiting_for_referral', None)
        bot.memory_cache[user_id] = user_cache
        await update.message.reply_text(
            f"✅ **Code validé :** `{message_text.strip()}`\n\nProcédons au paiement !",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Continuer vers le paiement", callback_data='proceed_to_payment'), InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]),
            parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"❌ **Code invalide :** `{message_text.strip()}`\n\nVeuillez réessayer avec un code valide.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Choisir un code aléatoire", callback_data='choose_random_referral'), InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]]),
            parse_mode='Markdown')

