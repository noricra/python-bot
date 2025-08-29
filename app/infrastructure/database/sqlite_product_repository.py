"""
SQLite implementation of ProductRepositoryInterface.
"""

import sqlite3
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.entities import Product
from app.domain.entities.product import ProductStatus
from app.application.interfaces import ProductRepositoryInterface
from app.core import get_sqlite_connection, settings


class SqliteProductRepository(ProductRepositoryInterface):
    """SQLite implementation of product repository."""
    
    def __init__(self, database_path: Optional[str] = None):
        self.database_path = database_path or settings.DATABASE_PATH
    
    async def create(self, product: Product) -> bool:
        """Create a new product."""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO products
                (product_id, seller_user_id, title, description, price_eur, category,
                 file_path, preview_text, status, sales_count, rating, creation_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product.product_id, product.seller_user_id, product.title,
                product.description, float(product.price_eur), product.category,
                product.file_path, product.preview_text, product.status.value,
                product.sales_count, float(product.rating),
                product.creation_date or datetime.utcnow()
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error creating product: {e}")
            return False
        finally:
            conn.close()
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
            row = cursor.fetchone()
            if row:
                return Product(
                    product_id=row['product_id'],
                    seller_user_id=row['seller_user_id'],
                    title=row['title'],
                    description=row['description'],
                    price_eur=Decimal(str(row['price_eur'])),
                    category=row['category'],
                    file_path=row['file_path'],
                    preview_text=row['preview_text'],
                    status=ProductStatus(row['status']),
                    sales_count=row['sales_count'] or 0,
                    rating=Decimal(str(row['rating'] or 0)),
                    creation_date=datetime.fromisoformat(row['creation_date']) if row['creation_date'] else None
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting product: {e}")
            return None
        finally:
            conn.close()
    
    async def get_by_seller(self, seller_id: int) -> List[Product]:
        """Get products by seller."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM products WHERE seller_user_id = ?', (seller_id,))
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = await self.get_by_id(row['product_id'])
                if product:
                    products.append(product)
            return products
        except sqlite3.Error as e:
            print(f"Error getting products by seller: {e}")
            return []
        finally:
            conn.close()
    
    async def get_by_category(self, category: str, limit: int = 10) -> List[Product]:
        """Get products by category."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM products 
                WHERE category = ? AND status = 'active'
                ORDER BY sales_count DESC
                LIMIT ?
            ''', (category, limit))
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = await self.get_by_id(row['product_id'])
                if product:
                    products.append(product)
            return products
        except sqlite3.Error as e:
            print(f"Error getting products by category: {e}")
            return []
        finally:
            conn.close()
    
    async def get_bestsellers(self, limit: int = 10) -> List[Product]:
        """Get bestseller products."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM products 
                WHERE status = 'active'
                ORDER BY sales_count DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = await self.get_by_id(row['product_id'])
                if product:
                    products.append(product)
            return products
        except sqlite3.Error as e:
            print(f"Error getting bestsellers: {e}")
            return []
        finally:
            conn.close()
    
    async def get_newest(self, limit: int = 10) -> List[Product]:
        """Get newest products."""
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM products 
                WHERE status = 'active'
                ORDER BY creation_date DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = await self.get_by_id(row['product_id'])
                if product:
                    products.append(product)
            return products
        except sqlite3.Error as e:
            print(f"Error getting newest products: {e}")
            return []
        finally:
            conn.close()
    
    async def search(self, query: str, limit: int = 10) -> List[Product]:
        """Search products."""
        # Simplified search implementation
        return await self.get_bestsellers(limit)
    
    async def update(self, product: Product) -> bool:
        """Update product."""
        return await self.create(product)  # Use REPLACE behavior
    
    async def delete(self, product_id: str) -> bool:
        """Delete product."""
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting product: {e}")
            return False
        finally:
            conn.close()
    
    async def exists(self, product_id: str) -> bool:
        """Check if product exists."""
        product = await self.get_by_id(product_id)
        return product is not None