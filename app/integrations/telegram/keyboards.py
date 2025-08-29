from telegram import InlineKeyboardButton


def main_menu_keyboard(is_seller: bool = False):
    rows = [[InlineKeyboardButton("🛒 Acheter une formation", callback_data='buy_menu')]]
    if is_seller:
        rows.append([InlineKeyboardButton("🏪 Mon espace vendeur", callback_data='seller_dashboard')])
    else:
        rows.append([InlineKeyboardButton("📚 Vendre vos formations", callback_data='sell_menu')])
    rows.append([InlineKeyboardButton("📊 Stats marketplace", callback_data='marketplace_stats')])
    rows.append([InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'), InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')])
    return rows


def buy_menu_keyboard():
    return [
        [InlineKeyboardButton("🔍 Rechercher par ID produit", callback_data='search_product')],
        [InlineKeyboardButton("📂 Parcourir catégories", callback_data='browse_categories')],
        [InlineKeyboardButton("🔥 Meilleures ventes", callback_data='category_bestsellers')],
        [InlineKeyboardButton("🆕 Nouveautés", callback_data='category_new')],
        [InlineKeyboardButton("💸 Payouts / Adresse de retrait", callback_data='my_wallet')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
    ]


def sell_menu_keyboard():
    return [
        [InlineKeyboardButton("🚀 Devenir vendeur", callback_data='create_seller')],
        [InlineKeyboardButton("📋 Conditions & avantages", callback_data='seller_info')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
    ]

