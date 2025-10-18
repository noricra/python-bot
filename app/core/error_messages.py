"""
User-Friendly Error Messages - Template System
Solves PROB-019 from UX_AUDIT.md
"""

ERROR_TEMPLATES = {
    'fr': {
        # Product errors
        'product_not_found': {
            'title': '❌ PRODUIT INTROUVABLE',
            'message': 'Ce produit n\'existe plus ou a été supprimé.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Parcourir les catégories',
                '• Utiliser la recherche',
                '• Contacter le support si le problème persiste'
            ],
            'buttons': ['browse_categories', 'search_product']
        },

        'product_load_error': {
            'title': '❌ OUPS, PROBLÈME TECHNIQUE',
            'message': 'Impossible de charger les produits pour le moment.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Réessayer dans 1 minute',
                '• Vérifier votre connexion',
                '• Contacter le support si le problème persiste'
            ],
            'buttons': ['retry', 'support']
        },

        'no_products': {
            'title': '🚧 AUCUN PRODUIT DISPONIBLE',
            'message': 'Cette catégorie ne contient pas encore de produits.',
            'actions': [
                '💡 SUGGESTIONS :',
                '• Explorer d\'autres catégories',
                '• Revenir plus tard',
                '• Devenir vendeur et ajouter vos produits'
            ],
            'buttons': ['browse_categories', 'become_seller']
        },

        # Payment errors
        'payment_expired': {
            'title': '⏰ PAIEMENT EXPIRÉ',
            'message': 'La session de paiement a expiré (délai: 1 heure).',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Recommencer l\'achat',
                '• Si vous avez déjà payé, contactez le support avec votre transaction ID'
            ],
            'buttons': ['restart_purchase', 'support']
        },

        'payment_verification_failed': {
            'title': '❌ VÉRIFICATION IMPOSSIBLE',
            'message': 'Impossible de vérifier le statut du paiement.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Réessayer dans quelques secondes',
                '• Vérifier votre connexion',
                '• Ne pas payer plusieurs fois (vérifiez d\'abord le statut)'
            ],
            'buttons': ['check_status', 'support']
        },

        'insufficient_balance': {
            'title': '💰 SOLDE INSUFFISANT',
            'message': 'Votre portefeuille n\'a pas assez de fonds pour cette transaction.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Recharger votre portefeuille crypto',
                '• Vérifier l\'adresse de destination',
                '• Prendre en compte les frais de réseau'
            ],
            'buttons': ['retry', 'help']
        },

        # File/Download errors
        'file_not_found': {
            'title': '📁 FICHIER INTROUVABLE',
            'message': 'Le fichier demandé n\'existe pas ou a été déplacé.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Vérifier votre bibliothèque',
                '• Contacter le vendeur',
                '• Signaler le problème au support'
            ],
            'buttons': ['my_library', 'support']
        },

        'download_failed': {
            'title': '❌ TÉLÉCHARGEMENT ÉCHOUÉ',
            'message': 'Impossible de télécharger le fichier pour le moment.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Réessayer dans quelques secondes',
                '• Vérifier votre connexion',
                '• Contacter le support si le problème persiste'
            ],
            'buttons': ['retry_download', 'support']
        },

        # Permission errors
        'not_authorized': {
            'title': '🔒 ACCÈS REFUSÉ',
            'message': 'Vous n\'avez pas l\'autorisation d\'accéder à cette ressource.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Vérifier que vous êtes connecté au bon compte',
                '• Acheter le produit si nécessaire',
                '• Contacter le support en cas d\'erreur'
            ],
            'buttons': ['my_account', 'support']
        },

        'seller_only': {
            'title': '🏪 RÉSERVÉ AUX VENDEURS',
            'message': 'Cette fonctionnalité est réservée aux comptes vendeurs.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Créer un compte vendeur (gratuit)',
                '• Se connecter à votre compte vendeur existant'
            ],
            'buttons': ['become_seller', 'login_seller']
        },

        # Network/Connection errors
        'connection_error': {
            'title': '🌐 PROBLÈME DE CONNEXION',
            'message': 'Impossible de se connecter au serveur.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Vérifier votre connexion Internet',
                '• Réessayer dans quelques secondes',
                '• Vérifier l\'état du service'
            ],
            'buttons': ['retry', 'status_page']
        },

        'timeout': {
            'title': '⏱️ DÉLAI DÉPASSÉ',
            'message': 'L\'opération a pris trop de temps.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Réessayer (parfois le serveur est surchargé)',
                '• Vérifier votre connexion',
                '• Signaler si le problème persiste'
            ],
            'buttons': ['retry', 'support']
        },

        # Generic errors
        'generic_error': {
            'title': '❌ ERREUR INATTENDUE',
            'message': 'Une erreur inattendue s\'est produite.',
            'actions': [
                '💡 QUE FAIRE ?',
                '• Réessayer l\'opération',
                '• Revenir au menu principal',
                '• Contacter le support avec une capture d\'écran'
            ],
            'buttons': ['retry', 'main_menu', 'support']
        },
    },

    'en': {
        # Product errors
        'product_not_found': {
            'title': '❌ PRODUCT NOT FOUND',
            'message': 'This product no longer exists or has been deleted.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Browse categories',
                '• Use search',
                '• Contact support if the issue persists'
            ],
            'buttons': ['browse_categories', 'search_product']
        },

        'product_load_error': {
            'title': '❌ OOPS, TECHNICAL ISSUE',
            'message': 'Unable to load products at the moment.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Try again in 1 minute',
                '• Check your connection',
                '• Contact support if the issue persists'
            ],
            'buttons': ['retry', 'support']
        },

        'no_products': {
            'title': '🚧 NO PRODUCTS AVAILABLE',
            'message': 'This category does not contain any products yet.',
            'actions': [
                '💡 SUGGESTIONS:',
                '• Explore other categories',
                '• Come back later',
                '• Become a seller and add your products'
            ],
            'buttons': ['browse_categories', 'become_seller']
        },

        # Payment errors
        'payment_expired': {
            'title': '⏰ PAYMENT EXPIRED',
            'message': 'The payment session has expired (timeout: 1 hour).',
            'actions': [
                '💡 WHAT TO DO?',
                '• Restart the purchase',
                '• If you already paid, contact support with your transaction ID'
            ],
            'buttons': ['restart_purchase', 'support']
        },

        'payment_verification_failed': {
            'title': '❌ VERIFICATION FAILED',
            'message': 'Unable to verify payment status.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Try again in a few seconds',
                '• Check your connection',
                '• Do not pay multiple times (check status first)'
            ],
            'buttons': ['check_status', 'support']
        },

        'insufficient_balance': {
            'title': '💰 INSUFFICIENT BALANCE',
            'message': 'Your wallet does not have enough funds for this transaction.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Reload your crypto wallet',
                '• Verify the destination address',
                '• Account for network fees'
            ],
            'buttons': ['retry', 'help']
        },

        # File/Download errors
        'file_not_found': {
            'title': '📁 FILE NOT FOUND',
            'message': 'The requested file does not exist or has been moved.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Check your library',
                '• Contact the seller',
                '• Report the issue to support'
            ],
            'buttons': ['my_library', 'support']
        },

        'download_failed': {
            'title': '❌ DOWNLOAD FAILED',
            'message': 'Unable to download the file at the moment.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Try again in a few seconds',
                '• Check your connection',
                '• Contact support if the issue persists'
            ],
            'buttons': ['retry_download', 'support']
        },

        # Permission errors
        'not_authorized': {
            'title': '🔒 ACCESS DENIED',
            'message': 'You do not have permission to access this resource.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Verify you are logged into the correct account',
                '• Purchase the product if necessary',
                '• Contact support if this is an error'
            ],
            'buttons': ['my_account', 'support']
        },

        'seller_only': {
            'title': '🏪 SELLERS ONLY',
            'message': 'This feature is reserved for seller accounts.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Create a seller account (free)',
                '• Login to your existing seller account'
            ],
            'buttons': ['become_seller', 'login_seller']
        },

        # Network/Connection errors
        'connection_error': {
            'title': '🌐 CONNECTION ISSUE',
            'message': 'Unable to connect to the server.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Check your Internet connection',
                '• Try again in a few seconds',
                '• Check service status'
            ],
            'buttons': ['retry', 'status_page']
        },

        'timeout': {
            'title': '⏱️ TIMEOUT',
            'message': 'The operation took too long.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Try again (server may be overloaded)',
                '• Check your connection',
                '• Report if the issue persists'
            ],
            'buttons': ['retry', 'support']
        },

        # Generic errors
        'generic_error': {
            'title': '❌ UNEXPECTED ERROR',
            'message': 'An unexpected error occurred.',
            'actions': [
                '💡 WHAT TO DO?',
                '• Try the operation again',
                '• Return to main menu',
                '• Contact support with a screenshot'
            ],
            'buttons': ['retry', 'main_menu', 'support']
        },
    }
}


BUTTON_CALLBACKS = {
    'retry': 'retry_last_action',
    'browse_categories': 'browse_categories',
    'search_product': 'search_product',
    'support': 'help_support',
    'become_seller': 'become_seller',
    'restart_purchase': 'buy_menu',
    'check_status': 'check_payment_status',
    'my_library': 'library',
    'my_account': 'settings',
    'main_menu': 'main_menu',
    'help': 'help_menu',
    'retry_download': 'retry_download',
    'login_seller': 'seller_login',
    'status_page': 'system_status',
}


BUTTON_LABELS = {
    'fr': {
        'retry': '🔄 Réessayer',
        'browse_categories': '📂 Catégories',
        'search_product': '🔍 Rechercher',
        'support': '💬 Support',
        'become_seller': '🏪 Devenir vendeur',
        'restart_purchase': '🔄 Recommencer',
        'check_status': '🔍 Vérifier statut',
        'my_library': '📚 Ma bibliothèque',
        'my_account': '⚙️ Mon compte',
        'main_menu': '🏠 Menu principal',
        'help': '❓ Aide',
        'retry_download': '🔄 Retélécharger',
        'login_seller': '🔑 Connexion vendeur',
        'status_page': '📊 État du service',
    },
    'en': {
        'retry': '🔄 Try Again',
        'browse_categories': '📂 Categories',
        'search_product': '🔍 Search',
        'support': '💬 Support',
        'become_seller': '🏪 Become Seller',
        'restart_purchase': '🔄 Restart',
        'check_status': '🔍 Check Status',
        'my_library': '📚 My Library',
        'my_account': '⚙️ My Account',
        'main_menu': '🏠 Main Menu',
        'help': '❓ Help',
        'retry_download': '🔄 Re-download',
        'login_seller': '🔑 Seller Login',
        'status_page': '📊 Service Status',
    }
}


def get_error_message(error_type: str, lang: str = 'fr', custom_message: str = None) -> dict:
    """
    Get user-friendly error message with actions and buttons

    Args:
        error_type: Error type key (e.g., 'product_not_found')
        lang: Language ('fr' or 'en')
        custom_message: Optional custom message to override default

    Returns:
        dict: {
            'text': Formatted error message,
            'keyboard': InlineKeyboardMarkup with action buttons
        }
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Get template
    template = ERROR_TEMPLATES.get(lang, ERROR_TEMPLATES['fr']).get(
        error_type,
        ERROR_TEMPLATES[lang]['generic_error']
    )

    # Build message text
    text_parts = [
        template['title'],
        '',
        custom_message or template['message'],
        '',
        *template['actions']
    ]

    text = '\n'.join(text_parts)

    # Build keyboard
    keyboard = []
    button_labels = BUTTON_LABELS.get(lang, BUTTON_LABELS['fr'])

    for button_key in template.get('buttons', []):
        callback_data = BUTTON_CALLBACKS.get(button_key, 'main_menu')
        label = button_labels.get(button_key, button_key)

        keyboard.append([InlineKeyboardButton(label, callback_data=callback_data)])

    # Always add back button
    keyboard.append([
        InlineKeyboardButton(
            '🔙 Retour' if lang == 'fr' else '🔙 Back',
            callback_data='main_menu'
        )
    ])

    return {
        'text': text,
        'keyboard': InlineKeyboardMarkup(keyboard)
    }


def send_error_message(bot, query_or_message, error_type: str, lang: str = 'fr', custom_message: str = None):
    """
    Convenience function to send error message directly

    Args:
        bot: Bot instance
        query_or_message: CallbackQuery or Message object
        error_type: Error type key
        lang: Language
        custom_message: Optional custom message
    """
    error_data = get_error_message(error_type, lang, custom_message)

    # Detect if it's a callback query or message
    if hasattr(query_or_message, 'edit_message_text'):
        # It's a CallbackQuery
        try:
            return query_or_message.edit_message_text(
                text=error_data['text'],
                reply_markup=error_data['keyboard'],
                parse_mode='Markdown'
            )
        except:
            # Fallback: send new message
            return query_or_message.message.reply_text(
                text=error_data['text'],
                reply_markup=error_data['keyboard'],
                parse_mode='Markdown'
            )
    else:
        # It's a Message
        return query_or_message.reply_text(
            text=error_data['text'],
            reply_markup=error_data['keyboard'],
            parse_mode='Markdown'
        )
