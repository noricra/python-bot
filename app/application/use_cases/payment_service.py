"""
Payment service containing payment-related business logic.
"""

from typing import Optional, Dict, Any
from decimal import Decimal

from app.domain.entities import Order, Payout
from app.domain.entities.order import PaymentMethod
from app.domain.entities.payout import PayoutStatus
from app.application.interfaces import (
    OrderRepositoryInterface,
    PayoutRepositoryInterface,
    UserRepositoryInterface
)
from app.application.use_cases.wallet_service import WalletService
from app.application.use_cases.order_service import OrderService
from app.core.exceptions import ValidationError, NotFoundError, PaymentError
from app.core import settings


class PaymentService:
    """Service for payment operations."""
    
    def __init__(self, order_repository: OrderRepositoryInterface,
                 payout_repository: PayoutRepositoryInterface,
                 user_repository: UserRepositoryInterface,
                 wallet_service: WalletService,
                 order_service: OrderService):
        self.order_repository = order_repository
        self.payout_repository = payout_repository
        self.user_repository = user_repository
        self.wallet_service = wallet_service
        self.order_service = order_service
    
    async def process_wallet_payment(self, order_id: str) -> Order:
        """Process payment from user wallet."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        if order.payment_method != PaymentMethod.WALLET:
            raise ValidationError("Order is not configured for wallet payment")
        
        # Check wallet balance
        has_funds = await self.wallet_service.has_sufficient_funds(
            order.buyer_user_id, order.amount_eur
        )
        if not has_funds:
            raise PaymentError("Insufficient wallet balance")
        
        # Process payment from wallet
        await self.wallet_service.process_order_payment_from_wallet(
            order.buyer_user_id, order.amount_eur, order_id
        )
        
        # Mark order as paid
        order = await self.order_service.mark_order_as_paid(order_id)
        
        # Process payouts
        await self._process_order_payouts(order)
        
        return order
    
    async def process_crypto_payment_webhook(self, payment_data: Dict[str, Any]) -> Optional[Order]:
        """Process NOWPayments webhook for crypto payment."""
        payment_id = payment_data.get("payment_id")
        payment_status = payment_data.get("payment_status")
        
        if not payment_id:
            raise ValidationError("Payment ID missing from webhook data")
        
        order = await self.order_repository.get_by_payment_id(payment_id)
        if not order:
            raise NotFoundError(f"Order not found for payment ID {payment_id}")
        
        if payment_status == "finished":
            # Mark order as paid
            order = await self.order_service.mark_order_as_paid(
                order.order_id,
                nowpayments_payment_id=payment_id,
                crypto_currency=payment_data.get("pay_currency"),
                crypto_amount=Decimal(str(payment_data.get("pay_amount", 0))),
                payment_address=payment_data.get("pay_address")
            )
            
            # Process payouts
            await self._process_order_payouts(order)
            
            return order
        
        elif payment_status in ["failed", "expired"]:
            # Cancel order
            await self.order_service.cancel_order(order.order_id, order.buyer_user_id)
        
        return order
    
    async def _process_order_payouts(self, order: Order) -> None:
        """Process payouts for a completed order."""
        if not order.is_paid:
            raise ValidationError("Order must be paid before processing payouts")
        
        # Seller payout
        if order.seller_payout_eur and order.seller_payout_eur > 0:
            await self.wallet_service.process_seller_payout_to_wallet(
                order.seller_user_id, order.seller_payout_eur, order.order_id
            )
        
        # Referrer commission
        if (order.referrer_user_id and 
            order.referrer_commission_eur and 
            order.referrer_commission_eur > 0):
            await self.wallet_service.process_referrer_commission(
                order.referrer_user_id, order.referrer_commission_eur, order.order_id
            )
    
    async def create_payout_request(self, seller_id: int, amount_eur: Decimal,
                                  solana_address: str) -> Payout:
        """Create a payout request for seller."""
        # Verify seller
        seller = await self.user_repository.get_by_id(seller_id)
        if not seller:
            raise NotFoundError(f"Seller {seller_id} not found")
        
        if not seller.is_seller:
            raise ValidationError("User is not a seller")
        
        # Check minimum payout amount
        min_payout = Decimal(str(settings.MARKETPLACE_CONFIG.get("min_payout_amount", "0.1")))
        if amount_eur < min_payout:
            raise ValidationError(f"Minimum payout amount is {min_payout} EUR")
        
        # Check wallet balance
        wallet_balance = await self.wallet_service.get_wallet_balance(seller_id)
        if wallet_balance < amount_eur:
            raise PaymentError(f"Insufficient wallet balance. Available: {wallet_balance} EUR")
        
        # Generate payout ID
        import uuid
        payout_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
        
        payout = Payout(
            payout_id=payout_id,
            seller_user_id=seller_id,
            amount_eur=amount_eur,
            solana_address=solana_address
        )
        
        success = await self.payout_repository.create(payout)
        if not success:
            raise ValidationError("Failed to create payout request")
        
        # Withdraw from wallet (reserve funds)
        await self.wallet_service.withdraw(
            seller_id, amount_eur, f"Payout request {payout_id}", payout_id
        )
        
        return payout
    
    async def process_payout(self, payout_id: str) -> Payout:
        """Process a payout request (admin operation)."""
        payout = await self.payout_repository.get_by_id(payout_id)
        if not payout:
            raise NotFoundError(f"Payout {payout_id} not found")
        
        if not payout.is_pending:
            raise ValidationError(f"Payout {payout_id} is not pending")
        
        payout.start_processing()
        
        success = await self.payout_repository.update(payout)
        if not success:
            raise ValidationError("Failed to update payout status")
        
        # TODO: Integrate with actual crypto payout system
        # For now, simulate successful payout
        import secrets
        transaction_hash = f"tx_{secrets.token_hex(32)}"
        
        payout.complete(transaction_hash)
        
        success = await self.payout_repository.update(payout)
        if not success:
            raise ValidationError("Failed to complete payout")
        
        return payout
    
    async def cancel_payout(self, payout_id: str, seller_id: int) -> Payout:
        """Cancel a payout request."""
        payout = await self.payout_repository.get_by_id(payout_id)
        if not payout:
            raise NotFoundError(f"Payout {payout_id} not found")
        
        if payout.seller_user_id != seller_id:
            raise ValidationError("You can only cancel your own payouts")
        
        if not payout.can_be_cancelled:
            raise ValidationError(f"Payout {payout_id} cannot be cancelled")
        
        payout.cancel()
        
        success = await self.payout_repository.update(payout)
        if not success:
            raise ValidationError("Failed to cancel payout")
        
        # Refund to wallet
        await self.wallet_service.deposit(
            seller_id, payout.amount_eur, f"Payout cancellation refund {payout_id}", payout_id
        )
        
        return payout
    
    async def get_seller_payouts(self, seller_id: int) -> list[Payout]:
        """Get all payouts for a seller."""
        return await self.payout_repository.get_by_seller(seller_id)
    
    async def get_pending_payouts(self) -> list[Payout]:
        """Get all pending payouts (admin operation)."""
        return await self.payout_repository.get_pending_payouts()
    
    async def calculate_seller_available_balance(self, seller_id: int) -> Decimal:
        """Calculate available balance for seller (excluding pending payouts)."""
        wallet_balance = await self.wallet_service.get_wallet_balance(seller_id)
        
        # Subtract pending payout amounts
        payouts = await self.payout_repository.get_by_seller(seller_id)
        pending_amount = sum(
            p.amount_eur for p in payouts 
            if p.status in [PayoutStatus.PENDING, PayoutStatus.PROCESSING]
        )
        
        return wallet_balance - pending_amount