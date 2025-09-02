from telegram import InlineKeyboardButton
from app.core.i18n import t as i18n


def main_menu_keyboard(lang: str):
    return [
        [InlineKeyboardButton(i18n(lang, 'cta_buy'), callback_data='buy_menu')],
        [InlineKeyboardButton(i18n(lang, 'cta_sell'), callback_data='sell_menu')],
        [InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'), InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')],
    ]


def buy_menu_keyboard(lang: str):
    return [
        [InlineKeyboardButton(i18n(lang, 'btn_search_product'), callback_data='search_product')],
        [InlineKeyboardButton(i18n(lang, 'btn_browse_categories'), callback_data='browse_categories')],
        [InlineKeyboardButton(i18n(lang, 'btn_bestsellers'), callback_data='category_bestsellers')],
        [InlineKeyboardButton(i18n(lang, 'btn_new'), callback_data='category_new')],
        [InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')],
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

