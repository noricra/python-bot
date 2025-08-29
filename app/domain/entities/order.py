"""
Order domain entity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum

from app.core.exceptions import ValidationError


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(Enum):
    """Payment method enumeration."""
    CRYPTO = "crypto"
    WALLET = "wallet"


@dataclass
class Order:
    """Order entity representing a marketplace transaction."""
    
    order_id: str
    buyer_user_id: int
    seller_user_id: int
    product_id: str
    amount_eur: Decimal
    payment_method: PaymentMethod
    status: OrderStatus = OrderStatus.PENDING
    nowpayments_payment_id: Optional[str] = None
    crypto_currency: Optional[str] = None
    crypto_amount: Optional[Decimal] = None
    payment_address: Optional[str] = None
    platform_commission_eur: Optional[Decimal] = None
    seller_payout_eur: Optional[Decimal] = None
    referrer_commission_eur: Optional[Decimal] = None
    referrer_user_id: Optional[int] = None
    download_count: int = 0
    creation_date: Optional[datetime] = None
    payment_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate order data after initialization."""
        if self.amount_eur <= 0:
            raise ValidationError("Order amount must be positive")
        
        if self.download_count < 0:
            raise ValidationError("Download count cannot be negative")
        
        if self.platform_commission_eur and self.platform_commission_eur < 0:
            raise ValidationError("Platform commission cannot be negative")
        
        if self.seller_payout_eur and self.seller_payout_eur < 0:
            raise ValidationError("Seller payout cannot be negative")
    
    @property
    def is_paid(self) -> bool:
        """Check if order is paid."""
        return self.status in [OrderStatus.PAID, OrderStatus.COMPLETED]
    
    @property
    def is_completed(self) -> bool:
        """Check if order is completed."""
        return self.status == OrderStatus.COMPLETED
    
    @property
    def can_download(self) -> bool:
        """Check if buyer can download the product."""
        return self.is_paid
    
    def mark_as_paid(self, payment_date: datetime = None) -> None:
        """Mark order as paid."""
        if self.status != OrderStatus.PENDING:
            raise ValidationError(f"Cannot mark order as paid from status: {self.status.value}")
        
        self.status = OrderStatus.PAID
        self.payment_date = payment_date or datetime.utcnow()
    
    def mark_as_completed(self, completion_date: datetime = None) -> None:
        """Mark order as completed."""
        if not self.is_paid:
            raise ValidationError("Order must be paid before completion")
        
        self.status = OrderStatus.COMPLETED
        self.completion_date = completion_date or datetime.utcnow()
    
    def cancel(self) -> None:
        """Cancel the order."""
        if self.is_paid:
            raise ValidationError("Cannot cancel a paid order")
        
        self.status = OrderStatus.CANCELLED
    
    def refund(self) -> None:
        """Mark order as refunded."""
        if not self.is_paid:
            raise ValidationError("Cannot refund an unpaid order")
        
        self.status = OrderStatus.REFUNDED
    
    def record_download(self) -> None:
        """Record a download."""
        if not self.can_download:
            raise ValidationError("Order must be paid to download")
        
        self.download_count += 1
    
    def calculate_commissions(self, platform_rate: Decimal, 
                            referrer_rate: Decimal = None) -> None:
        """Calculate and set commission amounts."""
        self.platform_commission_eur = self.amount_eur * platform_rate
        
        if referrer_rate and self.referrer_user_id:
            self.referrer_commission_eur = self.amount_eur * referrer_rate
            self.seller_payout_eur = (self.amount_eur - 
                                    self.platform_commission_eur - 
                                    self.referrer_commission_eur)
        else:
            self.referrer_commission_eur = Decimal("0")
            self.seller_payout_eur = self.amount_eur - self.platform_commission_eur