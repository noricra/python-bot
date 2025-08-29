"""
Product handler for Telegram bot operations.
"""

from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.application.use_cases import ProductService, UserService
from app.interfaces.telegram.handlers.base_handler import BaseHandler
from app.core.exceptions import ValidationError, NotFoundError, UnauthorizedError


class ProductHandler(BaseHandler):
    """Handler for product-related operations."""
    
    def __init__(self, product_service: ProductService, user_service: UserService):
        super().__init__()
        self.product_service = product_service
        self.user_service = user_service
    
    async def browse_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show product categories."""
        query = update.callback_query
        await query.answer()
        
        categories = [
            ("💻", "développement", "Développement"),
            ("📱", "mobile", "Développement Mobile"),
            ("🎨", "design", "Design & UI/UX"),
            ("💰", "business", "Business & Vente"),
            ("📊", "marketing", "Marketing Digital"),
            ("🔐", "cybersécurité", "Cybersécurité"),
            ("🤖", "ia", "Intelligence Artificielle"),
            ("☁️", "cloud", "Cloud & DevOps")
        ]
        
        keyboard = []
        for icon, key, name in categories:
            keyboard.append([InlineKeyboardButton(
                f"{icon} {name}", 
                callback_data=f'category_{key}'
            )])
        
        keyboard.append([InlineKeyboardButton("🏠 Retour menu", callback_data='back_main')])
        
        await query.edit_message_text(
            "📂 **CATÉGORIES DE FORMATIONS**\\n\\n"
            "Choisissez une catégorie pour voir les formations disponibles:",
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_category_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show products in a category."""
        query = update.callback_query
        await query.answer()
        
        category_key = query.data.replace('category_', '')
        
        try:
            products = await self.product_service.get_products_by_category(category_key, limit=10)
            
            if not products:
                await query.edit_message_text(
                    f"📂 **{category_key.upper()}**\\n\\n"
                    "Aucune formation disponible dans cette catégorie pour le moment\\.",
                    parse_mode='MarkdownV2'
                )
                return
            
            products_text = f"📂 **{category_key.upper()}**\\n\\n"
            
            keyboard = []
            for product in products:
                products_text += f"""
🏷️ **{self.escape_markdown_text(product.title)}**
💰 {self.format_price(float(product.price_eur))} • 📊 {product.sales_count} ventes • ⭐ {product.rating}/5
📝 {self.escape_markdown_text(product.description[:100])}...

"""
                keyboard.append([InlineKeyboardButton(
                    f"📖 {product.title[:30]}...", 
                    callback_data=f'product_{product.product_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("📂 Autres catégories", callback_data='browse_categories')])
            keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')])
            
            await query.edit_message_text(
                products_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing category products: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement des produits."
            )
    
    async def show_product_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show detailed product information."""
        query = update.callback_query
        await query.answer()
        
        product_id = query.data.replace('product_', '')
        
        try:
            product = await self.product_service.get_product(product_id)
            if not product:
                await query.edit_message_text("❌ Produit non trouvé.")
                return
            
            # Get seller info
            seller = await self.user_service.get_user(product.seller_user_id)
            seller_name = seller.seller_name if seller else "Vendeur inconnu"
            
            product_text = f"""
📖 **{self.escape_markdown_text(product.title)}**

**💰 Prix:** {self.format_price(float(product.price_eur))}
**👤 Vendeur:** {self.escape_markdown_text(seller_name)}
**📊 Statistiques:** {product.sales_count} ventes • ⭐ {product.rating}/5
**📂 Catégorie:** {self.escape_markdown_text(product.category)}

**📝 Description:**
{self.escape_markdown_text(product.description)}
            """
            
            if product.preview_text:
                product_text += f"""

**👀 Aperçu:**
{self.escape_markdown_text(product.preview_text)}
                """
            
            keyboard = []
            
            # Only show purchase button if product is available
            if product.is_available:
                keyboard.append([InlineKeyboardButton(
                    f"🛒 Acheter - {self.format_price(float(product.price_eur))}", 
                    callback_data=f'buy_{product.product_id}'
                )])
            else:
                product_text += "\n\n⚠️ **Produit non disponible**"
            
            keyboard.append([InlineKeyboardButton("📂 Retour catégorie", callback_data='browse_categories')])
            keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')])
            
            await query.edit_message_text(
                product_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing product details: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement du produit."
            )
    
    async def search_product_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prompt for product search."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        self.update_user_state(user_id, searching_product=True)
        
        await query.edit_message_text(
            "🔍 **RECHERCHE DE PRODUIT**\\n\\n"
            "Entrez l'ID exact du produit que vous recherchez\\n\\n"
            "💡 Format: TBF\\-YYMM\\-XXXXXX",
            parse_mode='MarkdownV2'
        )
    
    async def handle_product_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle product search input."""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        
        if not state.get('searching_product'):
            return
        
        product_id = update.message.text.strip().upper()
        self.update_user_state(user_id, searching_product=False)
        
        try:
            product = await self.product_service.get_product(product_id)
            if not product:
                await update.message.reply_text(
                    f"❌ Aucun produit trouvé avec l'ID: `{product_id}`",
                    parse_mode='MarkdownV2'
                )
                return
            
            # Show product details
            await self.show_product_by_id(update, product)
            
        except Exception as e:
            print(f"Error searching product: {e}")
            await update.message.reply_text(
                "❌ Erreur lors de la recherche du produit."
            )
    
    async def show_product_by_id(self, update: Update, product) -> None:
        """Show product found by ID search."""
        try:
            seller = await self.user_service.get_user(product.seller_user_id)
            seller_name = seller.seller_name if seller else "Vendeur inconnu"
            
            product_text = f"""
✅ **PRODUIT TROUVÉ**

📖 **{self.escape_markdown_text(product.title)}**
🆔 **ID:** `{product.product_id}`
💰 **Prix:** {self.format_price(float(product.price_eur))}
👤 **Vendeur:** {self.escape_markdown_text(seller_name)}

📝 **Description:**
{self.escape_markdown_text(product.description[:200])}...
            """
            
            keyboard = []
            if product.is_available:
                keyboard.append([InlineKeyboardButton(
                    f"🛒 Acheter - {self.format_price(float(product.price_eur))}", 
                    callback_data=f'buy_{product.product_id}'
                )])
                keyboard.append([InlineKeyboardButton(
                    "📖 Voir détails complets", 
                    callback_data=f'product_{product.product_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')])
            
            await update.message.reply_text(
                product_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing product by ID: {e}")
            await update.message.reply_text(
                "❌ Erreur lors de l'affichage du produit."
            )
    
    async def show_bestsellers(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bestselling products."""
        query = update.callback_query
        await query.answer()
        
        try:
            products = await self.product_service.get_bestsellers(limit=10)
            
            if not products:
                await query.edit_message_text(
                    "🔥 **MEILLEURES VENTES**\\n\\n"
                    "Aucun produit disponible pour le moment\\.",
                    parse_mode='MarkdownV2'
                )
                return
            
            products_text = "🔥 **MEILLEURES VENTES**\\n\\n"
            keyboard = []
            
            for i, product in enumerate(products, 1):
                products_text += f"""
{i}\\. **{self.escape_markdown_text(product.title)}**
💰 {self.format_price(float(product.price_eur))} • 📊 {product.sales_count} ventes • ⭐ {product.rating}/5

"""
                keyboard.append([InlineKeyboardButton(
                    f"#{i} {product.title[:25]}...", 
                    callback_data=f'product_{product.product_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')])
            
            await query.edit_message_text(
                products_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing bestsellers: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement des meilleures ventes."
            )
    
    async def show_newest_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show newest products."""
        query = update.callback_query
        await query.answer()
        
        try:
            products = await self.product_service.get_newest_products(limit=10)
            
            if not products:
                await query.edit_message_text(
                    "🆕 **NOUVEAUTÉS**\\n\\n"
                    "Aucun nouveau produit disponible pour le moment\\.",
                    parse_mode='MarkdownV2'
                )
                return
            
            products_text = "🆕 **NOUVEAUTÉS**\\n\\n"
            keyboard = []
            
            for product in products:
                products_text += f"""
📖 **{self.escape_markdown_text(product.title)}**
💰 {self.format_price(float(product.price_eur))} • 📂 {self.escape_markdown_text(product.category)}

"""
                keyboard.append([InlineKeyboardButton(
                    f"📖 {product.title[:30]}...", 
                    callback_data=f'product_{product.product_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')])
            
            await query.edit_message_text(
                products_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing newest products: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement des nouveautés."
            )