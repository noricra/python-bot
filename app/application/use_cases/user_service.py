"""
User service containing user-related business logic.
"""

import secrets
from typing import Optional, List
from decimal import Decimal

from app.domain.entities import User
from app.application.interfaces import UserRepositoryInterface
from app.core.exceptions import ValidationError, NotFoundError
from app.core.utils import validate_solana_address


class UserService:
    """Service for user operations."""
    
    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository
    
    async def register_user(self, user_id: int, username: str, 
                          first_name: str, language_code: str = "fr") -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.user_repository.get_by_id(user_id)
        if existing_user:
            return existing_user
        
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            language_code=language_code
        )
        
        success = await self.user_repository.create(user)
        if not success:
            raise ValidationError("Failed to create user")
        
        return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repository.get_by_id(user_id)
    
    async def get_user_or_create(self, user_id: int, username: str = None, 
                                first_name: str = None, language_code: str = "fr") -> User:
        """Get user or create if doesn't exist."""
        user = await self.user_repository.get_by_id(user_id)
        if user:
            return user
        
        return await self.register_user(user_id, username, first_name, language_code)
    
    async def become_seller(self, user_id: int, seller_name: str, 
                          seller_bio: str, solana_address: str) -> User:
        """Convert user to seller."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        if user.is_seller:
            raise ValidationError("User is already a seller")
        
        # Check if Solana address is already taken
        address_taken = await self.user_repository.is_solana_address_taken(
            solana_address, exclude_user_id=user_id
        )
        if address_taken:
            raise ValidationError("This Solana address is already registered")
        
        user.make_seller(seller_name, seller_bio, solana_address)
        
        success = await self.user_repository.update(user)
        if not success:
            raise ValidationError("Failed to update user to seller")
        
        return user
    
    async def update_seller_info(self, user_id: int, seller_name: str = None,
                               seller_bio: str = None, solana_address: str = None) -> User:
        """Update seller information."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        if not user.is_seller:
            raise ValidationError("User is not a seller")
        
        if seller_name:
            user.seller_name = seller_name.strip()
        
        if seller_bio:
            user.seller_bio = seller_bio.strip()
        
        if solana_address:
            if not validate_solana_address(solana_address):
                raise ValidationError("Invalid Solana address")
            
            # Check if address is taken by another user
            address_taken = await self.user_repository.is_solana_address_taken(
                solana_address, exclude_user_id=user_id
            )
            if address_taken:
                raise ValidationError("This Solana address is already registered")
            
            user.seller_solana_address = solana_address
        
        success = await self.user_repository.update(user)
        if not success:
            raise ValidationError("Failed to update seller information")
        
        return user
    
    async def remove_seller_status(self, user_id: int) -> User:
        """Remove seller status from user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        if not user.is_seller:
            raise ValidationError("User is not a seller")
        
        user.remove_seller_status()
        
        success = await self.user_repository.update(user)
        if not success:
            raise ValidationError("Failed to remove seller status")
        
        return user
    
    async def update_seller_rating(self, seller_id: int, new_rating: Decimal, 
                                 sales_count: int) -> User:
        """Update seller rating and sales count."""
        user = await self.user_repository.get_by_id(seller_id)
        if not user:
            raise NotFoundError(f"Seller {seller_id} not found")
        
        if not user.is_seller:
            raise ValidationError("User is not a seller")
        
        user.update_rating(new_rating, sales_count)
        
        success = await self.user_repository.update(user)
        if not success:
            raise ValidationError("Failed to update seller rating")
        
        return user
    
    async def generate_partner_code(self, user_id: int) -> str:
        """Generate a unique partner code for user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        # Generate unique partner code
        while True:
            code = f"REF{secrets.token_hex(4).upper()}"
            existing_user = await self.user_repository.get_by_partner_code(code)
            if not existing_user:
                break
        
        user.is_partner = True
        user.partner_code = code
        
        success = await self.user_repository.update(user)
        if not success:
            raise ValidationError("Failed to generate partner code")
        
        return code
    
    async def get_user_by_partner_code(self, partner_code: str) -> Optional[User]:
        """Get user by partner code."""
        return await self.user_repository.get_by_partner_code(partner_code)
    
    async def add_referral_earnings(self, user_id: int, amount: Decimal) -> User:
        """Add referral earnings to user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        
        user.referral_earnings_eur += amount
        
        success = await self.user_repository.update(user)
        if not success:
            raise ValidationError("Failed to update referral earnings")
        
        return user