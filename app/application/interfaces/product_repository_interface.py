"""
Product repository interface (port).
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities import Product


class ProductRepositoryInterface(ABC):
    """Interface for product repository."""
    
    @abstractmethod
    async def create(self, product: Product) -> bool:
        """Create a new product."""
        pass
    
    @abstractmethod
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        pass
    
    @abstractmethod
    async def get_by_seller(self, seller_id: int) -> List[Product]:
        """Get products by seller."""
        pass
    
    @abstractmethod
    async def get_by_category(self, category: str, limit: int = 10) -> List[Product]:
        """Get products by category."""
        pass
    
    @abstractmethod
    async def get_bestsellers(self, limit: int = 10) -> List[Product]:
        """Get bestseller products."""
        pass
    
    @abstractmethod
    async def get_newest(self, limit: int = 10) -> List[Product]:
        """Get newest products."""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Product]:
        """Search products."""
        pass
    
    @abstractmethod
    async def update(self, product: Product) -> bool:
        """Update product."""
        pass
    
    @abstractmethod
    async def delete(self, product_id: str) -> bool:
        """Delete product."""
        pass
    
    @abstractmethod
    async def exists(self, product_id: str) -> bool:
        """Check if product exists."""
        pass