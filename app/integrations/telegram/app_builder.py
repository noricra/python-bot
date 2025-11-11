from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import BotCommand

from app.core import settings as core_settings
from app.core.i18n import t as i18n


def build_application(bot_instance) -> Application:
    application = Application.builder().token(core_settings.TELEGRAM_TOKEN).build()

    # Use handlers instead of direct bot methods
    application.add_handler(CommandHandler("start", lambda update, context: bot_instance.core_handlers.start_command(bot_instance, update, context)))
    # Simple admin command handler
    async def admin_command_wrapper(update, context):
        # Check if user is admin (simplified check using ADMIN_USER_ID from settings)
        if update.effective_user.id == core_settings.ADMIN_USER_ID:
            # Create a mock query object for admin menu
            class MockQuery:
                def __init__(self, user, bot):
                    self.from_user = user
                    self._bot = bot
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

            mock_query = MockQuery(update.effective_user, bot_instance)
            # Get user language and call admin_menu
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
            def __init__(self, user, update_obj, bot):
                self.from_user = user
                self.effective_chat = update_obj.effective_chat
                self.bot = bot
                self._update = update_obj
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await self._update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user, update, context.bot)
        lang = bot_instance.get_user_language(update.effective_user.id)
        await bot_instance.buy_handlers.buy_menu(bot_instance, mock_query, lang)

    async def vendre_command_wrapper(update, context):
        """Quick access to sell menu"""
        class MockQuery:
            def __init__(self, user):
                self.from_user = user
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user)
        lang = bot_instance.get_user_language(update.effective_user.id)
        await bot_instance.sell_handlers.sell_menu(bot_instance, mock_query, lang)

    async def library_command_wrapper(update, context):
        """Quick access to library"""
        class MockQuery:
            def __init__(self, user):
                self.from_user = user
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user)
        lang = bot_instance.get_user_language(update.effective_user.id)
        await bot_instance.library_handlers.show_library(bot_instance, mock_query, lang)

    async def stats_command_wrapper(update, context):
        """Quick access to seller stats (if seller)"""
        user_id = update.effective_user.id
        from app.domain.repositories.user_repo import UserRepository
        user_repo = UserRepository()
        user = user_repo.get_user(user_id)

        class MockQuery:
            def __init__(self, user):
                self.from_user = user
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user)
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
        # Extract seller identifier from command
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

        # Import required modules
        from app.domain.repositories.user_repo import UserRepository
        from app.domain.repositories.product_repo import ProductRepository

        user_repo = UserRepository()
        product_repo = ProductRepository()

        # Find seller by username or ID
        seller = None
        if seller_identifier.startswith('@'):
            username = seller_identifier[1:]  # Remove @
            # Search by username (case-insensitive)
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
                    seller = None  # Not a seller
            except ValueError:
                pass

        if not seller:
            await update.message.reply_text(
                "❌ Vendeur introuvable ou utilisateur non vendeur.",
                parse_mode='Markdown'
            )
            return

        # Get seller's products
        products = product_repo.get_products_by_seller(seller['user_id'])

        seller_name = seller.get('seller_name') or seller.get('first_name') or "Vendeur"
        seller_bio = seller.get('seller_bio') or "Aucune bio"

        # Call the buy_handlers method to show seller shop
        class MockQuery:
            def __init__(self, user, update_obj, bot):
                self.from_user = user
                self.effective_chat = update_obj.effective_chat
                self.bot = bot
                self._update = update_obj
                # Add message attribute for fallback
                self.message = update_obj.message
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                await self._update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

        mock_query = MockQuery(update.effective_user, update, context.bot)
        lang = bot_instance.get_user_language(update.effective_user.id)

        # Use existing show_seller_shop method
        await bot_instance.buy_handlers.show_seller_shop(bot_instance, mock_query, seller['user_id'], lang)

    application.add_handler(CommandHandler("achat", achat_command_wrapper))
    application.add_handler(CommandHandler("vendre", vendre_command_wrapper))
    application.add_handler(CommandHandler("library", library_command_wrapper))
    application.add_handler(CommandHandler("stats", stats_command_wrapper))
    application.add_handler(CommandHandler("shop", shop_command_wrapper))
    # Use callback router for button handling
    async def callback_handler_wrapper(update, context):
        query = update.callback_query
        print(f"DEBUG CALLBACK: {query.data}")  # Debug immédiat
        await query.answer()
        # Route through the centralized callback router
        success = await bot_instance.callback_router.route(query)
        if not success:
            # Fallback error message
            from app.core.i18n import t as i18n
            lang = bot_instance.get_user_language(query.from_user.id)
            await query.edit_message_text(i18n(lang, 'err_temp'))

    application.add_handler(CallbackQueryHandler(callback_handler_wrapper))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_text_message)
    )
    # Document handler for file uploads
    application.add_handler(MessageHandler(filters.Document.ALL, bot_instance.handle_document_upload))

    # Photo handler for cover image uploads
    application.add_handler(MessageHandler(filters.PHOTO, bot_instance.handle_photo_upload))

    # Set bot commands for quick access - will be set when bot starts
    async def post_init(app):
        try:
            commands = [
                ("start", " Menu principal"),
                ("achat", " Acheter des produits"),
                ("vendre", " Vendre mes produits"),
                ("library", " Ma bibliothèque"),
                ("stats", " Mes statistiques vendeur"),
                ("shop", " Voir boutique vendeur"),
                ("help", " Aide"),
                ("support", " Support"),
            ]
            await app.bot.set_my_commands([BotCommand(name, desc) for name, desc in commands])
        except Exception:
            pass

    application.post_init = post_init

    return application

