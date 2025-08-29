"""
Wallet repository interface (port).
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities.wallet import Wallet, WalletTransaction


class WalletRepositoryInterface(ABC):
    """Interface for wallet repository."""
    
    @abstractmethod
    async def get_wallet(self, user_id: int) -> Optional[Wallet]:
        """Get user wallet."""
        pass
    
    @abstractmethod
    async def create_wallet(self, wallet: Wallet) -> bool:
        """Create wallet for user."""
        pass
    
    @abstractmethod
    async def update_wallet(self, wallet: Wallet) -> bool:
        """Update wallet balance."""
        pass
    
    @abstractmethod
    async def add_transaction(self, transaction: WalletTransaction) -> bool:
        """Add wallet transaction."""
        pass
    
    @abstractmethod
    async def get_transactions(self, user_id: int, limit: int = 50) -> List[WalletTransaction]:
        """Get wallet transactions for user."""
        pass
    
    @abstractmethod
    async def get_transaction_by_id(self, transaction_id: str) -> Optional[WalletTransaction]:
        """Get transaction by ID."""
        pass