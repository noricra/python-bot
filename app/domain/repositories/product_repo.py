import sqlite3
from typing import Optional, Dict, List, Tuple

from app.core import get_sqlite_connection, settings as core_settings


class ProductRepository:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path or core_settings.DATABASE_PATH

    def insert_product(self, product: Dict) -> bool:
        conn = get_sqlite_connection(self.database_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO products 
                (product_id, seller_user_id, title, description, category, price_eur, price_usd, main_file_path, file_size_mb, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    product['product_id'],
                    product['seller_user_id'],
                    product['title'],
                    product.get('description'),
                    product.get('category'),
                    product['price_eur'],
                    product['price_usd'],
                    product.get('main_file_path'),
                    product.get('file_size_mb'),
                    product.get('status', 'active'),
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        conn = get_sqlite_connection(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

