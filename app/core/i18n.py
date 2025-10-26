from typing import Dict


TEXTS: Dict[str, Dict[str, str]] = {
    'fr': {
        # Menu principal
        'welcome': "<b>⚡UZEUR</b>\n\nLa marketplace dédié aux produits numériques.\nFormations • eBooks • Templates • Guides ...\n\n<b>ACHETER :</b>\nParcourez le catalogue ou entrez un ID produit. Livraison automatique.\n(Paiement sécurisé par <b>Nowpayments</b>)\n\n<b>VENDRE :</b>\nUploadez vos produits et recevez vos paiements\ndirectement en crypto\n\n<b>MA BIBLIOTHÈQUE :</b>\nAccédez à tous vos achats et téléchargements\n────────────────\n🔒 Paiement accepté : BTC • ETH • SOL • USDC • USDT\n\n💡 Vous avez un ID produit ?\nEntrez-le directement (ex: TBF-782092-12345678)",
        'cta_buy': "Acheter",
        'cta_sell': "Vendre",

        # Boutons navigation
        'btn_home': "Accueil",
        'btn_back': "Retour",
        'btn_cancel': "Annuler",
        'btn_library': "Ma bibliothèque",
        'btn_search': "Rechercher",
        'btn_categories': "Catégories",
        'btn_back_dashboard': "Retour dashboard",

        # Menu achat
        'btn_search_product': "Rechercher par ID",
        'btn_browse_categories': "Parcourir catégories",
        'btn_bestsellers': "Meilleures ventes",
        'btn_new': "Nouveautés",
        'btn_buy': "Acheter",
        'search_prompt': """🔍 **RECHERCHE PAR ID PRODUIT**\n\nSaisissez l'ID de la formation que vous souhaitez acheter.\n\n💡 **Format attendu :** `TBF-2501-ABC123`\n\n✍️ **Tapez l'ID produit :**""",
        'categories_title': """📂 **CATÉGORIES DE FORMATIONS**\n\nChoisissez votre domaine d'intérêt :""",

        # Vendeur
        'btn_create_seller': "Créer un compte",
        'btn_seller_login': "Espace vendeur",
        'btn_seller_info': "Conditions & avantages",
        'btn_email': "Email",
        'seller_create_title': "🚀 **CRÉATION COMPTE VENDEUR**",
        'seller_step1_prompt': "Saisissez le nom qui apparaîtra sur vos formations :",
        'login_title': "🔐 **CONNEXION VENDEUR**\n\nSaisissez d'abord votre email, puis votre mot de passe.\n\nSi vous n'avez pas de compte vendeur, créez-en un d'abord.",

        # Dashboard vendeur
        'dashboard_welcome': "🏪 **Bienvenue {name} !**\n\n📊 **Votre tableau de bord :**\n• 📦 Produits : {products_count}\n• 💰 Revenus : {revenue}",
        'btn_add_product': "Ajouter un produit",
        'btn_my_products': "Mes produits",
        'btn_my_wallet': "Payouts / Adresse",
        'btn_seller_settings': "Paramètres",
        'btn_logout': "Se déconnecter",
        'btn_edit_bio': "Modifier bio",
        'btn_edit_name': "Modifier nom",
        'btn_payout_history': "Historique payouts",
        'analytics_title': "📊 Analytics vendeur",
        'settings_title': "⚙️ Paramètres vendeur",
        'wallet_title': "💰 Portefeuille / Payouts",
        'no_products_msg': "Aucun produit trouvé.",
        'product_add_title': "➕ Ajouter un produit",
        'product_step1_prompt': "📦 Étape 1: Titre du produit",
        'product_category_step': "✅ **Description sauvegardée**\n\nÉtape 3: Choisissez une catégorie",
        'seller_name_updated': "✅ Nom mis à jour.",

        # Récupération mot de passe
        'recovery_email_sent': "✅ Code de récupération envoyé à",
        'recovery_code_prompt': "📱 Entrez le code à 6 chiffres reçu par email :",
        'recovery_new_password_prompt': "🔒 Entrez votre nouveau mot de passe :\n(8 caractères minimum)",
        'recovery_success': "✅ Mot de passe mis à jour avec succès !\n\nVous pouvez maintenant vous connecter avec votre email et nouveau mot de passe.",
        'recovery_session_expired': "❌ Session de récupération expirée",

        # Paiement
        'payment_title': "Paiement",
        'crypto_selection_text': "Choisissez votre crypto-monnaie pour le paiement :",

        # Erreurs
        'err_product_not_found': "❌ Produit introuvable.",
        'err_temp': "⚠️ **Erreur temporaire**\n\nNos serveurs sont momentanément surchargés.\n\n🔄 **Veuillez réessayer dans quelques instants.**\n\n💬 Si le problème persiste, contactez notre support 24/7.",
        'err_verify': "❌ Erreur de vérification. Réessayez.",
        'err_update_error': "❌ Erreur lors de la mise à jour.",
        'err_purchase_error': "❌ Erreur lors de l'achat.",
        'err_invalid_price': "❌ Prix invalide (1-5000€).",
        'err_price_update_error': "❌ Prix invalide (1-5000€) ou erreur mise à jour.",
        'err_payment_creation': "💳 **Erreur de paiement**\n\n⚠️ Impossible de créer votre transaction crypto.\n\n🔧 **Solutions possibles :**\n• Vérifiez votre connexion internet\n• Réessayez avec une autre crypto\n• Contactez le support si le problème persiste\n\n💬 **Support disponible 24/7**",

        # Succès
        'success_price_updated': "✅ Prix mis à jour avec succès !",

        # Admin
        'admin_back': "🔙 Retour",
        'admin_payouts': "💰 Payouts",
        'admin_stats': "📊 Stats",
        'admin_payouts_title': "💰 **PAYOUTS PENDING**",
        'admin_products_title': "📦 **PRODUITS** (20 derniers)",

        # Support
        'ui_create_ticket_button': "Créer un ticket",
        'bot_faq_title': "❓ FAQ - Questions fréquentes",

        # Bot
        'bot_commands_start': "Ouvrir le menu principal",
        'bot_commands_help': "Aide et FAQ",
        'bot_commands_support': "Support & aide",
        'bot_access_denied': "❌ Accès refusé",
    },
    'en': {
        # Main menu
        'welcome': "<b>⚡UZEUR - MARKETPLACE</b>\n\nThe marketplace for digital products.\nCourses • eBooks • Templates • Guides ...\n\n<b>BUY :</b>\nBrowse the catalog or enter a product ID. Automatic delivery.\n(Secure payment via <b>NowPayments)</b>\n\n<b>SELL :</b>\nUpload your products and receive your payments\ndirectly in crypto\n\n<b>MY LIBRARY :</b>\nAccess all your purchases and downloads\n────────────────\n🔒 Payment accepted: BTC • ETH • SOL • USDC • USDT\n\n 💡 Have a product ID?\nEnter it directly (e.g. TBF-782092-12345678)",
        'cta_buy': "Buy",
        'cta_sell': "Sell",

        # Navigation buttons
        'btn_home': "Home",
        'btn_back': "Back",
        'btn_cancel': "Cancel",
        'btn_library': "My library",
        'btn_search': "Search",
        'btn_categories': "Categories",
        'btn_back_dashboard': "Back to dashboard",

        # Buy menu
        'btn_search_product': "Search by ID",
        'btn_browse_categories': "Browse categories",
        'btn_bestsellers': "Bestsellers",
        'btn_new': "New",
        'btn_buy': "Buy",
        'search_prompt': """🔍 **SEARCH BY PRODUCT ID**\n\nEnter the ID of the course you want to buy.\n\n💡 **Expected format:** `TBF-2501-ABC123`\n\n✍️ **Type the product ID:**""",
        'categories_title': """📂 **COURSE CATEGORIES**\n\nChoose your area of interest:""",

        # Seller
        'btn_create_seller': "Create account",
        'btn_seller_login': "Seller space",
        'btn_seller_info': "Terms & benefits",
        'btn_email': "Email",
        'seller_create_title': "🚀 **CREATE SELLER ACCOUNT**",
        'seller_step1_prompt': "Enter the name that will appear on your courses:",
        'login_title': "🔐 **SELLER LOGIN**\n\nEnter your email first, then your password.\n\nIf you don't have a seller account yet, create one first.",

        # Seller dashboard
        'dashboard_welcome': "🏪 **Welcome {name}!**\n\n📊 **Your dashboard:**\n• 📦 Products: {products_count}\n• 💰 Revenue: {revenue}",
        'btn_add_product': "Add product",
        'btn_my_products': "My products",
        'btn_my_wallet': "Payouts / Adresse",
        'btn_seller_settings': "Settings",
        'btn_logout': "Log out",
        'btn_edit_bio': "Edit bio",
        'btn_edit_name': "Edit name",
        'btn_payout_history': "Payout history",
        'analytics_title': "📊 Seller analytics",
        'settings_title': "⚙️ Seller settings",
        'wallet_title': "💰 Wallet / Payouts",
        'no_products_msg': "No products found.",
        'product_add_title': "➕ Add product",
        'product_step1_prompt': "📦 Step 1: Product title",
        'product_category_step': "✅ **Description saved**\n\nStep 3: Choose a category",
        'seller_name_updated': "✅ Name updated.",

        # Password recovery
        'recovery_email_sent': "✅ Recovery code sent to",
        'recovery_code_prompt': "📱 Enter the 6-digit code from your email:",
        'recovery_new_password_prompt': "🔒 Enter your new password:\n(Minimum 8 characters)",
        'recovery_success': "✅ Password updated successfully!\n\nYou can now login with your email and new password.",
        'recovery_session_expired': "❌ Recovery session expired",

        # Payment
        'payment_title': "Payment",
        'crypto_selection_text': "Choose your cryptocurrency for payment:",

        # Errors
        'err_product_not_found': "❌ Product not found.",
        'err_temp': "❌ Temporary error. Please try again.",
        'err_verify': "❌ Verification error. Please try again.",
        'err_update_error': "❌ Update error.",
        'err_purchase_error': "❌ Purchase error.",
        'err_invalid_price': "❌ Invalid price (€1-5000).",
        'err_price_update_error': "❌ Invalid price or update error.",
        'err_payment_creation': "❌ Error creating payment.",

        # Success
        'success_price_updated': "✅ Price updated successfully!",

        # Admin
        'admin_back': "🔙 Back",
        'admin_payouts': "💰 Payouts",
        'admin_stats': "📊 Stats",
        'admin_payouts_title': "💰 **PAYOUTS PENDING**",
        'admin_products_title': "📦 **PRODUCTS** (last 20)",

        # Support
        'ui_create_ticket_button': "Create ticket",
        'bot_faq_title': "❓ FAQ - Frequently asked questions",

        # Bot
        'bot_commands_start': "Open main menu",
        'bot_commands_help': "Help and FAQ",
        'bot_commands_support': "Support & help",
        'bot_access_denied': "❌ Access denied",
    },
}


def t(lang: str, key: str) -> str:
    lang_key = lang if lang in TEXTS else 'fr'
    return TEXTS.get(lang_key, TEXTS['fr']).get(key, key)
