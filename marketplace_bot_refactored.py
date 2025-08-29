#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechBot Marketplace - Refactored Clean Architecture Version
Version 3.0 - Modern, maintainable, and scalable architecture
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Import our clean architecture components
from app.core import settings, configure_logging
from app.infrastructure.database import (
    SqliteUserRepository,
    SqliteProductRepository, 
    SqliteOrderRepository,
    SqliteWalletRepository,
    SqlitePayoutRepository
)
from app.application.use_cases import (
    UserService,
    ProductService,
    OrderService,
    PaymentService,
    WalletService
)
from app.interfaces.telegram.handlers import (
    UserHandler,
    ProductHandler,
    OrderHandler,
    PaymentHandler,
    AdminHandler
)
from app.integrations.telegram.keyboards import main_menu_keyboard

# Configure logging
configure_logging(settings)
logger = logging.getLogger(__name__)


class MarketplaceBotRefactored:
    """
    Refactored marketplace bot using Clean Architecture.
    
    This is the main application class that orchestrates all components
    following dependency injection and clean architecture principles.
    """
    
    def __init__(self):
        """Initialize the bot with all dependencies."""
        self._setup_repositories()
        self._setup_services()
        self._setup_handlers()
        self._setup_database()
    
    def _setup_repositories(self):
        """Setup data access repositories."""
        self.user_repository = SqliteUserRepository()
        self.product_repository = SqliteProductRepository()
        self.order_repository = SqliteOrderRepository()
        self.wallet_repository = SqliteWalletRepository()
        self.payout_repository = SqlitePayoutRepository()
    
    def _setup_services(self):
        """Setup business logic services."""
        self.user_service = UserService(self.user_repository)
        self.product_service = ProductService(self.product_repository, self.user_repository)
        self.wallet_service = WalletService(self.wallet_repository, self.user_repository)
        self.order_service = OrderService(
            self.order_repository, 
            self.product_repository, 
            self.user_repository
        )
        self.payment_service = PaymentService(
            self.order_repository,
            self.payout_repository,
            self.user_repository,
            self.wallet_service,
            self.order_service
        )
    
    def _setup_handlers(self):
        """Setup Telegram handlers."""
        self.user_handler = UserHandler(self.user_service)
        self.product_handler = ProductHandler(self.product_service, self.user_service)
        self.order_handler = OrderHandler(self.order_service, self.product_service)
        self.payment_handler = PaymentHandler(
            self.payment_service, 
            self.wallet_service,
            self.product_service, 
            self.order_service
        )
        self.admin_handler = AdminHandler(
            self.user_service,
            self.product_service, 
            self.order_service,
            self.payment_service
        )
    
    def _setup_database(self):
        """Initialize database tables."""
        # For now, we'll use the existing database initialization
        # TODO: Move to proper migration system
        pass
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        # Register or get user
        await self.user_handler.register_or_get_user(update)
        
        welcome_text = f"""
🎉 **Bienvenue sur TechBot Marketplace !**

Bonjour {update.effective_user.first_name} !

🏪 **Votre marketplace de formations**
• 📚 Achetez des formations de qualité
• 💰 Vendez vos propres contenus
• 🔐 Paiements crypto sécurisés
• 💳 Wallet intégré

**Que souhaitez-vous faire ?**
        """
        
        keyboard = main_menu_keyboard()
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = """
🆘 **AIDE - TECHBOT MARKETPLACE**

**📚 ACHETEURS**
• `/start` - Démarrer le bot
• Parcourir les catégories de formations
• Rechercher par ID produit
• Payer en crypto ou wallet

**🏪 VENDEURS**
• Créer un compte vendeur
• Ajouter vos formations
• Gérer vos produits
• Suivre vos ventes

**💰 WALLET**
• Voir votre solde
• Historique des transactions
• Demander des payouts

**🔐 SÉCURITÉ**
• Paiements chiffrés
• Adresses crypto vérifiées
• Support réactif

**📞 SUPPORT**
Contactez l'équipe pour toute question !
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode='MarkdownV2'
        )
    
    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all callback queries."""
        query = update.callback_query
        data = query.data
        
        try:
            # Route callbacks to appropriate handlers
            if data == 'back_main':
                await self.back_to_main(update, context)
            
            # User-related callbacks
            elif data in ['sell_menu', 'seller_info', 'create_seller', 'seller_dashboard', 'seller_logout']:
                await self._route_user_callback(update, context)
            
            # Product-related callbacks
            elif data in ['buy_menu', 'browse_categories', 'search_product', 'category_bestsellers', 'category_new'] or \
                 data.startswith(('category_', 'product_', 'buy_')):
                await self._route_product_callback(update, context)
            
            # Order-related callbacks
            elif data in ['my_orders'] or data.startswith('download_'):
                await self._route_order_callback(update, context)
            
            # Payment-related callbacks
            elif data in ['my_wallet', 'wallet_history', 'request_payout'] or data.startswith('pay_'):
                await self._route_payment_callback(update, context)
            
            # Admin callbacks
            elif data.startswith('admin_'):
                await self._route_admin_callback(update, context)
            
            else:
                await query.answer("Fonction non implémentée.")
                
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            await query.answer("Erreur lors du traitement de la demande.")
    
    async def _route_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route user-related callbacks."""
        data = update.callback_query.data
        
        if data == 'sell_menu':
            await self.user_handler.seller_info(update, context)
        elif data == 'seller_info':
            await self.user_handler.seller_info(update, context)
        elif data == 'create_seller':
            await self.user_handler.create_seller_start(update, context)
        elif data == 'seller_dashboard':
            await self.user_handler.seller_dashboard(update, context)
        elif data == 'seller_logout':
            await self.user_handler.seller_logout(update, context)
    
    async def _route_product_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route product-related callbacks."""
        data = update.callback_query.data
        
        if data == 'buy_menu':
            await self.show_buy_menu(update, context)
        elif data == 'browse_categories':
            await self.product_handler.browse_categories(update, context)
        elif data == 'search_product':
            await self.product_handler.search_product_prompt(update, context)
        elif data == 'category_bestsellers':
            await self.product_handler.show_bestsellers(update, context)
        elif data == 'category_new':
            await self.product_handler.show_newest_products(update, context)
        elif data.startswith('category_'):
            await self.product_handler.show_category_products(update, context)
        elif data.startswith('product_'):
            await self.product_handler.show_product_details(update, context)
        elif data.startswith('buy_'):
            await self.payment_handler.initiate_purchase(update, context)
    
    async def _route_order_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route order-related callbacks."""
        data = update.callback_query.data
        
        if data == 'my_orders':
            await self.order_handler.show_buyer_orders(update, context)
        elif data.startswith('download_'):
            # TODO: Implement download functionality
            await update.callback_query.answer("Téléchargement non encore implémenté.")
    
    async def _route_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route payment-related callbacks."""
        data = update.callback_query.data
        
        if data == 'my_wallet':
            await self.payment_handler.show_wallet_info(update, context)
        elif data.startswith('pay_wallet_'):
            await self.payment_handler.process_wallet_payment(update, context)
        elif data.startswith('pay_crypto_'):
            # TODO: Implement crypto payment
            await update.callback_query.answer("Paiement crypto non encore implémenté.")
    
    async def _route_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route admin-related callbacks."""
        data = update.callback_query.data
        
        if data == 'admin_panel':
            await self.admin_handler.admin_panel(update, context)
        elif data == 'admin_stats':
            await self.admin_handler.admin_stats(update, context)
    
    async def show_buy_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show buy menu."""
        query = update.callback_query
        await query.answer()
        
        buy_text = """
🛒 **ACHETER UNE FORMATION**

Explorez notre catalogue de formations de qualité :
        """
        
        from app.integrations.telegram.keyboards import buy_menu_keyboard
        keyboard = buy_menu_keyboard()
        
        await query.edit_message_text(
            buy_text,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to main menu."""
        query = update.callback_query
        await query.answer()
        
        main_text = """
🏠 **MENU PRINCIPAL**

Bienvenue sur TechBot Marketplace !

Que souhaitez-vous faire ?
        """
        
        keyboard = main_menu_keyboard()
        
        await query.edit_message_text(
            main_text,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        user_id = update.effective_user.id
        
        # Check if user is in a specific input state
        if hasattr(self.user_handler, 'get_user_state'):
            state = self.user_handler.get_user_state(user_id)
            
            if state.get('creating_seller'):
                await self.user_handler.handle_seller_creation_input(update, context)
                return
            
            if state.get('searching_product'):
                await self.product_handler.handle_product_search(update, context)
                return
        
        # Default response
        await update.message.reply_text(
            "🤖 Utilisez les boutons du menu ou tapez /start pour commencer !"
        )


def create_application() -> Application:
    """Create and configure the Telegram application."""
    if not settings.TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN is required")
    
    bot = MarketplaceBotRefactored()
    application = Application.builder().token(settings.TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CallbackQueryHandler(bot.callback_query_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_handler))
    
    return application


def main():
    """Main function to start the bot."""
    try:
        logger.info("🚀 Starting TechBot Marketplace (Refactored)...")
        logger.info("✅ Clean Architecture enabled")
        logger.info("✅ Dependency Injection configured") 
        logger.info("✅ Separation of concerns implemented")
        logger.info("✅ Testable components ready")
        
        application = create_application()
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise


if __name__ == '__main__':
    main()