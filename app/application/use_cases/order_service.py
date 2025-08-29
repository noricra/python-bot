"""
Order service containing order-related business logic.
"""

import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.entities import Order, Product, User
from app.domain.entities.order import OrderStatus, PaymentMethod
from app.application.interfaces import (
    OrderRepositoryInterface, 
    ProductRepositoryInterface,
    UserRepositoryInterface
)
from app.core.exceptions import ValidationError, NotFoundError
from app.core import settings


class OrderService:
    """Service for order operations."""
    
    def __init__(self, order_repository: OrderRepositoryInterface,
                 product_repository: ProductRepositoryInterface,
                 user_repository: UserRepositoryInterface):
        self.order_repository = order_repository
        self.product_repository = product_repository
        self.user_repository = user_repository
    
    async def create_order(self, buyer_id: int, product_id: str, 
                         payment_method: PaymentMethod,
                         referrer_code: str = None) -> Order:
        """Create a new order."""
        # Verify product exists and is available
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        
        if not product.is_available:
            raise ValidationError(f"Product {product_id} is not available for purchase")
        
        # Verify buyer exists
        buyer = await self.user_repository.get_by_id(buyer_id)
        if not buyer:
            raise NotFoundError(f"Buyer {buyer_id} not found")
        
        # Check for self-purchase
        if buyer_id == product.seller_user_id:
            raise ValidationError("Cannot purchase your own product")
        
        # Handle referrer
        referrer_user_id = None
        if referrer_code:
            referrer = await self.user_repository.get_by_partner_code(referrer_code)
            if referrer and referrer.user_id != buyer_id:
                referrer_user_id = referrer.user_id
        
        # Generate unique order ID
        order_id = f"ORD_{uuid.uuid4().hex[:12].upper()}"
        
        order = Order(
            order_id=order_id,
            buyer_user_id=buyer_id,
            seller_user_id=product.seller_user_id,
            product_id=product_id,
            amount_eur=product.price_eur,
            payment_method=payment_method,
            referrer_user_id=referrer_user_id,
            creation_date=datetime.utcnow()
        )
        
        # Calculate commissions
        platform_rate = Decimal(str(settings.PLATFORM_COMMISSION_RATE))
        referrer_rate = Decimal(str(settings.PARTNER_COMMISSION_RATE)) if referrer_user_id else None
        
        order.calculate_commissions(platform_rate, referrer_rate)
        
        success = await self.order_repository.create(order)
        if not success:
            raise ValidationError("Failed to create order")
        
        return order
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return await self.order_repository.get_by_id(order_id)
    
    async def get_order_by_payment_id(self, payment_id: str) -> Optional[Order]:
        """Get order by NOWPayments payment ID."""
        return await self.order_repository.get_by_payment_id(payment_id)
    
    async def mark_order_as_paid(self, order_id: str, 
                               nowpayments_payment_id: str = None,
                               crypto_currency: str = None,
                               crypto_amount: Decimal = None,
                               payment_address: str = None) -> Order:
        """Mark order as paid."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.PENDING:
            raise ValidationError(f"Order {order_id} is not pending payment")
        
        order.mark_as_paid()
        
        # Update payment details
        if nowpayments_payment_id:
            order.nowpayments_payment_id = nowpayments_payment_id
        if crypto_currency:
            order.crypto_currency = crypto_currency
        if crypto_amount:
            order.crypto_amount = crypto_amount
        if payment_address:
            order.payment_address = payment_address
        
        success = await self.order_repository.update(order)
        if not success:
            raise ValidationError("Failed to update order payment status")
        
        # Record sale in product
        await self.record_product_sale(order.product_id)
        
        return order
    
    async def complete_order(self, order_id: str) -> Order:
        """Mark order as completed."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        order.mark_as_completed()
        
        success = await self.order_repository.update(order)
        if not success:
            raise ValidationError("Failed to complete order")
        
        return order
    
    async def cancel_order(self, order_id: str, user_id: int) -> Order:
        """Cancel an order."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        # Only buyer can cancel their own order
        if order.buyer_user_id != user_id:
            raise ValidationError("You can only cancel your own orders")
        
        order.cancel()
        
        success = await self.order_repository.update(order)
        if not success:
            raise ValidationError("Failed to cancel order")
        
        return order
    
    async def record_download(self, order_id: str, buyer_id: int) -> Order:
        """Record a download for an order."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")
        
        if order.buyer_user_id != buyer_id:
            raise ValidationError("You can only download your own purchases")
        
        order.record_download()
        
        success = await self.order_repository.update(order)
        if not success:
            raise ValidationError("Failed to record download")
        
        return order
    
    async def get_buyer_orders(self, buyer_id: int) -> List[Order]:
        """Get all orders for a buyer."""
        return await self.order_repository.get_by_buyer(buyer_id)
    
    async def get_seller_orders(self, seller_id: int) -> List[Order]:
        """Get all orders for a seller."""
        return await self.order_repository.get_by_seller(seller_id)
    
    async def get_completed_orders_for_seller(self, seller_id: int) -> List[Order]:
        """Get completed orders for seller (for payout calculation)."""
        return await self.order_repository.get_completed_orders_for_seller(seller_id)
    
    async def record_product_sale(self, product_id: str) -> None:
        """Record a sale for a product."""
        product = await self.product_repository.get_by_id(product_id)
        if product:
            product.record_sale()
            await self.product_repository.update(product)
    
    async def check_order_ownership(self, order_id: str, user_id: int) -> bool:
        """Check if user owns the order (as buyer)."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            return False
        
        return order.buyer_user_id == user_id
    
    async def can_download_order(self, order_id: str, buyer_id: int) -> bool:
        """Check if buyer can download the order."""
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            return False
        
        return (order.buyer_user_id == buyer_id and 
                order.can_download)
    
    async def get_order_statistics(self, seller_id: int) -> dict:
        """Get order statistics for a seller."""
        orders = await self.get_seller_orders(seller_id)
        
        total_orders = len(orders)
        completed_orders = len([o for o in orders if o.is_completed])
        pending_orders = len([o for o in orders if o.status == OrderStatus.PENDING])
        total_revenue = sum(o.seller_payout_eur or Decimal("0") for o in orders if o.is_paid)
        
        return {
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "total_revenue_eur": total_revenue,
            "conversion_rate": (completed_orders / total_orders * 100) if total_orders > 0 else 0
        }