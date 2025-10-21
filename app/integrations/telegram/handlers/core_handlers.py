"""Core Handlers - Core functions like start, help, main menu and language management"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from app.core.i18n import t as i18n
from app.core.utils import logger


class CoreHandlers:
    def __init__(self, user_repo):
        self.user_repo = user_repo

    async def _safe_transition_to_text(self, query, text: str, keyboard=None, parse_mode='Markdown'):
        """
        Gère intelligemment la transition d'un message (photo ou texte) vers un message texte

        Problème résolu:
        - Les carousels ont des photos → edit_message_text() échoue
        - Solution: Détecter photo et supprimer/renvoyer au lieu d'éditer
        """
        try:
            # Si le message original a une photo, on ne peut pas edit_message_text
            if query.message.photo:
                # Supprimer l'ancien message avec photo
                try:
                    await query.message.delete()
                except:
                    pass

                # Envoyer nouveau message texte
                await query.message.get_bot().send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
            else:
                # Message texte normal, on peut éditer
                await query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"Error in _safe_transition_to_text: {e}")
            # Fallback ultime : nouveau message
            try:
                await query.message.delete()
            except:
                pass
            await query.message.get_bot().send_message(
                chat_id=query.message.chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )

    async def start_command(self, marketplace_bot, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Nouveau menu d'accueil marketplace"""
        user = update.effective_user
        # Conserver l'état (ne pas déconnecter). Simplement assurer l'inscription DB.
        self.user_repo.add_user(user.id, user.username, user.first_name, user.language_code or 'fr')

        # Déterminer la langue depuis la base si disponible (persistance)
        user_data = self.user_repo.get_user(user.id)
        lang = user_data['language_code'] if user_data and user_data.get('language_code') else (user.language_code or 'fr')

        welcome_text = i18n(lang, 'welcome')

        # Add product ID search hint (BUYER_WORKFLOW_V2_SPEC.md: "À N'IMPORTE QUELLE étape")
        search_hint = "\n\n────────────────\n🔍 _Vous avez un ID produit ? Entrez-le directement (ex: TBF-12345678)_" if lang == 'fr' else "\n\n────────────────\n🔍 _Have a product ID? Enter it directly (e.g. TBF-12345678)_"
        welcome_text += search_hint

        # Construire dynamiquement le menu principal pour éviter les doublons
        is_seller = user_data and user_data.get('is_seller')

        # Row 1: Acheter + Vendre (ou Dashboard) sur la même ligne
        if is_seller and marketplace_bot.is_seller_logged_in(user.id):
            keyboard = [
                [InlineKeyboardButton(i18n(lang, 'buy_menu'), callback_data='buy_menu'),
                 InlineKeyboardButton(i18n(lang, 'seller_dashboard'), callback_data='seller_dashboard')]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton(i18n(lang, 'buy_menu'), callback_data='buy_menu'),
                 InlineKeyboardButton(i18n(lang, 'sell_menu'), callback_data='sell_menu')]
            ]

        # Row 2: Support
        keyboard.append([
            InlineKeyboardButton(i18n(lang, 'support'), callback_data='support_menu')
        ])
        keyboard.append([
            InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'), InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')
        ])

        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

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
        user_id = query.from_user.id
        user_data = self.user_repo.get_user(user_id)
        is_seller = user_data and user_data['is_seller']

        # Récupérer l'instance bot depuis le query
        bot = getattr(query, '_bot', None) or getattr(query, 'bot', None)

        # Row 1: Acheter + Vendre (ou Dashboard) sur la même ligne
        if is_seller and bot and bot.is_seller_logged_in(user_id):
            keyboard = [
                [InlineKeyboardButton(i18n(lang, 'buy_menu'), callback_data='buy_menu'),
                 InlineKeyboardButton(i18n(lang, 'seller_dashboard'), callback_data='seller_dashboard')]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton(i18n(lang, 'buy_menu'), callback_data='buy_menu'),
                 InlineKeyboardButton(i18n(lang, 'sell_menu'), callback_data='sell_menu')]
            ]

        # Row 2: Support et langues
        keyboard.extend([
            [InlineKeyboardButton(i18n(lang, 'support'), callback_data='support_menu')],
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data='lang_fr'),
                InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')
            ]
        ])

        welcome_text = i18n(lang, 'welcome')

        # Add product ID search hint (BUYER_WORKFLOW_V2_SPEC.md: "À N'IMPORTE QUELLE étape")
        search_hint = "\n\n────────────────\n🔍 _Vous avez un ID produit ? Entrez-le directement (ex: TBF-12345678)_" if lang == 'fr' else "\n\n────────────────\n🔍 _Have a product ID? Enter it directly (e.g. TBF-12345678)_"
        welcome_text += search_hint

        try:
            await query.edit_message_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')

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
        user_id = query.from_user.id
        # Clean any conflicting states when returning to main menu
        marketplace_bot.reset_conflicting_states(user_id)

        user_data = self.user_repo.get_user(user_id)
        is_seller = user_data and user_data.get('is_seller')

        # Row 1: Acheter + Vendre (ou Dashboard) sur la même ligne
        if is_seller and marketplace_bot.is_seller_logged_in(user_id):
            keyboard = [
                [InlineKeyboardButton(i18n(lang, 'buy_menu'), callback_data='buy_menu'),
                 InlineKeyboardButton(i18n(lang, 'seller_dashboard'), callback_data='seller_dashboard')]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton(i18n(lang, 'buy_menu'), callback_data='buy_menu'),
                 InlineKeyboardButton(i18n(lang, 'sell_menu'), callback_data='sell_menu')]
            ]

        # Row 2: Support et langues
        keyboard.extend([
            [InlineKeyboardButton(i18n(lang, 'support'), callback_data='support_menu')],
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data='lang_fr'),
                InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')
            ]
        ])

        welcome_text = i18n(lang, 'welcome')

        # Add product ID search hint
        search_hint = "\n\n────────────────\n🔍 _Vous avez un ID produit ? Entrez-le directement (ex: TBF-12345678)_" if lang == 'fr' else "\n\n────────────────\n🔍 _Have a product ID? Enter it directly (e.g. TBF-12345678)_"
        welcome_text += search_hint

        await self._safe_transition_to_text(
            query,
            welcome_text,
            InlineKeyboardMarkup(keyboard)
        )