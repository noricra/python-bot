"""
Product domain entity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum

from app.core.exceptions import ValidationError


class ProductStatus(Enum):
    """Product status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class Product:
    """Product entity representing a marketplace product."""
    
    product_id: str
    seller_user_id: int
    title: str
    description: str
    price_eur: Decimal
    category: str
    file_path: Optional[str] = None
    preview_text: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE
    sales_count: int = 0
    rating: Decimal = Decimal("0.0")
    creation_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate product data after initialization."""
        if not self.title.strip():
            raise ValidationError("Product title cannot be empty")
        
        if not self.description.strip():
            raise ValidationError("Product description cannot be empty")
        
        if self.price_eur <= 0:
            raise ValidationError("Product price must be positive")
        
        if self.rating < 0 or self.rating > 5:
            raise ValidationError("Product rating must be between 0 and 5")
        
        if self.sales_count < 0:
            raise ValidationError("Sales count cannot be negative")
    
    @property
    def is_available(self) -> bool:
        """Check if product is available for purchase."""
        return self.status == ProductStatus.ACTIVE
    
    @property
    def has_file(self) -> bool:
        """Check if product has an associated file."""
        return self.file_path is not None and self.file_path.strip() != ""
    
    def activate(self) -> None:
        """Activate the product."""
        self.status = ProductStatus.ACTIVE
    
    def deactivate(self) -> None:
        """Deactivate the product."""
        self.status = ProductStatus.INACTIVE
    
    def suspend(self) -> None:
        """Suspend the product (admin action)."""
        self.status = ProductStatus.SUSPENDED
    
    def delete(self) -> None:
        """Mark product as deleted."""
        self.status = ProductStatus.DELETED
    
    def update_price(self, new_price: Decimal) -> None:
        """Update product price."""
        if new_price <= 0:
            raise ValidationError("Price must be positive")
        self.price_eur = new_price
    
    def record_sale(self) -> None:
        """Record a sale for this product."""
        self.sales_count += 1
    
    def update_rating(self, new_rating: Decimal) -> None:
        """Update product rating."""
        if new_rating < 0 or new_rating > 5:
            raise ValidationError("Rating must be between 0 and 5")
        self.rating = new_rating
    
    def update_content(self, title: str = None, description: str = None, 
                      category: str = None, preview_text: str = None) -> None:
        """Update product content."""
        if title is not None:
            if not title.strip():
                raise ValidationError("Title cannot be empty")
            self.title = title.strip()
        
        if description is not None:
            if not description.strip():
                raise ValidationError("Description cannot be empty")
            self.description = description.strip()
        
        if category is not None:
            self.category = category
        
        if preview_text is not None:
            self.preview_text = preview_text.strip() if preview_text.strip() else None