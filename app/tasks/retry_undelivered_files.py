"""
Cronjob to retry delivery of undelivered files
Runs every hour to detect and retry failed deliveries

Usage:
    python -m app.tasks.retry_undelivered_files
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database_init import get_postgresql_connection
from app.core.db_pool import init_connection_pool, put_connection
from app.core import settings as core_settings
from telegram import Bot
from app.integrations.ipn_server import send_formation_to_buyer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def retry_undelivered_files():
    """
    Find orders that are paid but file not delivered, and retry delivery.

    Criteria for retry:
    - payment_status = 'completed'
    - file_delivered = FALSE
    - completed_at is older than 5 minutes (to avoid race conditions)
    - completed_at is less than 7 days old (don't retry very old orders)
    """
    conn = None
    try:
        # Initialize connection pool
        init_connection_pool(min_connections=1, max_connections=2)

        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Find undelivered paid orders
        cursor.execute('''
            SELECT
                o.order_id,
                o.buyer_user_id,
                o.product_id,
                o.nowpayments_id,
                o.completed_at,
                p.title
            FROM orders o
            JOIN products p ON o.product_id = p.product_id
            WHERE o.payment_status = 'completed'
              AND o.file_delivered = FALSE
              AND o.completed_at < NOW() - INTERVAL '5 minutes'
              AND o.completed_at > NOW() - INTERVAL '7 days'
            ORDER BY o.completed_at ASC
        ''')

        undelivered_orders = cursor.fetchall()
        conn.commit()

        if not undelivered_orders:
            logger.info("✅ No undelivered orders found")
            return

        logger.info(f"🔍 Found {len(undelivered_orders)} undelivered orders")

        # Retry delivery for each order
        for row in undelivered_orders:
            order_id, buyer_user_id, product_id, payment_id, completed_at, product_title = row

            logger.info(f"🔄 Retrying delivery for order {order_id} (product: {product_title}, completed: {completed_at})")

            try:
                await send_formation_to_buyer(
                    buyer_user_id=buyer_user_id,
                    order_id=order_id,
                    product_id=product_id,
                    payment_id=payment_id
                )

                logger.info(f"✅ Retry successful for order {order_id}")

            except Exception as e:
                logger.error(f"❌ Retry failed for order {order_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"❌ Error in retry_undelivered_files: {e}")
        if conn:
            conn.rollback()
        raise

    finally:
        if conn:
            put_connection(conn)


async def send_admin_report(undelivered_count: int):
    """
    Send daily report to admin about undelivered orders.

    Args:
        undelivered_count: Number of orders that failed delivery
    """
    if undelivered_count == 0:
        return

    try:
        bot = Bot(token=core_settings.TELEGRAM_BOT_TOKEN)

        message = f"""🚨 **Rapport de Livraison - Échecs**

📊 **{undelivered_count}** commandes payées mais non livrées détectées.

⚠️ Action requise : Vérifier les logs et contacter les clients si nécessaire.

🕐 Rapport généré : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        await bot.send_message(
            chat_id=core_settings.ADMIN_USER_ID,
            text=message,
            parse_mode='Markdown'
        )

        logger.info(f"✅ Admin report sent ({undelivered_count} undelivered)")

    except Exception as e:
        logger.error(f"❌ Failed to send admin report: {e}")


if __name__ == "__main__":
    logger.info("🚀 Starting retry_undelivered_files cronjob...")

    try:
        asyncio.run(retry_undelivered_files())
        logger.info("✅ Cronjob completed successfully")

    except KeyboardInterrupt:
        logger.info("⏹️ Cronjob interrupted by user")

    except Exception as e:
        logger.error(f"❌ Cronjob failed: {e}")
        sys.exit(1)
