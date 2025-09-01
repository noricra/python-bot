from telegram import InlineKeyboardButton


def main_menu_keyboard(lang: str):
    if lang == 'en':
        return [
            [InlineKeyboardButton("🛒 Buy a course", callback_data='buy_menu')],
            [InlineKeyboardButton("📚 Sell your courses", callback_data='sell_menu')],
            [InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'), InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')],
        ]
    return [
        [InlineKeyboardButton("🛒 Acheter une formation", callback_data='buy_menu')],
        [InlineKeyboardButton("📚 Vendre vos formations", callback_data='sell_menu')],
        [InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'), InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')],
    ]


def buy_menu_keyboard(lang: str):
    if lang == 'en':
        return [
            [InlineKeyboardButton("🔍 Search by product ID", callback_data='search_product')],
            [InlineKeyboardButton("📂 Browse categories", callback_data='browse_categories')],
            [InlineKeyboardButton("🔥 Bestsellers", callback_data='category_bestsellers')],
            [InlineKeyboardButton("🆕 New", callback_data='category_new')],
            [InlineKeyboardButton("💸 Payouts / Withdrawal address", callback_data='my_wallet')],
            [InlineKeyboardButton("🏠 Home", callback_data='back_main')],
        ]
    return [
        [InlineKeyboardButton("🔍 Rechercher par ID produit", callback_data='search_product')],
        [InlineKeyboardButton("📂 Parcourir catégories", callback_data='browse_categories')],
        [InlineKeyboardButton("🔥 Meilleures ventes", callback_data='category_bestsellers')],
        [InlineKeyboardButton("🆕 Nouveautés", callback_data='category_new')],
        [InlineKeyboardButton("💸 Payouts / Adresse de retrait", callback_data='my_wallet')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
    ]


def sell_menu_keyboard(lang: str):
    if lang == 'en':
        return [
            [InlineKeyboardButton("🚀 Become a seller", callback_data='create_seller')],
            [InlineKeyboardButton("📋 Terms & benefits", callback_data='seller_info')],
            [InlineKeyboardButton("🏠 Home", callback_data='back_main')],
        ]
    return [
        [InlineKeyboardButton("🚀 Devenir vendeur", callback_data='create_seller')],
        [InlineKeyboardButton("📋 Conditions & avantages", callback_data='seller_info')],
        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
    ]

