"""
Payment handler for Telegram bot operations.
"""

from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.application.use_cases import PaymentService, WalletService, ProductService, OrderService
from app.domain.entities.order import PaymentMethod
from app.interfaces.telegram.handlers.base_handler import BaseHandler
from app.core.exceptions import PaymentError, InsufficientFundsError


class PaymentHandler(BaseHandler):
    """Handler for payment-related operations."""
    
    def __init__(self, payment_service: PaymentService, wallet_service: WalletService,
                 product_service: ProductService, order_service: OrderService):
        super().__init__()
        self.payment_service = payment_service
        self.wallet_service = wallet_service
        self.product_service = product_service
        self.order_service = order_service
    
    async def initiate_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Initiate product purchase."""
        query = update.callback_query
        await query.answer()
        
        product_id = query.data.replace('buy_', '')
        user_id = query.from_user.id
        
        try:
            product = await self.product_service.get_product(product_id)
            if not product:
                await query.edit_message_text("❌ Produit non trouvé.")
                return
            
            if not product.is_available:
                await query.edit_message_text("❌ Produit non disponible.")
                return
            
            # Check wallet balance
            wallet_balance = await self.wallet_service.get_wallet_balance(user_id)
            
            purchase_text = f"""
🛒 **CONFIRMER L'ACHAT**

📖 **Produit:** {self.escape_markdown_text(product.title)}
💰 **Prix:** {self.format_price(float(product.price_eur))}

💳 **Moyens de paiement disponibles:**
            """
            
            keyboard = []
            
            # Wallet payment option
            if wallet_balance >= product.price_eur:
                purchase_text += f"""
✅ **Wallet:** {self.format_price(float(wallet_balance))} EUR disponible
"""
                keyboard.append([InlineKeyboardButton(
                    f"💳 Payer avec Wallet - {self.format_price(float(product.price_eur))}", 
                    callback_data=f'pay_wallet_{product_id}'
                )])
            else:
                purchase_text += f"""
❌ **Wallet:** {self.format_price(float(wallet_balance))} EUR (insuffisant)
"""
            
            # Crypto payment option
            purchase_text += f"""
💰 **Crypto:** Paiement sécurisé (BTC, ETH, USDT, etc.)
"""
            keyboard.append([InlineKeyboardButton(
                f"🪙 Payer en Crypto - {self.format_price(float(product.price_eur))}", 
                callback_data=f'pay_crypto_{product_id}'
            )])
            
            keyboard.append([InlineKeyboardButton("❌ Annuler", callback_data=f'product_{product_id}')])
            
            await query.edit_message_text(
                purchase_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error initiating purchase: {e}")
            await query.edit_message_text(
                "❌ Erreur lors de l'initialisation de l'achat."
            )
    
    async def process_wallet_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process payment from wallet."""
        query = update.callback_query
        await query.answer()
        
        product_id = query.data.replace('pay_wallet_', '')
        user_id = query.from_user.id
        
        try:
            # Create order
            order = await self.order_service.create_order(
                buyer_id=user_id,
                product_id=product_id,
                payment_method=PaymentMethod.WALLET
            )
            
            # Process payment
            paid_order = await self.payment_service.process_wallet_payment(order.order_id)
            
            success_text = f"""
✅ **PAIEMENT RÉUSSI !**

📖 **Produit:** {self.escape_markdown_text((await self.product_service.get_product(product_id)).title)}
💰 **Montant:** {self.format_price(float(paid_order.amount_eur))}
🆔 **Commande:** `{paid_order.order_id}`

🎉 Votre achat est confirmé ! Vous pouvez maintenant télécharger votre formation\\.
            """
            
            keyboard = [
                [InlineKeyboardButton("📥 Télécharger maintenant", callback_data=f'download_{paid_order.order_id}')],
                [InlineKeyboardButton("📦 Mes commandes", callback_data='my_orders')],
                [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
            ]
            
            await query.edit_message_text(
                success_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except InsufficientFundsError:
            await query.edit_message_text(
                "❌ **Solde insuffisant**\\n\\n"
                "Veuillez recharger votre wallet ou utiliser le paiement crypto\\.",
                parse_mode='MarkdownV2'
            )
        except PaymentError as e:
            await query.edit_message_text(f"❌ Erreur de paiement: {e}")
        except Exception as e:
            print(f"Error processing wallet payment: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du traitement du paiement."
            )
    
    async def show_wallet_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show wallet information."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        try:
            balance = await self.wallet_service.get_wallet_balance(user_id)
            transactions = await self.wallet_service.get_wallet_transactions(user_id, limit=5)
            
            wallet_text = f"""
💳 **MON WALLET**

💰 **Solde actuel:** {self.format_price(float(balance))}

📊 **Dernières transactions:**
            """
            
            if transactions:
                for tx in transactions:
                    tx_type_emoji = {
                        'deposit': '📈',
                        'withdrawal': '📉', 
                        'commission': '🎁',
                        'payout': '💰',
                        'refund': '🔄'
                    }.get(tx.transaction_type.value, '💱')
                    
                    amount_sign = '+' if tx.amount_eur > 0 else ''
                    wallet_text += f"""
{tx_type_emoji} {amount_sign}{self.format_price(float(tx.amount_eur))} - {self.escape_markdown_text(tx.description[:30])}...
"""
            else:
                wallet_text += "\nAucune transaction pour le moment\\."
            
            keyboard = [
                [InlineKeyboardButton("💰 Demander un payout", callback_data='request_payout')],
                [InlineKeyboardButton("📊 Historique complet", callback_data='wallet_history')],
                [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
            ]
            
            await query.edit_message_text(
                wallet_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing wallet info: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement du wallet."
            )