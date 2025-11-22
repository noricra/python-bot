"""
Service de cache Telegram pour réutilisation des file_id
Évite les re-uploads et accélère l'affichage (Railway-proof)
"""
import logging
from typing import Optional
from app.core.db_pool import get_connection, put_connection
import psycopg2.extras

logger = logging.getLogger(__name__)


class TelegramCacheService:
    """Gestion du cache Telegram (file_id) pour images produits"""

    def get_product_image_file_id(self, product_id: str, image_type: str = 'thumb') -> Optional[str]:
        """
        Récupère le file_id Telegram pour une image produit

        Args:
            product_id: ID du produit
            image_type: 'thumb' ou 'cover'

        Returns:
            file_id Telegram ou None si pas en cache
        """
        conn = get_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            field = 'telegram_thumb_file_id' if image_type == 'thumb' else 'telegram_cover_file_id'
            cursor.execute(f"SELECT {field} FROM products WHERE product_id = %s", (product_id,))

            result = cursor.fetchone()
            return result[field] if result and result[field] else None

        except Exception as e:
            logger.error(f"❌ Error fetching Telegram file_id for {product_id}: {e}")
            return None
        finally:
            put_connection(conn)

    def save_telegram_file_id(self, product_id: str, file_id: str, image_type: str = 'thumb') -> bool:
        """
        Sauvegarde le file_id Telegram pour réutilisation future

        Args:
            product_id: ID du produit
            file_id: file_id retourné par Telegram
            image_type: 'thumb' ou 'cover'

        Returns:
            bool: True si sauvegarde réussie, False sinon
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            field = 'telegram_thumb_file_id' if image_type == 'thumb' else 'telegram_cover_file_id'
            cursor.execute(
                f"UPDATE products SET {field} = %s WHERE product_id = %s",
                (file_id, product_id)
            )
            conn.commit()
            logger.info(f"✅ Telegram file_id cached: {product_id}/{image_type} -> {file_id[:20]}...")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving Telegram file_id for {product_id}: {e}")
            conn.rollback()
            return False
        finally:
            put_connection(conn)

    def get_both_file_ids(self, product_id: str) -> dict:
        """
        Récupère les deux file_id (thumb + cover) d'un produit

        Args:
            product_id: ID du produit

        Returns:
            dict: {'thumb': file_id or None, 'cover': file_id or None}
        """
        conn = get_connection()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT telegram_thumb_file_id, telegram_cover_file_id
                FROM products
                WHERE product_id = %s
            """, (product_id,))

            result = cursor.fetchone()

            if result:
                return {
                    'thumb': result['telegram_thumb_file_id'],
                    'cover': result['telegram_cover_file_id']
                }
            return {'thumb': None, 'cover': None}

        except Exception as e:
            logger.error(f"❌ Error fetching Telegram file_ids for {product_id}: {e}")
            return {'thumb': None, 'cover': None}
        finally:
            put_connection(conn)

    def invalidate_cache(self, product_id: str, image_type: Optional[str] = None):
        """
        Invalide le cache Telegram (si image modifiée)

        Args:
            product_id: ID du produit
            image_type: 'thumb', 'cover', ou None pour tout invalider
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            if image_type == 'thumb':
                cursor.execute(
                    "UPDATE products SET telegram_thumb_file_id = NULL WHERE product_id = %s",
                    (product_id,)
                )
            elif image_type == 'cover':
                cursor.execute(
                    "UPDATE products SET telegram_cover_file_id = NULL WHERE product_id = %s",
                    (product_id,)
                )
            else:
                # Invalider les deux
                cursor.execute(
                    "UPDATE products SET telegram_thumb_file_id = NULL, telegram_cover_file_id = NULL WHERE product_id = %s",
                    (product_id,)
                )

            conn.commit()
            logger.info(f"🗑️  Telegram cache invalidated: {product_id}/{image_type or 'all'}")

        except Exception as e:
            logger.error(f"❌ Error invalidating Telegram cache for {product_id}: {e}")
            conn.rollback()
        finally:
            put_connection(conn)


# Singleton instance
_telegram_cache_service = None


def get_telegram_cache_service() -> TelegramCacheService:
    """
    Get singleton instance of TelegramCacheService

    Returns:
        TelegramCacheService: Service instance
    """
    global _telegram_cache_service
    if _telegram_cache_service is None:
        _telegram_cache_service = TelegramCacheService()
    return _telegram_cache_service
