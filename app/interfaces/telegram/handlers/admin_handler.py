"""
Admin handler for Telegram bot operations.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.application.use_cases import UserService, ProductService, OrderService, PaymentService
from app.interfaces.telegram.handlers.base_handler import BaseHandler
from app.core import settings


class AdminHandler(BaseHandler):
    """Handler for admin operations."""
    
    def __init__(self, user_service: UserService, product_service: ProductService,
                 order_service: OrderService, payment_service: PaymentService):
        super().__init__()
        self.user_service = user_service
        self.product_service = product_service
        self.order_service = order_service
        self.payment_service = payment_service
        self.admin_user_id = settings.ADMIN_USER_ID
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == self.admin_user_id
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show admin panel."""
        query = update.callback_query
        await query.answer()
        
        if not self.is_admin(query.from_user.id):
            await query.edit_message_text("❌ Accès non autorisé.")
            return
        
        admin_text = """
👑 **PANEL ADMINISTRATEUR**

Gestion de la marketplace:
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistiques globales", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 Gérer utilisateurs", callback_data='admin_users')],
            [InlineKeyboardButton("📦 Gérer produits", callback_data='admin_products')],
            [InlineKeyboardButton("💰 Gérer payouts", callback_data='admin_payouts')],
            [InlineKeyboardButton("🔧 Maintenance", callback_data='admin_maintenance')],
            [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            admin_text,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show admin statistics."""
        query = update.callback_query
        await query.answer()
        
        if not self.is_admin(query.from_user.id):
            return
        
        try:
            # Get basic stats (simplified)
            stats_text = """
📊 **STATISTIQUES GLOBALES**

Données de la marketplace:

🏪 **Produits:** En cours de calcul...
👥 **Utilisateurs:** En cours de calcul...
💰 **Commandes:** En cours de calcul...
💳 **Revenus:** En cours de calcul...
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 Actualiser", callback_data='admin_stats')],
                [InlineKeyboardButton("👑 Retour panel", callback_data='admin_panel')],
                [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
            ]
            
            await query.edit_message_text(
                stats_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing admin stats: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement des statistiques."
            )