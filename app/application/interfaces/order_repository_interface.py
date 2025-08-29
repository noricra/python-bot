"""
Order repository interface (port).
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities import Order


class OrderRepositoryInterface(ABC):
    """Interface for order repository."""
    
    @abstractmethod
    async def create(self, order: Order) -> bool:
        """Create a new order."""
        pass
    
    @abstractmethod
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        pass
    
    @abstractmethod
    async def get_by_buyer(self, buyer_id: int) -> List[Order]:
        """Get orders by buyer."""
        pass
    
    @abstractmethod
    async def get_by_seller(self, seller_id: int) -> List[Order]:
        """Get orders by seller."""
        pass
    
    @abstractmethod
    async def get_by_product(self, product_id: str) -> List[Order]:
        """Get orders by product."""
        pass
    
    @abstractmethod
    async def get_by_payment_id(self, payment_id: str) -> Optional[Order]:
        """Get order by NOWPayments payment ID."""
        pass
    
    @abstractmethod
    async def update(self, order: Order) -> bool:
        """Update order."""
        pass
    
    @abstractmethod
    async def get_completed_orders_for_seller(self, seller_id: int) -> List[Order]:
        """Get completed orders for seller (for payout calculation)."""
        pass