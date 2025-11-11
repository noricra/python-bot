"""
Seller Payout Service
Handles 24-hour escrow logic and payout processing
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from app.domain.repositories.payout_repo import PayoutRepository
from app.domain.repositories.order_repo import OrderRepository
from app.domain.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class SellerPayoutService:
    """Service for managing seller payouts with 24h escrow"""

    def __init__(self):
        self.payout_repo = PayoutRepository()
        self.order_repo = OrderRepository()
        self.user_repo = UserRepository()

    async def create_payout_from_order_async(self, order_id: str) -> Optional[int]:
        """Async version that sends notification"""
        payout_id = self.create_payout_from_order(order_id)

        if payout_id:
            # Get order and seller info for notification
            try:
                order = self.order_repo.get_order_by_id(order_id)
                if order:
                    seller_user_id = order['seller_user_id']
                    seller = self.user_repo.get_user_by_id(seller_user_id)
                    if seller:
                        seller_revenue_usd = order.get('seller_revenue_usd', 0)
                        payment_currency = order.get('payment_currency', 'USDT')
                        seller_wallet_address = seller.get('seller_solana_address', '')

                        await self._notify_seller_payout_created(
                            seller_user_id=seller_user_id,
                            payout_id=payout_id,
                            amount=seller_revenue_usd,
                            currency=payment_currency,
                            wallet_address=seller_wallet_address
                        )
            except Exception as e:
                logger.error(f"Failed to send payout notification: {e}")

        return payout_id

    def create_payout_from_order(self, order_id: str) -> Optional[int]:
        """
        Create a payout entry from a completed order

        Args:
            order_id: Order ID

        Returns:
            Payout ID if created, None if failed
        """
        try:
            # Get order details
            order = self.order_repo.get_order_by_id(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return None

            if order['payment_status'] != 'completed':
                logger.warning(f"Order {order_id} not completed, cannot create payout")
                return None

            # Get seller info for wallet address
            seller_user_id = order['seller_user_id']
            seller = self.user_repo.get_user_by_id(seller_user_id)

            if not seller:
                logger.error(f"Seller {seller_user_id} not found")
                return None

            seller_wallet_address = seller.get('seller_solana_address')
            if not seller_wallet_address:
                logger.error(f"Seller {seller_user_id} has no wallet address configured")
                return None

            # Use seller_revenue_usd as payout amount (in USDT)
            seller_revenue_usd = order.get('seller_revenue_usd', 0)
            payment_currency = order.get('payment_currency', 'USDT').upper()

            # Create payout entry
            payout_id = self.payout_repo.insert_payout(
                seller_user_id=seller_user_id,
                order_ids=[order_id],
                total_amount_usdt=seller_revenue_usd,
                seller_wallet_address=seller_wallet_address,
                payment_currency=payment_currency
            )

            if payout_id:
                logger.info(f"✅ Payout {payout_id} created for order {order_id} - ${seller_revenue_usd:.2f} USDT to {seller_wallet_address[:8]}...")
            else:
                logger.error(f"Failed to create payout for order {order_id}")

            return payout_id

        except Exception as e:
            logger.error(f"Error creating payout from order {order_id}: {e}")
            return None

    async def _notify_seller_payout_created(self, seller_user_id: int, payout_id: int,
                                            amount: float, currency: str, wallet_address: str):
        """Send Telegram notification to seller when payout is created"""
        try:
            from telegram import Bot
            import os

            bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
            if not bot_token:
                logger.warning("No bot token available for seller notification")
                return

            bot = Bot(token=bot_token)

            wallet_short = f"{wallet_address[:6]}...{wallet_address[-4:]}" if len(wallet_address) > 10 else wallet_address

            message = f"""
💰 **NOUVEAU PAYOUT CRÉÉ**

✅ Votre payout a été créé avec succès !

📊 **Détails:**
• Montant: ${amount:.2f} {currency}
• Wallet: `{wallet_short}`
• Payout ID: #{payout_id}

⏳ **Status:** En attente de traitement

📌 Ce payout sera traité et payé après vérification par notre équipe. Vous recevrez une notification une fois le paiement effectué.
"""

            await bot.send_message(chat_id=seller_user_id, text=message, parse_mode='Markdown')
            logger.info(f"✅ Payout notification sent to seller {seller_user_id}")

        except Exception as e:
            logger.error(f"Error sending payout notification: {e}")
            raise

    def get_pending_payouts_for_seller(self, seller_user_id: int) -> List[Dict]:
        """
        Get pending payouts for a seller

        Args:
            seller_user_id: Seller user ID

        Returns:
            List of pending payouts with details
        """
        try:
            payouts = self.payout_repo.list_recent_for_seller(seller_user_id, limit=50)

            # Filter only pending and add time remaining
            pending_payouts = []
            for payout in payouts:
                if payout['payout_status'] == 'pending':
                    # Calculate time remaining (24h from creation)
                    created_at = payout['created_at']
                    release_time = created_at + timedelta(hours=24)
                    time_remaining = release_time - datetime.now()

                    payout_dict = dict(payout)
                    payout_dict['release_time'] = release_time
                    payout_dict['hours_remaining'] = max(0, time_remaining.total_seconds() / 3600)
                    payout_dict['can_release'] = time_remaining.total_seconds() <= 0
                    # Fix: use total_amount_usdt instead of total_amount_sol
                    payout_dict['total_amount_usdt'] = payout.get('total_amount_usdt', 0)

                    pending_payouts.append(payout_dict)

            return pending_payouts

        except Exception as e:
            logger.error(f"Error getting pending payouts for seller {seller_user_id}: {e}")
            return []

    def get_all_pending_payouts_admin(self) -> List[Dict]:
        """
        Get all pending payouts for admin dashboard

        Returns:
            List of all pending payouts with seller info
        """
        try:
            payouts = self.payout_repo.get_pending_payouts(limit=100)

            # Enrich with seller info
            enriched = []
            for payout in payouts:
                seller_user_id = payout.get('user_id')
                if seller_user_id:
                    seller = self.user_repo.get_user_by_id(seller_user_id)
                    payout_dict = dict(payout)
                    payout_dict['seller_name'] = seller.get('seller_name', 'Unknown') if seller else 'Unknown'
                    payout_dict['seller_username'] = seller.get('username', '') if seller else ''
                    enriched.append(payout_dict)

            return enriched

        except Exception as e:
            logger.error(f"Error getting pending payouts for admin: {e}")
            return []

    def mark_payout_as_completed(self, payout_id: int, admin_user_id: int) -> bool:
        """
        Mark a payout as completed (manual approval)

        Args:
            payout_id: Payout ID
            admin_user_id: Admin who approved

        Returns:
            True if successful
        """
        try:
            logger.info(f"Admin {admin_user_id} marking payout {payout_id} as completed")

            # Mark specific payout as completed
            success = self.payout_repo.mark_payout_completed(payout_id)

            if success:
                logger.info(f"Payout {payout_id} marked as completed by admin {admin_user_id}")
            else:
                logger.error(f"Failed to mark payout {payout_id} as completed")

            return success

        except Exception as e:
            logger.error(f"Error marking payout {payout_id} as completed: {e}")
            return False

    def process_automatic_payouts(self) -> int:
        """
        Process all payouts that are older than 24h (for cron job)

        Returns:
            Number of payouts processed
        """
        try:
            # Get all pending payouts
            pending = self.get_all_pending_payouts_admin()

            processed_count = 0
            for payout in pending:
                # Check if 24h have passed
                created_at = payout.get('created_at')
                if created_at:
                    hours_elapsed = (datetime.now() - created_at).total_seconds() / 3600

                    if hours_elapsed >= 24:
                        # Auto-release
                        payout_id = payout.get('id')
                        success = self.mark_payout_as_completed(payout_id, admin_user_id=0)  # 0 = automatic

                        if success:
                            processed_count += 1
                            logger.info(f"Auto-released payout {payout_id} after 24h")

            if processed_count > 0:
                logger.info(f"Auto-processed {processed_count} payouts")

            return processed_count

        except Exception as e:
            logger.error(f"Error processing automatic payouts: {e}")
            return 0

    def get_total_pending_amount(self, seller_user_id: int) -> float:
        """
        Get total pending payout amount for a seller

        Args:
            seller_user_id: Seller user ID

        Returns:
            Total pending amount in USDT
        """
        try:
            pending_payouts = self.get_pending_payouts_for_seller(seller_user_id)
            total = sum(p.get('total_amount_usdt', 0) for p in pending_payouts)
            return total

        except Exception as e:
            logger.error(f"Error calculating total pending amount: {e}")
            return 0.0
