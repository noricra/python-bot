"""
Wallet service containing wallet-related business logic.
"""

from typing import Optional, List
from decimal import Decimal

from app.domain.entities.wallet import Wallet, WalletTransaction, TransactionType
from app.application.interfaces import WalletRepositoryInterface, UserRepositoryInterface
from app.core.exceptions import ValidationError, NotFoundError, InsufficientFundsError


class WalletService:
    """Service for wallet operations."""
    
    def __init__(self, wallet_repository: WalletRepositoryInterface,
                 user_repository: UserRepositoryInterface):
        self.wallet_repository = wallet_repository
        self.user_repository = user_repository
    
    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        """Get user wallet or create if doesn't exist."""
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        wallet = await self.wallet_repository.get_wallet(user_id)
        if wallet:
            return wallet
        
        # Create new wallet
        wallet = Wallet(user_id=user_id)
        success = await self.wallet_repository.create_wallet(wallet)
        if not success:
            raise ValidationError("Failed to create wallet")
        
        return wallet
    
    async def get_wallet_balance(self, user_id: int) -> Decimal:
        """Get wallet balance for user."""
        wallet = await self.get_or_create_wallet(user_id)
        return wallet.balance_eur
    
    async def deposit(self, user_id: int, amount: Decimal, description: str,
                     reference_order_id: str = None) -> Wallet:
        """Deposit money to user wallet."""
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive")
        
        wallet = await self.get_or_create_wallet(user_id)
        transaction = wallet.deposit(amount, description, reference_order_id)
        
        # Save transaction and update wallet
        transaction_success = await self.wallet_repository.add_transaction(transaction)
        wallet_success = await self.wallet_repository.update_wallet(wallet)
        
        if not (transaction_success and wallet_success):
            raise ValidationError("Failed to process deposit")
        
        return wallet
    
    async def withdraw(self, user_id: int, amount: Decimal, description: str,
                     reference_order_id: str = None) -> Wallet:
        """Withdraw money from user wallet."""
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be positive")
        
        wallet = await self.get_or_create_wallet(user_id)
        
        if not wallet.has_sufficient_funds(amount):
            raise InsufficientFundsError(
                f"Insufficient funds. Balance: {wallet.balance_eur}, Required: {amount}"
            )
        
        transaction = wallet.withdraw(amount, description, reference_order_id)
        
        # Save transaction and update wallet
        transaction_success = await self.wallet_repository.add_transaction(transaction)
        wallet_success = await self.wallet_repository.update_wallet(wallet)
        
        if not (transaction_success and wallet_success):
            raise ValidationError("Failed to process withdrawal")
        
        return wallet
    
    async def add_commission(self, user_id: int, amount: Decimal, description: str,
                           reference_order_id: str = None) -> Wallet:
        """Add commission to user wallet."""
        if amount <= 0:
            raise ValidationError("Commission amount must be positive")
        
        wallet = await self.get_or_create_wallet(user_id)
        transaction = wallet.add_commission(amount, description, reference_order_id)
        
        # Save transaction and update wallet
        transaction_success = await self.wallet_repository.add_transaction(transaction)
        wallet_success = await self.wallet_repository.update_wallet(wallet)
        
        if not (transaction_success and wallet_success):
            raise ValidationError("Failed to process commission")
        
        return wallet
    
    async def transfer_between_wallets(self, from_user_id: int, to_user_id: int,
                                     amount: Decimal, description: str) -> tuple[Wallet, Wallet]:
        """Transfer money between two wallets."""
        if amount <= 0:
            raise ValidationError("Transfer amount must be positive")
        
        if from_user_id == to_user_id:
            raise ValidationError("Cannot transfer to the same wallet")
        
        # Get both wallets
        from_wallet = await self.get_or_create_wallet(from_user_id)
        to_wallet = await self.get_or_create_wallet(to_user_id)
        
        # Check sufficient funds
        if not from_wallet.has_sufficient_funds(amount):
            raise InsufficientFundsError(
                f"Insufficient funds. Balance: {from_wallet.balance_eur}, Required: {amount}"
            )
        
        # Create transactions
        withdrawal_transaction = from_wallet.withdraw(amount, f"Transfer to user {to_user_id}: {description}")
        deposit_transaction = to_wallet.deposit(amount, f"Transfer from user {from_user_id}: {description}")
        
        # Save everything
        import asyncio
        results = await asyncio.gather(
            self.wallet_repository.add_transaction(withdrawal_transaction),
            self.wallet_repository.add_transaction(deposit_transaction),
            self.wallet_repository.update_wallet(from_wallet),
            self.wallet_repository.update_wallet(to_wallet),
            return_exceptions=True
        )
        
        if not all(results):
            raise ValidationError("Failed to process transfer")
        
        return from_wallet, to_wallet
    
    async def get_wallet_transactions(self, user_id: int, limit: int = 50) -> List[WalletTransaction]:
        """Get wallet transactions for user."""
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        return await self.wallet_repository.get_transactions(user_id, limit)
    
    async def has_sufficient_funds(self, user_id: int, amount: Decimal) -> bool:
        """Check if user has sufficient funds."""
        try:
            wallet = await self.get_or_create_wallet(user_id)
            return wallet.has_sufficient_funds(amount)
        except Exception:
            return False
    
    async def get_transaction(self, transaction_id: str) -> Optional[WalletTransaction]:
        """Get transaction by ID."""
        return await self.wallet_repository.get_transaction_by_id(transaction_id)
    
    async def process_order_payment_from_wallet(self, user_id: int, order_amount: Decimal,
                                              order_id: str) -> Wallet:
        """Process payment from wallet for an order."""
        description = f"Payment for order {order_id}"
        return await self.withdraw(user_id, order_amount, description, order_id)
    
    async def process_seller_payout_to_wallet(self, seller_id: int, payout_amount: Decimal,
                                            order_id: str) -> Wallet:
        """Process payout to seller wallet."""
        description = f"Payout for order {order_id}"
        return await self.deposit(seller_id, payout_amount, description, order_id)
    
    async def process_referrer_commission(self, referrer_id: int, commission_amount: Decimal,
                                        order_id: str) -> Wallet:
        """Process referrer commission."""
        description = f"Referral commission for order {order_id}"
        return await self.add_commission(referrer_id, commission_amount, description, order_id)