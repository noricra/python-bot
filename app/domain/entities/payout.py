"""
Payout domain entity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum

from app.core.exceptions import ValidationError
from app.core.utils import validate_solana_address


class PayoutStatus(Enum):
    """Payout status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Payout:
    """Payout entity representing seller withdrawals."""
    
    payout_id: str
    seller_user_id: int
    amount_eur: Decimal
    solana_address: str
    status: PayoutStatus = PayoutStatus.PENDING
    transaction_hash: Optional[str] = None
    failure_reason: Optional[str] = None
    request_date: Optional[datetime] = None
    processing_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate payout data."""
        if self.amount_eur <= 0:
            raise ValidationError("Payout amount must be positive")
        
        if not validate_solana_address(self.solana_address):
            raise ValidationError(f"Invalid Solana address: {self.solana_address}")
    
    @property
    def is_pending(self) -> bool:
        """Check if payout is pending."""
        return self.status == PayoutStatus.PENDING
    
    @property
    def is_processing(self) -> bool:
        """Check if payout is being processed."""
        return self.status == PayoutStatus.PROCESSING
    
    @property
    def is_completed(self) -> bool:
        """Check if payout is completed."""
        return self.status == PayoutStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if payout failed."""
        return self.status == PayoutStatus.FAILED
    
    @property
    def can_be_cancelled(self) -> bool:
        """Check if payout can be cancelled."""
        return self.status in [PayoutStatus.PENDING, PayoutStatus.FAILED]
    
    def start_processing(self, processing_date: datetime = None) -> None:
        """Mark payout as processing."""
        if self.status != PayoutStatus.PENDING:
            raise ValidationError(f"Cannot process payout with status: {self.status.value}")
        
        self.status = PayoutStatus.PROCESSING
        self.processing_date = processing_date or datetime.utcnow()
        self.failure_reason = None
    
    def complete(self, transaction_hash: str, completion_date: datetime = None) -> None:
        """Mark payout as completed."""
        if self.status != PayoutStatus.PROCESSING:
            raise ValidationError(f"Cannot complete payout with status: {self.status.value}")
        
        if not transaction_hash.strip():
            raise ValidationError("Transaction hash is required for completion")
        
        self.status = PayoutStatus.COMPLETED
        self.transaction_hash = transaction_hash
        self.completion_date = completion_date or datetime.utcnow()
        self.failure_reason = None
    
    def fail(self, reason: str) -> None:
        """Mark payout as failed."""
        if self.status not in [PayoutStatus.PENDING, PayoutStatus.PROCESSING]:
            raise ValidationError(f"Cannot fail payout with status: {self.status.value}")
        
        if not reason.strip():
            raise ValidationError("Failure reason is required")
        
        self.status = PayoutStatus.FAILED
        self.failure_reason = reason
        self.transaction_hash = None
    
    def cancel(self) -> None:
        """Cancel the payout."""
        if not self.can_be_cancelled:
            raise ValidationError(f"Cannot cancel payout with status: {self.status.value}")
        
        self.status = PayoutStatus.CANCELLED
        self.failure_reason = "Cancelled by user"
        self.transaction_hash = None