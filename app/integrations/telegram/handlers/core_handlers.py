"""Core Handlers - Core functions like start, help, main menu and language management"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from app.core.i18n import t as i18n
from app.core.utils import logger
from app.integrations.telegram.utils import safe_transition_to_text


class CoreHandlers:
    def __init__(self, user_repo):
        self.user_repo = user_repo

    async def start_command(self, marketplace_bot, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Nouveau menu d'accueil marketplace"""
        user = update.effective_user

        # 🔧 FIX: Réinitialiser tous les états (support, recherche, etc.) sauf la langue et requires_relogin
        marketplace_bot.reset_user_state(user.id, keep={'lang', 'requires_relogin'})

        # Conserver l'état (ne pas déconnecter). Simplement assurer l'inscription DB.
        self.user_repo.add_user(user.id, user.username, user.first_name, user.language_code or 'fr')

        # Déterminer la langue depuis la base si disponible (persistance)
        user_data = self.user_repo.get_user(user.id)
        lang = user_data['language_code'] if user_data and user_data.get('language_code') else (user.language_code or 'fr')

        # 🔗 DEEP LINKING: Si payload fourni (ex: /start product_TBF-ABC-123 ou shop_USER_ID)
        if context.args and len(context.args) > 0:
            payload = context.args[0]

            # Format: product_TBF-ABC-123 → affichage direct du produit
            if payload.startswith('product_'):
                product_id = payload.replace('product_', '').upper()

                # Récupérer le produit depuis la DB
                product = marketplace_bot.product_repo.get_product_by_id(product_id)

                if product:
                    # Afficher le produit directement
                    await marketplace_bot.buy_handlers.show_product_details_from_search(
                        marketplace_bot,
                        update,
                        product
                    )
                    return
                else:
                    # Produit introuvable, afficher message + continuer vers menu principal
                    await update.message.reply_text(
                        f"❌ Produit non trouvé: {product_id}" if lang == 'fr'
                        else f"❌ Product not found: {product_id}"
                    )

            # Format: shop_USER_ID → affichage boutique vendeur
            elif payload.startswith('shop_'):
                try:
                    seller_id = int(payload.replace('shop_', ''))

                    # Créer un mock query pour l'appel
                    class MockQuery:
                        def __init__(self, user, update_obj):
                            self.from_user = user
                            self.message = update_obj.message
                            self.effective_chat = update_obj.effective_chat
                        async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                            await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

                    mock_query = MockQuery(update.effective_user, update)

                    # Afficher la boutique du vendeur
                    await marketplace_bot.buy_handlers.show_seller_shop(
                        marketplace_bot,
                        mock_query,
                        seller_id,
                        lang
                    )
                    return
                except ValueError:
                    await update.message.reply_text(
                        f"❌ Lien boutique invalide" if lang == 'fr'
                        else f"❌ Invalid shop link"
                    )

        # Menu normal si pas de payload
        welcome_text = i18n(lang, 'welcome')

        # Utiliser le keyboard centralisé depuis keyboards.py
        from app.integrations.telegram.keyboards import main_menu_keyboard
        keyboard = main_menu_keyboard(lang)

        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML')

    async def help_command(self, marketplace_bot, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Redirige vers la FAQ en respectant la langue de l'utilisateur."""
        user = update.effective_user
        user_data = self.user_repo.get_user(user.id)
        lang = user_data['language_code'] if user_data else (user.language_code or 'fr')

        faq_text = i18n(lang, 'bot_faq_title')
        keyboard = [
            [InlineKeyboardButton(i18n(lang, 'ui_create_ticket_button'), callback_data='create_ticket')],
            [InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]
        ]

        await update.message.reply_text(
            faq_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def back_to_main(self, query, lang):
        """Menu principal avec récupération - Compatible avec CallbackRouter"""
        # Utiliser la fonction centralisée pour garantir la cohérence
        from app.integrations.telegram.keyboards import main_menu_keyboard

        keyboard = main_menu_keyboard(lang)
        welcome_text = i18n(lang, 'welcome')

        try:
            await query.edit_message_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML')
        except Exception:
            await query.message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML')

    async def change_language(self, bot, query, new_lang):
        """Change la langue de l'utilisateur - Compatible avec CallbackRouter"""
        user_id = query.from_user.id

        # Valider la langue
        supported_languages = ['fr', 'en']
        if new_lang not in supported_languages:
            await query.answer("❌ Langue non supportée")
            return

        try:
            # Mise à jour base de données
            self.user_repo.update_user_language(user_id, new_lang)

            # Mettre à jour aussi l'état mémoire pour utilisation immédiate
            if hasattr(bot, 'update_user_state'):
                bot.state_manager.update_state(user_id, lang=new_lang)

            # Forcer le refresh du cache de langue si il existe
            if hasattr(bot, '_user_language_cache') and user_id in bot._user_language_cache:
                bot._user_language_cache[user_id] = new_lang

            await query.answer(f"✅ Language changed to {new_lang}" if new_lang == 'en' else f"✅ Langue changée en {new_lang}")
            await self.back_to_main(query, new_lang)

        except Exception as e:
            await query.answer("❌ Erreur changement langue")

    async def back_to_main_with_bot(self, marketplace_bot, query, lang):
        """Menu principal avec accès au MarketplaceBot - appelé via callback router"""
        await query.answer()

        user_id = query.from_user.id
        # 🔧 FIX: Réinitialiser TOUS les états quand on retourne au menu principal (sauf requires_relogin)
        marketplace_bot.reset_user_state(user_id, keep={'lang', 'requires_relogin'})

        # Utiliser la fonction centralisée pour garantir la cohérence
        from app.integrations.telegram.keyboards import main_menu_keyboard

        keyboard = main_menu_keyboard(lang)
        welcome_text = i18n(lang, 'welcome')

        await safe_transition_to_text(
            query,
            welcome_text,
            InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
