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
        'dashboard_welcome': "🏪 **Bienvenue {name} !**\n\n **Votre tableau de bord :**\n•  Produits : {products_count}\n•  Revenus : {revenue}",
        'btn_add_product': "Ajouter un produit",
        'btn_my_products': "Mes produits",
        'btn_my_wallet': "Payouts / Adresse",
        'btn_seller_settings': "Paramètres",
        'btn_logout': "Se déconnecter",
        'btn_edit_bio': "Modifier bio",
        'btn_edit_name': "Modifier nom",
        'btn_payout_history': "Historique payouts",
        'analytics_title': "📊 Analytics vendeur",
        'analytics_dashboard_title': "📊 TABLEAU DE BORD VENDEUR",
        'analytics_net_revenue': "Revenus nets",
        'analytics_products_sales': "Produits & Ventes",
        'analytics_products_active': "Produits: {active}/{total} actifs",
        'analytics_orders': "Ventes: {sales} commandes",
        'analytics_top5': "🏆 Top 5 Produits",
        'analytics_no_products': "Aucun produit vendu pour le moment",
        'analytics_chart_30days': "📈 Graphique ci-dessous pour les 30 derniers jours",
        'analytics_no_data': "Pas encore de données de vente pour afficher un graphique",
        'analytics_sales_count': "ventes",
        'analytics_btn_detailed': "📊 Graphiques détaillés",
        'analytics_btn_export': "📥 Export CSV",
        'analytics_btn_back': "🔙 Retour Analytics",
        'analytics_btn_refresh': "🔄 Rafraîchir",
        'analytics_detailed_title': "📊 Graphiques détaillés :",
        'analytics_export_success': "✅ Export CSV terminé avec succès !",
        'btn_dashboard': "🔙 Dashboard",
        'settings_title': "⚙️ Paramètres vendeur",
        'wallet_title': " Portefeuille / Payouts",
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
        'err_invalid_price': "Prix invalide. Entrez un nombre entre 9.99$ et 5000$ (ou 0 pour gratuit).",
        'err_price_update_error': "Prix invalide. Entrez un nombre entre 9.99$ et 5000$ (ou 0 pour gratuit).",
        'err_title_update_error': "❌ Titre invalide (minimum 3 caractères) ou erreur mise à jour.",
        'err_description_update_error': "❌ Description invalide ou erreur mise à jour.",
        'err_payment_creation': "💳 **Erreur de paiement**\n\n⚠️ Impossible de créer votre transaction crypto.\n\n🔧 **Solutions possibles :**\n• Vérifiez votre connexion internet\n• Réessayez avec une autre crypto\n• Contactez le support si le problème persiste\n\n💬 **Support disponible 24/7**",
        'err_not_seller': "❌ Vous devez être vendeur pour utiliser cette fonctionnalité.",

        # Succès
        'success_price_updated': "✅ Prix mis à jour avec succès !",
        'success_title_updated': "✅ Titre mis à jour avec succès !",
        'success_description_updated': "✅ Description mise à jour avec succès !",

        # Admin
        'admin_back': "🔙 Retour",
        'admin_payouts': " Payouts",
        'admin_stats': " Stats",
        'admin_payouts_title': " **PAYOUTS PENDING**",
        'admin_products_title': " **PRODUITS** (20 derniers)",

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
        'dashboard_welcome': "🏪 **Welcome {name}!**\n\n **Your dashboard:**\n•  Products: {products_count}\n•  Revenue: {revenue}",
        'btn_add_product': "Add product",
        'btn_my_products': "My products",
        'btn_my_wallet': "Payouts / Adresse",
        'btn_seller_settings': "Settings",
        'btn_logout': "Log out",
        'btn_edit_bio': "Edit bio",
        'btn_edit_name': "Edit name",
        'btn_payout_history': "Payout history",
        'analytics_title': " Seller analytics",
        'analytics_dashboard_title': "📊 SELLER DASHBOARD",
        'analytics_net_revenue': "Net Revenue",
        'analytics_products_sales': "Products & Sales",
        'analytics_products_active': "Products: {active}/{total} active",
        'analytics_orders': "Sales: {sales} orders",
        'analytics_top5': "🏆 Top 5 Products",
        'analytics_no_products': "No products sold yet",
        'analytics_chart_30days': "📈 Chart below for the last 30 days",
        'analytics_no_data': "No sales data yet to display a chart",
        'analytics_sales_count': "sales",
        'analytics_btn_detailed': "📊 Detailed Charts",
        'analytics_btn_export': "📥 Export CSV",
        'analytics_btn_back': "🔙 Back to Analytics",
        'analytics_btn_refresh': "🔄 Refresh",
        'analytics_detailed_title': "📊 Detailed Charts:",
        'analytics_export_success': "✅ CSV export completed successfully!",
        'btn_dashboard': "🔙 Dashboard",
        'settings_title': "⚙️ Seller settings",
        'wallet_title': " Wallet / Payouts",
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
        'err_invalid_price': "Invalid price. Enter a number between $9.99 and $5000 (or 0 for free).",
        'err_price_update_error': "Invalid price. Enter a number between $9.99 and $5000 (or 0 for free).",
        'err_title_update_error': "❌ Invalid title (minimum 3 characters) or update error.",
        'err_description_update_error': "❌ Invalid description or update error.",
        'err_payment_creation': "❌ Error creating payment.",
        'err_not_seller': "❌ You must be a seller to use this feature.",

        # Success
        'success_price_updated': "✅ Price updated successfully!",
        'success_title_updated': "✅ Title updated successfully!",
        'success_description_updated': "✅ Description updated successfully!",

        # Admin
        'admin_back': "🔙 Back",
        'admin_payouts': " Payouts",
        'admin_stats': " Stats",
        'admin_payouts_title': " **PAYOUTS PENDING**",
        'admin_products_title': " **PRODUCTS** (last 20)",

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
