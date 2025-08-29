"""
User repository interface (port).
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities import User


class UserRepositoryInterface(ABC):
    """Interface for user repository."""
    
    @abstractmethod
    async def create(self, user: User) -> bool:
        """Create a new user."""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def get_by_partner_code(self, partner_code: str) -> Optional[User]:
        """Get user by partner code."""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> bool:
        """Update user."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """Delete user."""
        pass
    
    @abstractmethod
    async def get_all_sellers(self) -> List[User]:
        """Get all sellers."""
        pass
    
    @abstractmethod
    async def is_solana_address_taken(self, address: str, exclude_user_id: int = None) -> bool:
        """Check if Solana address is already taken."""
        pass