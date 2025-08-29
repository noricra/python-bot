"""
Payout repository interface (port).
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities import Payout


class PayoutRepositoryInterface(ABC):
    """Interface for payout repository."""
    
    @abstractmethod
    async def create(self, payout: Payout) -> bool:
        """Create a new payout request."""
        pass
    
    @abstractmethod
    async def get_by_id(self, payout_id: str) -> Optional[Payout]:
        """Get payout by ID."""
        pass
    
    @abstractmethod
    async def get_by_seller(self, seller_id: int) -> List[Payout]:
        """Get payouts by seller."""
        pass
    
    @abstractmethod
    async def get_pending_payouts(self) -> List[Payout]:
        """Get all pending payouts."""
        pass
    
    @abstractmethod
    async def update(self, payout: Payout) -> bool:
        """Update payout."""
        pass