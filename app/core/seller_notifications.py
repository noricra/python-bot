"""
Seller Notifications System - Real-time alerts for important events
Notifie les vendeurs à chaque événement important
"""

import logging
import psycopg2.extras
from datetime import datetime
from typing import Optional, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


class SellerNotifications:
    """Système de notifications en temps réel pour les vendeurs"""

    @staticmethod
    async def notify_new_purchase(bot, seller_id: int, product_data: Dict, buyer_name: str, amount_usd: float, crypto_code: str):
        """
        Notification immédiate : Nouvel achat confirmé

        Args:
            bot: Bot instance
            seller_id: Seller user ID
            product_data: Product information
            buyer_name: Buyer's name/username
            amount_usd: Purchase amount in USD
            crypto_code: Cryptocurrency used
        """
        try:
            # seller_id is already the telegram user_id
            telegram_id = seller_id
            product_title = product_data.get('title', 'Produit')
            product_id = product_data.get('product_id', 'N/A')

            # Message de notification enrichi
            notification_text = f"""
🎉 **NOUVELLE VENTE !**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 **Produit:** {product_title}
 **ID:** `{product_id}`

 **Montant:** {amount_usd:.2f} $
 **Crypto:** {crypto_code}

 **Acheteur:** {buyer_name}
 **Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Le paiement est en cours de vérification**
Vous serez notifié dès confirmation blockchain.
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(" Voir Analytics", callback_data='analytics_dashboard')],
                [InlineKeyboardButton(" Mes Ventes", callback_data='my_sales')],
                [InlineKeyboardButton(" Dashboard", callback_data='seller_dashboard')]
            ])

            # Envoyer notification
            await bot.application.bot.send_message(
                chat_id=telegram_id,
                text=notification_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"✅ Purchase notification sent to seller {seller_id} (telegram: {telegram_id})")

        except Exception as e:
            logger.error(f"❌ Error sending purchase notification: {e}")

    @staticmethod
    async def notify_payment_confirmed(bot, seller_id: int, product_data: Dict, buyer_name: str, amount_usd: float, crypto_code: str, tx_hash: Optional[str] = None):
        """
        Notification : Paiement confirmé sur la blockchain

        Args:
            bot: Bot instance
            seller_id: Seller user ID
            product_data: Product information
            buyer_name: Buyer's name
            amount_usd: Final amount in USD
            crypto_code: Cryptocurrency used
            tx_hash: Blockchain transaction hash (optional)
        """
        try:
            # seller_id is already the telegram user_id
            telegram_id = seller_id
            product_title = product_data.get('title', 'Produit')

            # Calculate amounts
            # amount_usd = Prix du produit (ex: $2.00)
            # Client paie = Prix × 1.0278 (ex: $2.00 × 1.0278 = $2.0556)
            # Vendeur reçoit = Prix (ex: $2.00 = 100% du prix affiché)
            # Plateforme reçoit = Total payé - Prix vendeur (ex: $2.0556 - $2.00 = $0.0556)
            from app.core import settings as core_settings
            commission_percent = core_settings.PLATFORM_COMMISSION_PERCENT
            seller_revenue = amount_usd  # Vendeur reçoit 100% du prix affiché
            total_paid_by_buyer = amount_usd * (1 + commission_percent / 100)  # Total payé par l'acheteur
            buyer_fees = total_paid_by_buyer - seller_revenue  # Frais payés par l'acheteur

            notification_text = f"""
**PAIEMENT CONFIRMÉ**
━━━━━━━━━━━━━━━━━━

**Produit:** {product_title}
**Acheteur:** {buyer_name}

**Prix du produit:** {seller_revenue:.2f} $
**Frais acheteur:** {buyer_fees:.2f} $
**Total payé:** {total_paid_by_buyer:.2f} $

**Votre revenu:** {seller_revenue:.2f} $
**Crypto:** {crypto_code}
"""

            if tx_hash:
                notification_text += f"**TX Hash:** `{tx_hash[:16]}...`\n"

            notification_text += f"""
**Confirmé le:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}
━━━━━━━━━━━━━━━━━━

**Le produit a été automatiquement livré à l'acheteur.**
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Voir Mes Revenus", callback_data='my_revenue')],
                [InlineKeyboardButton("Analytics", callback_data='analytics_dashboard')]
            ])

            await bot.application.bot.send_message(
                chat_id=telegram_id,
                text=notification_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"✅ Payment confirmation notification sent to seller {seller_id}")

        except Exception as e:
            logger.error(f"❌ Error sending payment confirmation: {e}")

    @staticmethod
    async def notify_new_review(bot, seller_id: int, product_data: Dict, reviewer_name: str, rating: int, review_text: str):
        """
        Notification : Nouvel avis laissé sur un produit

        Args:
            bot: Bot instance
            seller_id: Seller user ID
            product_data: Product information
            reviewer_name: Reviewer's name
            rating: Star rating (1-5)
            review_text: Review text content
        """
        try:
            # seller_id is already the telegram user_id
            telegram_id = seller_id
            product_title = product_data.get('title', 'Produit')

            # Star rating visual
            stars = '⭐' * rating + '☆' * (5 - rating)

            # Truncate review if too long
            review_snippet = (review_text[:150] + '…') if len(review_text) > 150 else review_text

            notification_text = f"""
💬 **NOUVEL AVIS !**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 **Produit:** {product_title}

{stars} **{rating}/5**

 **{reviewer_name}** a écrit :
_{review_snippet}_

 **{datetime.now().strftime('%d/%m/%Y à %H:%M')}**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👀 Voir tous les avis", callback_data=f'product_reviews_{product_data.get("product_id")}')],
                [InlineKeyboardButton("📊 Analytics Produit", callback_data='analytics_products')]
            ])

            await bot.application.bot.send_message(
                chat_id=telegram_id,
                text=notification_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"✅ Review notification sent to seller {seller_id}")

        except Exception as e:
            logger.error(f"❌ Error sending review notification: {e}")

    @staticmethod
    async def notify_daily_summary(bot, seller_id: int, summary_data: Dict):
        """
        Notification quotidienne : Résumé des ventes de la journée

        Args:
            bot: Bot instance
            seller_id: Seller user ID
            summary_data: Dict with:
                - sales_today: Number of sales
                - revenue_today: Total revenue
                - views_today: Product views
                - top_product: Best selling product
        """
        try:
            # seller_id is already the telegram user_id
            telegram_id = seller_id

            sales_today = summary_data.get('sales_today', 0)
            revenue_today = summary_data.get('revenue_today', 0.0)
            views_today = summary_data.get('views_today', 0)
            top_product = summary_data.get('top_product', 'N/A')

            # Emoji based on performance
            emoji = '🎉' if sales_today >= 5 else '📊' if sales_today > 0 else '💤'

            notification_text = f"""
{emoji} **RÉSUMÉ QUOTIDIEN**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 **{datetime.now().strftime('%d %B %Y')}**

 **Revenus:** {revenue_today:.2f} $
 **Ventes:** {sales_today}
 **Vues produits:** {views_today}

 **Produit star:** {top_product}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Conseil du jour:**
"""

            # Personalized tip based on performance
            if sales_today == 0:
                notification_text += "Essayez d'optimiser vos titres et descriptions pour plus de visibilité !"
            elif sales_today < 3:
                notification_text += "Bon début ! Ajoutez des images de qualité pour augmenter les conversions."
            else:
                notification_text += "Excellente journée ! Continuez sur cette lancée 🚀"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Voir Analytics Complet", callback_data='analytics_dashboard')],
                [InlineKeyboardButton("💰 Mes Revenus", callback_data='my_revenue')]
            ])

            await bot.application.bot.send_message(
                chat_id=telegram_id,
                text=notification_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"✅ Daily summary sent to seller {seller_id}")

        except Exception as e:
            logger.error(f"❌ Error sending daily summary: {e}")

    @staticmethod
    async def notify_product_milestone(bot, seller_id: int, product_data: Dict, milestone_type: str, milestone_value: int):
        """
        Notification : Jalon atteint (50 ventes, 100 vues, etc.)

        Args:
            bot: Bot instance
            seller_id: Seller user ID
            product_data: Product information
            milestone_type: 'sales', 'views', 'revenue'
            milestone_value: The milestone number (50, 100, 500, etc.)
        """
        try:
            # seller_id is already the telegram user_id
            telegram_id = seller_id
            product_title = product_data.get('title', 'Produit')

            # Milestone-specific message
            milestone_messages = {
                'sales': {
                    10: ('🎯', 'Vos 10 premières ventes !'),
                    50: ('🎉', '50 ventes atteintes !'),
                    100: ('🏆', '100 ventes — Best-seller !'),
                    500: ('💎', '500 ventes — Succès phénoménal !'),
                },
                'views': {
                    100: ('👀', '100 vues sur votre produit'),
                    500: ('🔥', '500 vues — Produit populaire !'),
                    1000: ('⭐', '1000 vues — Viral !'),
                },
                'revenue': {
                    100: ('💰', '100$ de revenus générés'),
                    500: ('💵', '500$ de revenus !'),
                    1000: ('💸', '1000$ de revenus — Excellent !'),
                }
            }

            emoji, title = milestone_messages.get(milestone_type, {}).get(milestone_value, ('🎊', 'Jalon atteint !'))

            notification_text = f"""
{emoji} **{title.upper()}**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 **{product_title}**

🎊 Félicitations ! Votre produit vient d'atteindre **{milestone_value} {milestone_type}** !

 **Continuez sur cette lancée :**
• Ajoutez des avis clients
• Créez des produits complémentaires
• Optimisez votre description

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Voir Statistiques", callback_data='analytics_products')],
                [InlineKeyboardButton("🚀 Dashboard", callback_data='seller_dashboard')]
            ])

            await bot.application.bot.send_message(
                chat_id=telegram_id,
                text=notification_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"✅ Milestone notification sent to seller {seller_id}")

        except Exception as e:
            logger.error(f"❌ Error sending milestone notification: {e}")

