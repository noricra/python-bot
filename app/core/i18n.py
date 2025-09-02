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
        # Support
        'support_title': "Assistance et support",
        'support_sub': "Comment pouvons-nous vous aider ?",
        'btn_faq': "FAQ",
        'btn_create_ticket': "Créer un ticket",
        'btn_my_tickets': "Mes tickets",
        'btn_back': "🔙 Retour",
        # Admin
        'btn_admin_payouts': "💸 Vendeurs à payer",
        # Buy menu text
        'buy_menu_text': """🛒 **ACHETER UNE FORMATION**\n\nPlusieurs façons de découvrir nos formations :\n\n🔍 **Recherche directe** - Si vous avez un ID produit\n📂 **Par catégories** - Explorez par domaine\n🔥 **Tendances** - Les plus populaires\n🆕 **Nouveautés** - Dernières publications\n\n💰 **Paiement crypto sécurisé** avec votre wallet intégré""",
        # Search
        'search_prompt': """🔍 **RECHERCHE PAR ID PRODUIT**\n\nSaisissez l'ID de la formation que vous souhaitez acheter.\n\n💡 **Format attendu :** `TBF-2501-ABC123`\n\n✍️ **Tapez l'ID produit :**""",
        # Categories
        'categories_title': """📂 **CATÉGORIES DE FORMATIONS**\n\nChoisissez votre domaine d'intérêt :""",
        'no_products_category': "Aucune formation disponible dans cette catégorie pour le moment.\n\nSoyez le premier à publier dans ce domaine !",
        # Product detail labels
        'label_seller': "👤 **Vendeur :**",
        'label_category': "📂 **Catégorie :**",
        'label_price': "💰 **Prix :**",
        'label_description': "📖 **Description :**",
        'label_seller_bio': "🧾 **Bio vendeur :**",
        'stats_title': "📊 **Statistiques :**",
        'label_views': "👁️",
        'label_sales': "🛒",
        # Library
        'already_owned': "✅ **VOUS POSSÉDEZ DÉJÀ CE PRODUIT**\n\nAccédez-y depuis votre bibliothèque.",
        'library_title': "📚 Vos achats:",
        'library_empty': "📚 Votre bibliothèque est vide.",
        # Buttons common
        'btn_download': "📥 Télécharger",
        'btn_contact_seller': "📨 Contacter le vendeur",
        'btn_preview': "👀 Aperçu",
        'btn_buy': "🛒 Acheter",
        'btn_other_products': "📂 Autres produits",
        # Errors/common
        'err_product_not_found': "❌ Produit introuvable.",
        'err_update_status': "❌ Erreur mise à jour statut.",
        'err_delete': "❌ Erreur lors de la suppression.",
        'err_temp': "❌ Erreur temporaire. Retour au menu principal.",
        'err_internal': "❌ Erreur interne.",
        'btn_library': "📚 Ma bibliothèque",
        'err_nowpayments': "❌ Erreur NOWPayments lors de la création du paiement. Réessayez ou choisissez une autre crypto.",
        'err_verify': "❌ Erreur de vérification. Réessayez.",
        'btn_retry': "🔄 Réessayer",
        'btn_search': "🔍 Rechercher",
        'btn_categories': "📂 Catégories",
        'label_file': "📁 **Fichier :**",
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
        # Support
        'support_title': "Support",
        'support_sub': "How can we help you?",
        'btn_faq': "FAQ",
        'btn_create_ticket': "Create a ticket",
        'btn_my_tickets': "My tickets",
        'btn_back': "🔙 Back",
        # Admin
        'btn_admin_payouts': "💸 Sellers to pay",
        # Buy menu text
        'buy_menu_text': """🛒 **BUY A COURSE**\n\nMultiple ways to discover our courses:\n\n🔍 **Direct search** - If you have a product ID\n📂 **By categories** - Explore by domain\n🔥 **Trending** - Most popular\n🆕 **New** - Latest releases\n\n💰 **Secure crypto payment** with your integrated wallet""",
        # Search
        'search_prompt': """🔍 **SEARCH BY PRODUCT ID**\n\nEnter the ID of the course you want to buy.\n\n💡 **Expected format:** `TBF-2501-ABC123`\n\n✍️ **Type the product ID:**""",
        # Categories
        'categories_title': """📂 **COURSE CATEGORIES**\n\nChoose your area of interest:""",
        'no_products_category': "No course available in this category yet.\n\nBe the first to publish here!",
        # Product detail labels
        'label_seller': "👤 **Seller:**",
        'label_category': "📂 **Category:**",
        'label_price': "💰 **Price:**",
        'label_description': "📖 **Description:**",
        'label_seller_bio': "🧾 **Seller bio:**",
        'stats_title': "📊 **Statistics:**",
        'label_views': "👁️",
        'label_sales': "🛒",
        # Library
        'already_owned': "✅ **YOU ALREADY OWN THIS PRODUCT**\n\nOpen it from your library.",
        'library_title': "📚 Your purchases:",
        'library_empty': "📚 Your library is empty.",
        # Buttons common
        'btn_download': "📥 Download",
        'btn_contact_seller': "📨 Contact seller",
        'btn_preview': "👀 Preview",
        'btn_buy': "🛒 Buy",
        'btn_other_products': "📂 Other products",
        # Errors/common
        'err_product_not_found': "❌ Product not found.",
        'err_update_status': "❌ Error updating status.",
        'err_delete': "❌ Error during deletion.",
        'err_temp': "❌ Temporary error. Back to main menu.",
        'err_internal': "❌ Internal error.",
        'btn_library': "📚 My library",
        'err_nowpayments': "❌ NOWPayments error while creating the payment. Try again or choose another crypto.",
        'err_verify': "❌ Verification error. Please try again.",
        'btn_retry': "🔄 Retry",
        'btn_search': "🔍 Search",
        'btn_categories': "📂 Categories",
        'label_file': "📁 **File:**",
    },
}


def t(lang: str, key: str) -> str:
    lang_key = lang if lang in TEXTS else 'fr'
    return TEXTS.get(lang_key, TEXTS['fr']).get(key, key)

