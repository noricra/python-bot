"""
Product service containing product-related business logic.
"""

from typing import Optional, List
from decimal import Decimal

from app.domain.entities import Product, User
from app.domain.entities.product import ProductStatus
from app.application.interfaces import ProductRepositoryInterface, UserRepositoryInterface
from app.core.exceptions import ValidationError, NotFoundError, UnauthorizedError
from app.core.utils import generate_product_id


class ProductService:
    """Service for product operations."""
    
    def __init__(self, product_repository: ProductRepositoryInterface,
                 user_repository: UserRepositoryInterface):
        self.product_repository = product_repository
        self.user_repository = user_repository
    
    async def create_product(self, seller_id: int, title: str, description: str,
                           price_eur: Decimal, category: str, preview_text: str = None,
                           file_path: str = None) -> Product:
        """Create a new product."""
        # Verify seller exists and is a seller
        seller = await self.user_repository.get_by_id(seller_id)
        if not seller:
            raise NotFoundError(f"Seller {seller_id} not found")
        
        if not seller.is_seller:
            raise UnauthorizedError("User is not authorized to sell products")
        
        # Generate unique product ID
        while True:
            product_id = generate_product_id()
            if not await self.product_repository.exists(product_id):
                break
        
        product = Product(
            product_id=product_id,
            seller_user_id=seller_id,
            title=title.strip(),
            description=description.strip(),
            price_eur=price_eur,
            category=category,
            preview_text=preview_text.strip() if preview_text else None,
            file_path=file_path
        )
        
        success = await self.product_repository.create(product)
        if not success:
            raise ValidationError("Failed to create product")
        
        return product
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return await self.product_repository.get_by_id(product_id)
    
    async def get_product_with_seller_check(self, product_id: str, seller_id: int) -> Product:
        """Get product and verify seller ownership."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        
        if product.seller_user_id != seller_id:
            raise UnauthorizedError("You don't own this product")
        
        return product
    
    async def update_product(self, product_id: str, seller_id: int,
                           title: str = None, description: str = None,
                           price_eur: Decimal = None, category: str = None,
                           preview_text: str = None) -> Product:
        """Update product information."""
        product = await self.get_product_with_seller_check(product_id, seller_id)
        
        if title is not None:
            product.title = title.strip()
        
        if description is not None:
            product.description = description.strip()
        
        if price_eur is not None:
            product.update_price(price_eur)
        
        if category is not None:
            product.category = category
        
        if preview_text is not None:
            product.preview_text = preview_text.strip() if preview_text else None
        
        success = await self.product_repository.update(product)
        if not success:
            raise ValidationError("Failed to update product")
        
        return product
    
    async def delete_product(self, product_id: str, seller_id: int) -> bool:
        """Delete a product (seller only)."""
        product = await self.get_product_with_seller_check(product_id, seller_id)
        
        product.delete()
        
        success = await self.product_repository.update(product)
        if not success:
            raise ValidationError("Failed to delete product")
        
        return True
    
    async def suspend_product(self, product_id: str) -> Product:
        """Suspend a product (admin only)."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        
        product.suspend()
        
        success = await self.product_repository.update(product)
        if not success:
            raise ValidationError("Failed to suspend product")
        
        return product
    
    async def activate_product(self, product_id: str, seller_id: int) -> Product:
        """Activate a product."""
        product = await self.get_product_with_seller_check(product_id, seller_id)
        
        product.activate()
        
        success = await self.product_repository.update(product)
        if not success:
            raise ValidationError("Failed to activate product")
        
        return product
    
    async def deactivate_product(self, product_id: str, seller_id: int) -> Product:
        """Deactivate a product."""
        product = await self.get_product_with_seller_check(product_id, seller_id)
        
        product.deactivate()
        
        success = await self.product_repository.update(product)
        if not success:
            raise ValidationError("Failed to deactivate product")
        
        return product
    
    async def get_seller_products(self, seller_id: int) -> List[Product]:
        """Get all products for a seller."""
        return await self.product_repository.get_by_seller(seller_id)
    
    async def get_products_by_category(self, category: str, limit: int = 10) -> List[Product]:
        """Get products by category."""
        return await self.product_repository.get_by_category(category, limit)
    
    async def get_bestsellers(self, limit: int = 10) -> List[Product]:
        """Get bestselling products."""
        return await self.product_repository.get_bestsellers(limit)
    
    async def get_newest_products(self, limit: int = 10) -> List[Product]:
        """Get newest products."""
        return await self.product_repository.get_newest(limit)
    
    async def search_products(self, query: str, limit: int = 10) -> List[Product]:
        """Search products by title or description."""
        if not query.strip():
            return []
        
        return await self.product_repository.search(query.strip(), limit)
    
    async def record_sale(self, product_id: str) -> Product:
        """Record a sale for a product."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        
        product.record_sale()
        
        success = await self.product_repository.update(product)
        if not success:
            raise ValidationError("Failed to record product sale")
        
        return product
    
    async def update_product_rating(self, product_id: str, new_rating: Decimal) -> Product:
        """Update product rating."""
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        
        product.update_rating(new_rating)
        
        success = await self.product_repository.update(product)
        if not success:
            raise ValidationError("Failed to update product rating")
        
        return product