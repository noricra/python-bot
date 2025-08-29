"""
Order handler for Telegram bot operations.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.application.use_cases import OrderService, ProductService
from app.interfaces.telegram.handlers.base_handler import BaseHandler


class OrderHandler(BaseHandler):
    """Handler for order-related operations."""
    
    def __init__(self, order_service: OrderService, product_service: ProductService):
        super().__init__()
        self.order_service = order_service
        self.product_service = product_service
    
    async def show_buyer_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show orders for buyer."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        try:
            orders = await self.order_service.get_buyer_orders(user_id)
            
            if not orders:
                await query.edit_message_text(
                    "📦 **MES COMMANDES**\\n\\n"
                    "Vous n'avez pas encore passé de commande\\.",
                    parse_mode='MarkdownV2'
                )
                return
            
            orders_text = "📦 **MES COMMANDES**\\n\\n"
            keyboard = []
            
            for order in orders[:10]:  # Limit to 10 recent orders
                product = await self.product_service.get_product(order.product_id)
                product_title = product.title if product else "Produit supprimé"
                
                status_emoji = {
                    'pending': '⏳',
                    'paid': '✅', 
                    'completed': '🎉',
                    'cancelled': '❌',
                    'refunded': '🔄'
                }.get(order.status.value, '❓')
                
                orders_text += f"""
{status_emoji} **{self.escape_markdown_text(product_title)}**
💰 {self.format_price(float(order.amount_eur))} • 📅 {order.creation_date.strftime('%d/%m/%Y') if order.creation_date else 'N/A'}

"""
                
                if order.can_download:
                    keyboard.append([InlineKeyboardButton(
                        f"📥 Télécharger - {product_title[:20]}...", 
                        callback_data=f'download_{order.order_id}'
                    )])
            
            keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')])
            
            await query.edit_message_text(
                orders_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing buyer orders: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement des commandes."
            )