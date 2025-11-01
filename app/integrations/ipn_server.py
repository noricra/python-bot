from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
import os
import psycopg2
import psycopg2.extras
import logging
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

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
        cursor.execute('SELECT order_id, product_id, seller_user_id, seller_revenue_usd, platform_commission_usd FROM orders WHERE nowpayments_id = %s', (payment_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"ok": True}

        order_id = row['order_id']
        product_id = row['product_id']
        seller_user_id = row['seller_user_id']
        seller_revenue_usd = row['seller_revenue_usd']
        platform_commission_usd = row['platform_commission_usd']

        if payment_status in ['finished', 'confirmed']:
            # Check if already delivered to avoid duplicate sends
            cursor.execute('SELECT payment_status, file_delivered, buyer_user_id FROM orders WHERE nowpayments_id = %s', (payment_id,))
            order_check = cursor.fetchone()

            if order_check and order_check['payment_status'] == 'completed' and order_check['file_delivered']:
                # Already processed and delivered
                conn.close()
                logger.info(f"Order {order_id} already completed and delivered, skipping")
                return {"ok": True}

            buyer_user_id = order_check['buyer_user_id'] if order_check else None

            # Log commission split info
            logger.info(f"Payment confirmed - Order: {order_id}, Seller revenue: ${seller_revenue_usd:.2f}, Platform commission: ${platform_commission_usd:.2f}")

            # Update order status (but keep file_delivered=FALSE until actually sent)
            cursor.execute('UPDATE orders SET payment_status = %s, completed_at = CURRENT_TIMESTAMP WHERE nowpayments_id = %s', ('completed', payment_id))
            cursor.execute('UPDATE products SET sales_count = sales_count + 1 WHERE product_id = %s', (product_id,))
            cursor.execute('UPDATE users SET total_sales = total_sales + 1, total_revenue = total_revenue + %s WHERE user_id = %s', (seller_revenue_usd, seller_user_id))

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

        # Send confirmation message with button to library
        success_message = f"""✅ **PAIEMENT CONFIRMÉ !**

🎉 Félicitations ! Votre paiement a été reçu et confirmé.

📦 **Commande :** `{order_id}`
📚 **Formation :** {title}

Votre formation est en cours d'envoi..."""

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📚 Voir ma bibliothèque", callback_data='library_menu')
        ]])

        await bot.send_message(
            chat_id=buyer_user_id,
            text=success_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

        # Download file from B2 and send it
        if file_url:
            try:
                # Download from Backblaze B2 to temp location
                local_path = await download_product_file_from_b2(file_url, product_id)

                if local_path and os.path.exists(local_path):
                    # Send the file with library button
                    library_keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("📚 Accéder à ma bibliothèque", callback_data='library_menu')
                    ]])

                    with open(local_path, 'rb') as file:
                        await bot.send_document(
                            chat_id=buyer_user_id,
                            document=file,
                            caption=f"📚 **{title}**\n\n✅ Téléchargement réussi !\n\n💡 Conservez ce fichier précieusement.\n📖 Vous pouvez aussi le retrouver dans votre bibliothèque.",
                            parse_mode='Markdown',
                            reply_markup=library_keyboard
                        )

                    # Mark as delivered and update download count
                    cursor.execute('''UPDATE orders
                                     SET file_delivered = TRUE,
                                         download_count = download_count + 1
                                     WHERE nowpayments_id = %s''', (payment_id,))
                    conn.commit()

                    logger.info(f"✅ Formation automatically sent to user {buyer_user_id} for order {order_id}")

                    # Send confirmation emails
                    try:
                        from app.core.email_service import EmailService
                        email_service = EmailService()

                        # Get seller and buyer info for emails
                        cursor.execute('''
                            SELECT
                                u_seller.email as seller_email,
                                u_seller.seller_name as seller_name,
                                u_buyer.username as buyer_username,
                                u_buyer.email as buyer_email,
                                o.product_price_usd,
                                o.seller_revenue_usd,
                                o.platform_commission_usd,
                                o.payment_currency,
                                p.title as product_title
                            FROM orders o
                            JOIN users u_seller ON o.seller_user_id = u_seller.user_id
                            LEFT JOIN users u_buyer ON o.buyer_user_id = u_buyer.user_id
                            JOIN products p ON o.product_id = p.product_id
                            WHERE o.nowpayments_id = %s
                        ''', (payment_id,))
                        email_data = cursor.fetchone()

                        if email_data:
                            # Email au vendeur (nouvelle vente)
                            if email_data['seller_email']:
                                email_service.send_sale_notification_seller(
                                    seller_email=email_data['seller_email'],
                                    seller_name=email_data['seller_name'] or 'Vendeur',
                                    product_title=email_data['product_title'],
                                    product_price_usd=float(email_data['product_price_usd']),
                                    seller_revenue_usd=float(email_data['seller_revenue_usd']),
                                    platform_commission_usd=float(email_data['platform_commission_usd']),
                                    buyer_username=email_data['buyer_username'] or f'User_{buyer_user_id}',
                                    order_id=order_id,
                                    payment_currency=email_data['payment_currency']
                                )
                                logger.info(f"📧 Email vente envoyé au vendeur: {email_data['seller_email']}")

                            # Email à l'acheteur (confirmation d'achat)
                            if email_data['buyer_email']:
                                email_service.send_purchase_confirmation_buyer(
                                    buyer_email=email_data['buyer_email'],
                                    buyer_username=email_data['buyer_username'] or f'User_{buyer_user_id}',
                                    product_title=email_data['product_title'],
                                    product_price_usd=float(email_data['product_price_usd']),
                                    payment_currency=email_data['payment_currency'],
                                    order_id=order_id,
                                    seller_name=email_data['seller_name'] or 'Vendeur'
                                )
                                logger.info(f"📧 Email confirmation envoyé à l'acheteur: {email_data['buyer_email']}")

                    except Exception as email_error:
                        logger.error(f"Erreur lors de l'envoi des emails de confirmation: {email_error}")
                        # Ne pas bloquer la livraison si erreur email

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

