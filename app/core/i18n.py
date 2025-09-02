from typing import Dict


TEXTS: Dict[str, Dict[str, str]] = {
    'fr': {
        'main_title': "🏪 TECHBOT MARKETPLACE",
        'main_subtitle': "La première marketplace crypto pour formations",
        'choose_option': "Choisissez une option pour commencer :",
        'cta_buy': "🛒 Acheter une formation",
        'cta_sell': "📚 Vendre vos formations",
        # 'cta_account': removed to simplify UX
        # 'cta_stats': removed from main menu
        'cta_support': "🆘 Support & aide",
        'cta_home': "🏠 Accueil",
        'seller_space': "🏪 Mon espace vendeur",
        # Buttons (menus)
        'btn_search_product': "🔍 Rechercher par ID produit",
        'btn_browse_categories': "📂 Parcourir catégories",
        'btn_bestsellers': "🔥 Meilleures ventes",
        'btn_new': "🆕 Nouveautés",
        'btn_home': "🏠 Accueil",
    },
    'en': {
        'main_title': "🏪 TECHBOT MARKETPLACE",
        'main_subtitle': "The first crypto marketplace for courses",
        'choose_option': "Choose an option to get started:",
        'cta_buy': "🛒 Buy a course",
        'cta_sell': "📚 Sell your courses",
        # 'cta_account': removed to simplify UX
        # 'cta_stats': removed from main menu
        'cta_support': "🆘 Support & help",
        'cta_home': "🏠 Home",
        'seller_space': "🏪 My seller space",
        # Buttons (menus)
        'btn_search_product': "🔍 Search by product ID",
        'btn_browse_categories': "📂 Browse categories",
        'btn_bestsellers': "🔥 Bestsellers",
        'btn_new': "🆕 New",
        'btn_home': "🏠 Home",
    },
}


def t(lang: str, key: str) -> str:
    lang_key = lang if lang in TEXTS else 'fr'
    return TEXTS.get(lang_key, TEXTS['fr']).get(key, key)

