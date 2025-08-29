"""
Wallet domain entity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum

from app.core.exceptions import ValidationError, InsufficientFundsError


class TransactionType(Enum):
    """Wallet transaction type enumeration."""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    COMMISSION = "commission"
    PAYOUT = "payout"
    REFUND = "refund"


@dataclass
class WalletTransaction:
    """Wallet transaction entity."""
    
    transaction_id: str
    user_id: int
    transaction_type: TransactionType
    amount_eur: Decimal
    description: str
    reference_order_id: Optional[str] = None
    creation_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate transaction data."""
        if self.amount_eur == 0:
            raise ValidationError("Transaction amount cannot be zero")
        
        if not self.description.strip():
            raise ValidationError("Transaction description cannot be empty")


@dataclass
class Wallet:
    """Wallet entity representing user's balance."""
    
    user_id: int
    balance_eur: Decimal = Decimal("0.0")
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate wallet data."""
        if self.balance_eur < 0:
            raise ValidationError("Wallet balance cannot be negative")
    
    def deposit(self, amount: Decimal, description: str, 
               reference_order_id: str = None) -> WalletTransaction:
        """Deposit money to wallet."""
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive")
        
        self.balance_eur += amount
        self.last_updated = datetime.utcnow()
        
        return WalletTransaction(
            transaction_id=self._generate_transaction_id(),
            user_id=self.user_id,
            transaction_type=TransactionType.DEPOSIT,
            amount_eur=amount,
            description=description,
            reference_order_id=reference_order_id,
            creation_date=self.last_updated
        )
    
    def withdraw(self, amount: Decimal, description: str,
                reference_order_id: str = None) -> WalletTransaction:
        """Withdraw money from wallet."""
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be positive")
        
        if self.balance_eur < amount:
            raise InsufficientFundsError(
                f"Insufficient funds. Balance: {self.balance_eur}, Required: {amount}"
            )
        
        self.balance_eur -= amount
        self.last_updated = datetime.utcnow()
        
        return WalletTransaction(
            transaction_id=self._generate_transaction_id(),
            user_id=self.user_id,
            transaction_type=TransactionType.WITHDRAWAL,
            amount_eur=-amount,  # Negative for withdrawals
            description=description,
            reference_order_id=reference_order_id,
            creation_date=self.last_updated
        )
    
    def add_commission(self, amount: Decimal, description: str,
                      reference_order_id: str = None) -> WalletTransaction:
        """Add commission to wallet."""
        if amount <= 0:
            raise ValidationError("Commission amount must be positive")
        
        self.balance_eur += amount
        self.last_updated = datetime.utcnow()
        
        return WalletTransaction(
            transaction_id=self._generate_transaction_id(),
            user_id=self.user_id,
            transaction_type=TransactionType.COMMISSION,
            amount_eur=amount,
            description=description,
            reference_order_id=reference_order_id,
            creation_date=self.last_updated
        )
    
    def has_sufficient_funds(self, amount: Decimal) -> bool:
        """Check if wallet has sufficient funds."""
        return self.balance_eur >= amount
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        import uuid
        return f"TXN_{uuid.uuid4().hex[:12].upper()}"