from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import BotCommand, BotCommandScopeDefault

from app.core import settings as core_settings
from app.core.i18n import t as i18n


def build_application(bot_instance) -> Application:
    application = Application.builder().token(core_settings.TELEGRAM_TOKEN).build()

    # ✅ CRITICAL: Store bot_instance in bot_data for miniapp access
    application.bot_data['bot_instance'] = bot_instance

    # Use handlers instead of direct bot methods
    application.add_handler(CommandHandler("start", lambda update, context: bot_instance.core_handlers.start_command(bot_instance, update, context)))
    
    # Simple admin command handler
    async def admin_command_wrapper(update, context):
        # Check if user is admin
        if update.effective_user.id == core_settings.ADMIN_USER_ID:
            # Create a robust mock query for admin menu
            class MockQuery:
                def __init__(self, user, update_obj, bot):
                    self.from_user = user
                    self._bot = bot
                    self.message = update_obj.message  # AJOUT CRITIQUE pour CarouselHelper
                    self.effective_chat = update_obj.effective_chat # AJOUT CRITIQUE
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

            mock_query = MockQuery(update.effective_user, update, bot_instance)
            lang = bot_instance.get_user_language(update.effective_user.id)
            await bot_instance.admin_handlers.admin_menu(bot_instance, mock_query, lang)
        else:
            await update.message.reply_text(i18n('fr', 'bot_access_denied'))

    application.add_handler(CommandHandler("admin", admin_command_wrapper))

    # Help/support commands
    application.add_handler(CommandHandler("help", lambda update, context: bot_instance.core_handlers.help_command(bot_instance, update, context)))
    application.add_handler(CommandHandler("support", lambda update, context: bot_instance.support_handlers.support_command(bot_instance, update, context)))

    # Quick access commands for main features
    async def achat_command_wrapper(update, context):
        """Quick access to buy menu"""
        class MockQuery:
            def __init__(self, user, update_obj):
                self.from_user = user
                self.message = update_obj.message
                self.effective_chat = update_obj.effective_chat
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user, update)
        lang = bot_instance.get_user_language(update.effective_user.id)
        await bot_instance.buy_handlers.buy_menu(bot_instance, mock_query, lang)

    async def vendre_command_wrapper(update, context):
        """Quick access to sell menu"""
        class MockQuery:
            def __init__(self, user, update_obj):
                self.from_user = user
                self.message = update_obj.message 
                self.effective_chat = update_obj.effective_chat
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user, update)
        lang = bot_instance.get_user_language(update.effective_user.id)
        await bot_instance.sell_handlers.sell_menu(bot_instance, mock_query, lang)

    async def library_command_wrapper(update, context):
        """Quick access to library"""
        class MockQuery:
            def __init__(self, user, update_obj):
                self.from_user = user
                self.message = update_obj.message 
                self.effective_chat = update_obj.effective_chat
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            def get_bot(self):
                return context.bot

        mock_query = MockQuery(update.effective_user, update)
        lang = bot_instance.get_user_language(update.effective_user.id)
        # Appel asynchrone
        await bot_instance.library_handlers.show_library(bot_instance, mock_query, lang)

    async def stats_command_wrapper(update, context):
        """Quick access to seller stats (if seller)"""
        user_id = update.effective_user.id
        from app.domain.repositories.user_repo import UserRepository
        user_repo = UserRepository()
        user = user_repo.get_user(user_id)

        class MockQuery:
            def __init__(self, user, update_obj):
                self.from_user = user
                self.message = update_obj.message 
                self.effective_chat = update_obj.effective_chat
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            async def answer(self, text=None):
                pass 

        mock_query = MockQuery(update.effective_user, update)
        lang = bot_instance.get_user_language(user_id)

        if user and user.get('is_seller'):
            await bot_instance.sell_handlers.seller_dashboard(bot_instance, mock_query, lang)
        else:
            await update.message.reply_text(
                "📊 Cette commande est réservée aux vendeurs.\n\n"
                "💡 Pour devenir vendeur, utilisez /vendre",
                parse_mode='Markdown'
            )

    async def shop_command_wrapper(update, context):
        """View a seller's complete shop: /shop @username or /shop <user_id>"""
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "🛍️ **Voir la boutique d'un vendeur**\n\n"
                "Utilisez: `/shop @username` ou `/shop <user_id>`\n\n"
                "Exemple:\n"
                "• `/shop @johnvendeur`\n"
                "• `/shop 123456789`",
                parse_mode='Markdown'
            )
            return

        seller_identifier = context.args[0]

        from app.domain.repositories.user_repo import UserRepository
        from app.domain.repositories.product_repo import ProductRepository

        user_repo = UserRepository()
        product_repo = ProductRepository()

        seller = None
        if seller_identifier.startswith('@'):
            username = seller_identifier[1:]
            from app.core.database_init import get_postgresql_connection
            from app.core.db_pool import put_connection
            import psycopg2.extras
            conn = get_postgresql_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT * FROM users WHERE LOWER(username) = LOWER(%s) AND is_seller = TRUE', (username,))
            seller = cursor.fetchone()
            if seller:
                seller = dict(seller)
            put_connection(conn)
        else:
            try:
                seller_id = int(seller_identifier)
                seller = user_repo.get_user(seller_id)
                if seller and not seller.get('is_seller'):
                    seller = None
            except ValueError:
                pass

        if not seller:
            await update.message.reply_text(
                "❌ Vendeur introuvable ou utilisateur non vendeur.",
                parse_mode='Markdown'
            )
            return

        class MockQuery:
            def __init__(self, user, update_obj, bot):
                self.from_user = user
                self.effective_chat = update_obj.effective_chat
                self.bot = bot
                self._update = update_obj
                self.message = update_obj.message 
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await self._update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user, update, context.bot)
        lang = bot_instance.get_user_language(update.effective_user.id)

        await bot_instance.buy_handlers.show_seller_shop(bot_instance, mock_query, seller['user_id'], lang)

    application.add_handler(CommandHandler("achat", achat_command_wrapper))
    application.add_handler(CommandHandler("vendre", vendre_command_wrapper))
    application.add_handler(CommandHandler("library", library_command_wrapper))
    application.add_handler(CommandHandler("stats", stats_command_wrapper))
    application.add_handler(CommandHandler("shop", shop_command_wrapper))
    
    # Use callback router for button handling
    async def callback_handler_wrapper(update, context):
        query = update.callback_query
        success = await bot_instance.callback_router.route(query)
        if not success:
            try:
                await query.answer() 
            except:
                pass

    application.add_handler(CallbackQueryHandler(callback_handler_wrapper))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_text_message)
    )
    application.add_handler(MessageHandler(filters.Document.ALL, bot_instance.handle_document_upload))
    application.add_handler(MessageHandler(filters.PHOTO, bot_instance.handle_photo_upload))

    # --- CONFIGURATION DES COMMANDES MULTILANGUES ---
    async def post_init(app):
        try:
            # Commandes en Français (Défaut)
            commands_fr = [
                ("start", " Menu principal"),
                ("achat", " Acheter des produits"),
                ("vendre", " Vendre mes produits"),
                ("library", " Ma bibliothèque"),
                ("stats", " Mes statistiques vendeur"),
                ("shop", " Voir boutique vendeur"),
                ("help", " Aide"),
                ("support", " Support"),
            ]
            
            # Commandes en Anglais
            commands_en = [
                ("start", " Main menu"),
                ("achat", " Buy products"),
                ("sell", " Sell my products"),
                ("library", " My library"),
                ("stats", " Seller statistics"),
                ("shop", " View seller shop"),
                ("help", " Help"),
                ("support", " Support"),
            ]

            # 1. Définir les commandes par défaut (Français pour tout le monde sauf exception)
            await app.bot.set_my_commands(
                [BotCommand(name, desc) for name, desc in commands_fr],
                scope=BotCommandScopeDefault()
            )
            
            # 2. Définir les commandes spécifiques pour les utilisateurs Anglais
            # Telegram détecte la langue de l'app de l'utilisateur
            await app.bot.set_my_commands(
                [BotCommand(name, desc) for name, desc in commands_en],
                language_code='en'
            )
            
            # 3. Redéfinir explicitement pour le Français (pour être sûr)
            await app.bot.set_my_commands(
                [BotCommand(name, desc) for name, desc in commands_fr],
                language_code='fr'
            )
            
        except Exception as e:
            print(f"⚠️ Erreur setting commands: {e}")

    application.post_init = post_init

    return application
