"""
User handler for Telegram bot operations.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.application.use_cases import UserService
from app.interfaces.telegram.handlers.base_handler import BaseHandler
from app.core.exceptions import ValidationError, NotFoundError
from app.core import settings


class UserHandler(BaseHandler):
    """Handler for user-related operations."""
    
    def __init__(self, user_service: UserService):
        super().__init__()
        self.user_service = user_service
    
    async def register_or_get_user(self, update: Update) -> None:
        """Register or get existing user."""
        user = update.effective_user
        try:
            await self.user_service.get_user_or_create(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                language_code=user.language_code or "fr"
            )
        except Exception as e:
            print(f"Error registering user: {e}")
    
    async def seller_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show seller information and benefits."""
        query = update.callback_query
        await query.answer()
        
        info_text = """
🚀 **DEVENIR VENDEUR - CONDITIONS & AVANTAGES**

**💰 COMMISSIONS**
• Commission plateforme : 5%
• Vous gardez 95% de vos ventes !

**🎯 AVANTAGES**
• ✅ Marketplace établie avec acheteurs actifs
• ✅ Paiements crypto sécurisés (8 devises)
• ✅ Wallet intégré pour vos gains
• ✅ Analytics complets de vos ventes
• ✅ Support technique dédié
• ✅ Interface simple et efficace

**📋 PRÉREQUIS**
• Avoir des formations/contenus de qualité
• Adresse Solana pour recevoir vos paiements
• Respecter les conditions d'utilisation

**🔥 BONUS PARRAINAGE**
• Gagnez 10% sur les ventes de vos filleuls
• Code de parrainage unique fourni

Prêt à commencer ?
        """
        
        keyboard = [
            [InlineKeyboardButton("🚀 Devenir vendeur maintenant", callback_data='create_seller')],
            [InlineKeyboardButton("🏠 Retour menu principal", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            info_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def create_seller_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start seller creation process."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Check if already a seller
        try:
            user = await self.user_service.get_user(user_id)
            if user and user.is_seller:
                await self.already_seller_message(query)
                return
        except Exception as e:
            print(f"Error checking user seller status: {e}")
        
        self.update_user_state(user_id, creating_seller=True, step='seller_name')
        
        await query.edit_message_text(
            "🚀 **CRÉATION COMPTE VENDEUR**\\n\\n"
            "Étape 1/3: Choisissez votre nom de vendeur \\(visible publiquement\\)\\n\\n"
            "💡 Exemple: *Tech Academy*, *Formation Pro*, etc\\.",
            parse_mode='MarkdownV2'
        )
    
    async def handle_seller_creation_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle seller creation input."""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        
        if not state.get('creating_seller'):
            return
        
        step = state.get('step')
        text = update.message.text.strip()
        
        if step == 'seller_name':
            if len(text) < 2 or len(text) > 50:
                await update.message.reply_text(
                    "❌ Le nom de vendeur doit contenir entre 2 et 50 caractères."
                )
                return
            
            self.update_user_state(user_id, seller_name=text, step='seller_bio')
            await update.message.reply_text(
                f"✅ Nom de vendeur: **{self.escape_markdown_text(text)}**\\n\\n"
                "Étape 2/3: Décrivez votre activité en quelques mots\\n\\n"
                "💡 Exemple: *Formations en développement web et mobile*",
                parse_mode='MarkdownV2'
            )
        
        elif step == 'seller_bio':
            if len(text) < 10 or len(text) > 200:
                await update.message.reply_text(
                    "❌ La description doit contenir entre 10 et 200 caractères."
                )
                return
            
            self.update_user_state(user_id, seller_bio=text, step='solana_address')
            await update.message.reply_text(
                f"✅ Description: **{self.escape_markdown_text(text)}**\\n\\n"
                "Étape 3/3: Votre adresse Solana pour recevoir les paiements\\n\\n"
                "💡 Format: Base58, exemple: *9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM*",
                parse_mode='MarkdownV2'
            )
        
        elif step == 'solana_address':
            try:
                # Create seller
                user = await self.user_service.become_seller(
                    user_id=user_id,
                    seller_name=state['seller_name'],
                    seller_bio=state['seller_bio'],
                    solana_address=text
                )
                
                self.clear_user_state(user_id)
                
                success_text = f"""
🎉 **COMPTE VENDEUR CRÉÉ AVEC SUCCÈS !**

**Vos informations:**
• 👤 Nom: {self.escape_markdown_text(user.seller_name)}
• 📝 Description: {self.escape_markdown_text(user.seller_bio)}
• 💰 Adresse Solana: `{user.seller_solana_address}`

**Prochaines étapes:**
1️⃣ Créez vos premiers produits
2️⃣ Configurez vos formations
3️⃣ Commencez à vendre !

**Commission plateforme:** 5% par vente
**Vous gardez:** 95% de vos revenus
                """
                
                keyboard = [
                    [InlineKeyboardButton("📝 Créer mon premier produit", callback_data='seller_add_product')],
                    [InlineKeyboardButton("📊 Accéder au dashboard vendeur", callback_data='seller_dashboard')],
                    [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
                ]
                
                await update.message.reply_text(
                    success_text,
                    parse_mode='MarkdownV2',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            except ValidationError as e:
                await update.message.reply_text(f"❌ Erreur: {e}")
                if "address" in str(e).lower():
                    await update.message.reply_text(
                        "💡 Vérifiez le format de votre adresse Solana. "
                        "Elle doit être une adresse valide en Base58."
                    )
            except Exception as e:
                print(f"Error creating seller: {e}")
                await update.message.reply_text(
                    "❌ Erreur lors de la création du compte vendeur. "
                    "Veuillez réessayer plus tard."
                )
    
    async def already_seller_message(self, query) -> None:
        """Show message when user is already a seller."""
        keyboard = [
            [InlineKeyboardButton("📊 Dashboard vendeur", callback_data='seller_dashboard')],
            [InlineKeyboardButton("⚙️ Modifier mes infos", callback_data='seller_edit_info')],
            [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            "✅ **Vous êtes déjà vendeur !**\\n\\n"
            "Accédez à votre dashboard pour gérer vos produits et voir vos statistiques\\.",
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def seller_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show seller dashboard."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        try:
            user = await self.user_service.get_user(user_id)
            if not user or not user.is_seller:
                await query.edit_message_text(
                    "❌ Vous devez être vendeur pour accéder au dashboard."
                )
                return
            
            dashboard_text = f"""
📊 **DASHBOARD VENDEUR**

**👤 Profil:**
• Nom: {self.escape_markdown_text(user.seller_name)}
• Note: {user.seller_rating}/5 ⭐
• Ventes totales: {user.seller_sales_count}

**💰 Revenus:**
• Commission parrainage: {user.referral_earnings_eur} EUR

**📋 Actions rapides:**
            """
            
            keyboard = [
                [InlineKeyboardButton("📝 Mes produits", callback_data='seller_my_products')],
                [InlineKeyboardButton("➕ Ajouter produit", callback_data='seller_add_product')],
                [InlineKeyboardButton("💰 Mes commandes", callback_data='seller_orders')],
                [InlineKeyboardButton("🏦 Wallet & Payouts", callback_data='seller_wallet')],
                [InlineKeyboardButton("⚙️ Paramètres", callback_data='seller_settings')],
                [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
            ]
            
            await query.edit_message_text(
                dashboard_text,
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"Error showing seller dashboard: {e}")
            await query.edit_message_text(
                "❌ Erreur lors du chargement du dashboard."
            )
    
    async def seller_logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Logout seller."""
        query = update.callback_query
        await query.answer("Déconnecté avec succès.")
        
        user_id = query.from_user.id
        self.set_seller_logged_in(user_id, False)
        
        await query.edit_message_text(
            "✅ **Déconnexion réussie**\\n\\n"
            "Vous avez été déconnecté de votre compte vendeur\\.",
            parse_mode='MarkdownV2'
        )