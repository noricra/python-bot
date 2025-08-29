"""
User domain entity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal

from app.core.exceptions import ValidationError
from app.core.utils import validate_email, validate_solana_address


@dataclass
class User:
    """User entity representing a marketplace user."""
    
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language_code: str = "fr"
    is_seller: bool = False
    is_partner: bool = False
    partner_code: Optional[str] = None
    seller_name: Optional[str] = None
    seller_bio: Optional[str] = None
    seller_solana_address: Optional[str] = None
    seller_rating: Decimal = Decimal("0.0")
    seller_sales_count: int = 0
    referral_code: Optional[str] = None
    referral_earnings_eur: Decimal = Decimal("0.0")
    email: Optional[str] = None
    registration_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate user data after initialization."""
        if self.email and not validate_email(self.email):
            raise ValidationError(f"Invalid email format: {self.email}")
        
        if self.seller_solana_address and not validate_solana_address(self.seller_solana_address):
            raise ValidationError(f"Invalid Solana address: {self.seller_solana_address}")
        
        if self.seller_rating < 0 or self.seller_rating > 5:
            raise ValidationError("Seller rating must be between 0 and 5")
    
    @property
    def display_name(self) -> str:
        """Get the display name for the user."""
        if self.seller_name:
            return self.seller_name
        if self.first_name:
            return self.first_name
        if self.username:
            return self.username
        return f"User_{self.user_id}"
    
    def make_seller(self, seller_name: str, seller_bio: str, solana_address: str) -> None:
        """Convert user to seller."""
        if not seller_name.strip():
            raise ValidationError("Seller name cannot be empty")
        
        if not validate_solana_address(solana_address):
            raise ValidationError("Invalid Solana address")
        
        self.is_seller = True
        self.seller_name = seller_name.strip()
        self.seller_bio = seller_bio.strip()
        self.seller_solana_address = solana_address
    
    def remove_seller_status(self) -> None:
        """Remove seller status from user."""
        self.is_seller = False
        self.seller_name = None
        self.seller_bio = None
        self.seller_solana_address = None
    
    def update_rating(self, new_rating: Decimal, sales_count: int) -> None:
        """Update seller rating and sales count."""
        if not self.is_seller:
            raise ValidationError("User is not a seller")
        
        if new_rating < 0 or new_rating > 5:
            raise ValidationError("Rating must be between 0 and 5")
        
        self.seller_rating = new_rating
        self.seller_sales_count = sales_count