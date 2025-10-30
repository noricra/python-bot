from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
import os
import psycopg2
import psycopg2.extras
import logging
import asyncio
from telegram import Bot

from app.core import settings as core_settings
from app.core.database_init import get_postgresql_connection
from app.core.file_utils import download_product_file_from_b2

logger = logging.getLogger(__name__)


app = FastAPI()


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not secret or not signature:
        return False
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha512).hexdigest()
    return hmac.compare_digest(mac, signature)


@app.post("/ipn/nowpayments")
async def nowpayments_ipn(request: Request):
    raw = await request.body()
    signature = request.headers.get('x-nowpayments-sig') or request.headers.get('X-Nowpayments-Sig')
    if not verify_signature(core_settings.NOWPAYMENTS_IPN_SECRET or '', raw, signature or ''):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        data = json.loads(raw.decode())
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    payment_id = data.get('payment_id')
    payment_status = data.get('payment_status')
    if not payment_id:
        raise HTTPException(status_code=400, detail="missing payment_id")

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute('SELECT order_id, product_id, seller_user_id, seller_revenue FROM orders WHERE nowpayments_id = %s', (payment_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"ok": True}

        order_id, product_id, seller_user_id, seller_revenue = row

        if payment_status in ['finished', 'confirmed']:
            # Check if already delivered to avoid duplicate sends
            cursor.execute('SELECT payment_status, file_delivered, buyer_user_id FROM orders WHERE nowpayments_id = %s', (payment_id,))
            order_check = cursor.fetchone()

            if order_check and order_check[0] == 'completed' and order_check[1]:
                # Already processed and delivered
                conn.close()
                logger.info(f"Order {order_id} already completed and delivered, skipping")
                return {"ok": True}

            buyer_user_id = order_check[2] if order_check else None

            # Update order status (but keep file_delivered=FALSE until actually sent)
            cursor.execute('UPDATE orders SET payment_status = %s, completed_at = CURRENT_TIMESTAMP WHERE nowpayments_id = %s', ('completed', payment_id))
            cursor.execute('UPDATE products SET sales_count = sales_count + 1 WHERE product_id = %s', (product_id,))
            cursor.execute('UPDATE users SET total_sales = total_sales + 1, total_revenue = total_revenue + %s WHERE user_id = %s', (seller_revenue, seller_user_id))

            conn.commit()

            # Send formation automatically to buyer
            if buyer_user_id:
                await send_formation_to_buyer(buyer_user_id, order_id, product_id, payment_id)
        conn.close()
    except psycopg2.Error:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail="db error")

    return {"ok": True}


async def send_formation_to_buyer(buyer_user_id: int, order_id: str, product_id: str, payment_id: str):
    """Envoie automatiquement la formation à l'acheteur après paiement confirmé"""
    try:
        bot = Bot(token=core_settings.TELEGRAM_BOT_TOKEN)

        # Get product info
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('SELECT title, main_file_url FROM products WHERE product_id = %s', (product_id,))
        product_result = cursor.fetchone()

        if not product_result:
            logger.error(f"Product {product_id} not found for auto delivery")
            conn.close()
            return

        title, file_url = product_result

        # Send confirmation message with file
        success_message = f"""✅ **PAIEMENT CONFIRMÉ !**

🎉 Félicitations ! Votre paiement a été reçu et confirmé.

📦 **Commande :** `{order_id}`
📚 **Formation :** {title}

Votre formation est en cours d'envoi..."""

        await bot.send_message(
            chat_id=buyer_user_id,
            text=success_message,
            parse_mode='Markdown'
        )

        # Download file from B2 and send it
        if file_url:
            try:
                # Download from Backblaze B2 to temp location
                local_path = await download_product_file_from_b2(file_url, product_id)

                if local_path and os.path.exists(local_path):
                    # Send the file
                    with open(local_path, 'rb') as file:
                        await bot.send_document(
                            chat_id=buyer_user_id,
                            document=file,
                            caption=f"📚 **{title}**\n\n✅ Téléchargement réussi !\n\n💡 Conservez ce fichier précieusement.",
                            parse_mode='Markdown'
                        )

                    # Mark as delivered and update download count
                    cursor.execute('''UPDATE orders
                                     SET file_delivered = TRUE,
                                         download_count = download_count + 1
                                     WHERE nowpayments_id = %s''', (payment_id,))
                    conn.commit()

                    logger.info(f"✅ Formation automatically sent to user {buyer_user_id} for order {order_id}")

                    # Clean up temp file
                    try:
                        os.remove(local_path)
                        logger.info(f"🗑️ Temp file cleaned up: {local_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ Could not clean up temp file: {cleanup_error}")
                else:
                    logger.error(f"❌ Failed to download file from B2: {file_url}")
                    await bot.send_message(
                        chat_id=buyer_user_id,
                        text="❌ Le fichier de formation est temporairement indisponible. Contactez le support.",
                        parse_mode='Markdown'
                    )

            except FileNotFoundError:
                await bot.send_message(
                    chat_id=buyer_user_id,
                    text="❌ Le fichier de formation est temporairement indisponible. Contactez le support.",
                    parse_mode='Markdown'
                )
                logger.error(f"File not found after B2 download for product {product_id}")
            except Exception as file_err:
                logger.error(f"Error downloading/sending file from B2 for order {order_id}: {file_err}")
                await bot.send_message(
                    chat_id=buyer_user_id,
                    text="❌ Erreur lors de l'envoi du fichier. Contactez le support.",
                    parse_mode='Markdown'
                )
        else:
            await bot.send_message(
                chat_id=buyer_user_id,
                text="❌ Aucun fichier associé à cette formation. Contactez le support.",
                parse_mode='Markdown'
            )

        conn.close()

    except (psycopg2.Error, Exception) as e:
        logger.error(f"Error sending formation automatically: {e}")
        # Try to send a basic confirmation at least
        try:
            bot = Bot(token=core_settings.TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=buyer_user_id,
                text=f"✅ Paiement confirmé pour la commande `{order_id}`. Contactez le support pour recevoir votre formation.",
                parse_mode='Markdown'
            )
        except:
            pass

