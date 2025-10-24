from telegram import InlineKeyboardButton
from app.core.i18n import t as i18n


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS CENTRALISÉS - Boutons communs (évite duplication)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def back_to_main_button(lang: str):
    """Bouton retour accueil - TOUJOURS identique"""
    label = "🏠 Accueil" if lang == 'fr' else "🏠 Home"
    return InlineKeyboardButton(label, callback_data='back_main')

def support_button(lang: str):
    """Bouton support - TOUJOURS identique"""
    return InlineKeyboardButton("💬 Support", callback_data='support_menu')

def language_buttons():
    """Boutons langue - TOUJOURS identiques"""
    return [
        InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'),
        InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')
    ]

def cancel_button(lang: str):
    """Bouton annuler - TOUJOURS identique"""
    label = "❌ Annuler" if lang == 'fr' else "❌ Cancel"
    return InlineKeyboardButton(label, callback_data='back_main')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KEYBOARDS PRINCIPAUX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main_menu_keyboard(lang: str):
    """Menu principal - SOURCE UNIQUE DE VÉRITÉ"""
    return [
        # Ligne 1: Acheter | Vendre
        [InlineKeyboardButton(i18n(lang, 'cta_buy'), callback_data='buy_menu'),
         InlineKeyboardButton(i18n(lang, 'cta_sell'), callback_data='sell_menu')],
        # Ligne 2: Bibliothèque
        [InlineKeyboardButton("📚 " + ("My Library" if lang == 'en' else "Ma Bibliothèque"), callback_data='library_menu')],
        # Ligne 3: Support | FR/EN
        [support_button(lang)] + language_buttons(),
    ]


def buy_menu_keyboard(lang: str):
    """Menu achat - utilise helper centralisé"""
    return [
        [InlineKeyboardButton(i18n(lang, 'btn_search_product'), callback_data='search_product'),
         InlineKeyboardButton(i18n(lang, 'btn_browse_categories'), callback_data='browse_categories')],
        [InlineKeyboardButton(i18n(lang, 'btn_bestsellers'), callback_data='category_bestsellers'),
         InlineKeyboardButton(i18n(lang, 'btn_new'), callback_data='category_new')],
        [back_to_main_button(lang)],
    ]


def sell_menu_keyboard(lang: str):
    """Menu vente - utilise helper centralisé"""
    return [
        [InlineKeyboardButton(i18n(lang, 'btn_seller_login'), callback_data='seller_login_menu')],
        [InlineKeyboardButton(i18n(lang, 'btn_create_seller'), callback_data='create_seller')],
        [InlineKeyboardButton(i18n(lang, 'btn_seller_info'), callback_data='seller_info')],
        [back_to_main_button(lang)],
    ]

