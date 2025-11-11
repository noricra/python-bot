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
from app.core.db_pool import put_connection
from app.core.file_utils import download_product_file_from_b2
from app.services.b2_storage_service import B2StorageService

logger = logging.getLogger(__name__)

# Retry configuration
RETRY_DELAYS = [2, 5, 10]  # Seconds between retry attempts
MAX_RETRIES = len(RETRY_DELAYS)
PRESIGNED_URL_EXPIRY = 24 * 3600  # 24 hours


app = FastAPI()


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Railway and monitoring
    Tests: PostgreSQL connection, B2 storage, and basic service health
    """
    checks = {
        "status": "healthy",
        "postgres": False,
        "b2_configured": False,
        "telegram_configured": False
    }

    # Check PostgreSQL
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        put_connection(conn)
        checks["postgres"] = True
    except Exception as e:
        logger.error(f"Health check - PostgreSQL failed: {e}")
        checks["postgres"] = False

    # Check B2 configuration
    checks["b2_configured"] = bool(
        core_settings.B2_KEY_ID and
        core_settings.B2_APPLICATION_KEY
    )

    # Check Telegram configuration
    checks["telegram_configured"] = bool(core_settings.TELEGRAM_BOT_TOKEN)

    # Overall health status
    all_healthy = all([
        checks["postgres"],
        checks["b2_configured"],
        checks["telegram_configured"]
    ])

    if not all_healthy:
        checks["status"] = "degraded"
        return checks, 503

    return checks


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Uzeur Marketplace IPN Server",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "ipn": "/ipn/nowpayments"
        }
    }


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

    conn = None
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute('SELECT order_id, product_id, seller_user_id, seller_revenue_usd, platform_commission_usd, product_price_usd, payment_currency FROM orders WHERE nowpayments_id = %s', (payment_id,))
        row = cursor.fetchone()
        if not row:
            conn.commit()
            return {"ok": True}

        order_id = row['order_id']
        product_id = row['product_id']
        seller_user_id = row['seller_user_id']
        seller_revenue_usd = row['seller_revenue_usd']
        platform_commission_usd = row['platform_commission_usd']
        product_price_usd = row['product_price_usd']
        payment_currency = row['payment_currency']

        if payment_status in ['finished', 'confirmed']:
            # Check if already delivered to avoid duplicate sends
            cursor.execute('SELECT payment_status, file_delivered, buyer_user_id FROM orders WHERE nowpayments_id = %s', (payment_id,))
            order_check = cursor.fetchone()

            if order_check and order_check['payment_status'] == 'completed' and order_check['file_delivered']:
                # Already processed and delivered
                logger.info(f"Order {order_id} already completed and delivered, skipping")
                conn.commit()
                return {"ok": True}

            buyer_user_id = order_check['buyer_user_id'] if order_check else None

            # Log commission split info
            logger.info(f"Payment confirmed - Order: {order_id}, Seller revenue: ${seller_revenue_usd:.2f}, Platform commission: ${platform_commission_usd:.2f}")

            # Update order status (but keep file_delivered=FALSE until actually sent)
            cursor.execute('UPDATE orders SET payment_status = %s, completed_at = CURRENT_TIMESTAMP WHERE nowpayments_id = %s', ('completed', payment_id))
            cursor.execute('UPDATE products SET sales_count = sales_count + 1 WHERE product_id = %s', (product_id,))
            cursor.execute('UPDATE users SET total_sales = total_sales + 1, total_revenue = total_revenue + %s WHERE user_id = %s', (seller_revenue_usd, seller_user_id))

            conn.commit()

            # 📢 NOTIFICATION TELEGRAM AU VENDEUR : Paiement confirmé
            try:
                from app.core.seller_notifications import SellerNotifications

                # Get product title for notification
                cursor.execute('SELECT title FROM products WHERE product_id = %s', (product_id,))
                product_title_row = cursor.fetchone()
                product_title = product_title_row['title'] if product_title_row else 'Produit'

                # Get buyer info
                cursor.execute('SELECT username FROM users WHERE user_id = %s', (buyer_user_id,))
                buyer_row = cursor.fetchone()
                buyer_name = buyer_row['username'] if buyer_row and buyer_row['username'] else f'User_{buyer_user_id}'

                # Get bot instance (we need the MarketplaceBot with .application)
                # For now, we'll create a simple Bot and use it directly
                # Note: The bot needs .application.bot to send messages
                class SimpleBot:
                    def __init__(self, token):
                        from telegram import Bot
                        self.bot_instance = Bot(token=token)
                        self.application = type('obj', (object,), {'bot': self.bot_instance})()

                bot = SimpleBot(core_settings.TELEGRAM_BOT_TOKEN)

                await SellerNotifications.notify_payment_confirmed(
                    bot=bot,
                    seller_id=seller_user_id,
                    product_data={
                        'product_id': product_id,
                        'title': product_title,
                        'seller_user_id': seller_user_id
                    },
                    buyer_name=buyer_name,
                    amount_usd=product_price_usd,
                    crypto_code=payment_currency or 'CRYPTO',
                    tx_hash=None
                )
                logger.info(f"✅ Telegram notification sent to seller {seller_user_id} for order {order_id}")
            except Exception as notif_error:
                logger.error(f"❌ Failed to send Telegram notification to seller: {notif_error}")
                # Don't fail the IPN if notification fails

            # Create payout for seller (automatic) and send notification
            try:
                from app.services.seller_payout_service import SellerPayoutService
                import asyncio

                payout_service = SellerPayoutService()
                payout_id = await payout_service.create_payout_from_order_async(order_id)
                if payout_id:
                    logger.info(f"✅ Payout {payout_id} created for seller {seller_user_id} - ${seller_revenue_usd:.2f}")
                else:
                    logger.warning(f"⚠️ Failed to create payout for order {order_id} (seller may not have wallet configured)")
            except Exception as e:
                logger.error(f"❌ Error creating payout for order {order_id}: {e}")

            # Send formation automatically to buyer
            if buyer_user_id:
                await send_formation_to_buyer(buyer_user_id, order_id, product_id, payment_id)

        conn.commit()
        return {"ok": True}

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error in IPN handler: {e}")
        raise HTTPException(status_code=500, detail="db error")
    finally:
        if conn:
            put_connection(conn)  # Return connection to pool


async def send_formation_to_buyer(buyer_user_id: int, order_id: str, product_id: str, payment_id: str):
    """Envoie automatiquement la formation à l'acheteur après paiement confirmé"""
    conn = None
    try:
        bot = Bot(token=core_settings.TELEGRAM_BOT_TOKEN)

        # Get product info
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('SELECT title, main_file_url FROM products WHERE product_id = %s', (product_id,))
        product_result = cursor.fetchone()

        if not product_result:
            logger.error(f"Product {product_id} not found for auto delivery")
            conn.commit()
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

        # Download file from B2 and send it with retry logic
        if file_url:
            try:
                # Download from Backblaze B2 to temp location
                local_path = await download_product_file_from_b2(file_url, product_id)

                if local_path and os.path.exists(local_path):
                    # Send the file with library button (WITH RETRY LOGIC)
                    library_keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("📚 Accéder à ma bibliothèque", callback_data='library_menu')
                    ]])

                    file_sent = False
                    last_error = None

                    # Attempt to send file with retries
                    for attempt in range(MAX_RETRIES + 1):
                        try:
                            with open(local_path, 'rb') as file:
                                await bot.send_document(
                                    chat_id=buyer_user_id,
                                    document=file,
                                    caption=f"📚 **{title}**\n\n✅ Téléchargement réussi !\n\n💡 Conservez ce fichier précieusement.\n📖 Vous pouvez aussi le retrouver dans votre bibliothèque.",
                                    parse_mode='Markdown',
                                    reply_markup=library_keyboard,
                                    read_timeout=60,
                                    write_timeout=60
                                )

                            file_sent = True
                            logger.info(f"✅ File sent to user {buyer_user_id} on attempt {attempt + 1}")
                            break  # Success, exit retry loop

                        except Exception as send_error:
                            last_error = send_error
                            logger.warning(f"⚠️ Attempt {attempt + 1}/{MAX_RETRIES + 1} failed to send file to user {buyer_user_id}: {send_error}")

                            if attempt < MAX_RETRIES:
                                delay = RETRY_DELAYS[attempt]
                                logger.info(f"⏳ Retrying in {delay} seconds...")
                                await asyncio.sleep(delay)
                            else:
                                logger.error(f"❌ All {MAX_RETRIES + 1} attempts failed to send file")

                    # If file was sent successfully
                    if file_sent:
                        # Mark as delivered and update download count
                        cursor.execute('''UPDATE orders
                                         SET file_delivered = TRUE,
                                             download_count = download_count + 1
                                         WHERE nowpayments_id = %s''', (payment_id,))
                        conn.commit()

                        logger.info(f"✅ Formation automatically sent to user {buyer_user_id} for order {order_id}")

                    # If all retries failed, send presigned URL as fallback
                    else:
                        logger.error(f"❌ All send attempts failed. Generating presigned URL fallback...")

                        try:
                            # Generate presigned URL (24h expiry)
                            b2_service = B2StorageService()
                            presigned_url = b2_service.get_presigned_url(file_url, expiry_seconds=PRESIGNED_URL_EXPIRY)

                            if presigned_url:
                                fallback_message = f"""⚠️ **Envoi du fichier temporairement indisponible**

📚 **Formation :** {title}
📦 **Commande :** `{order_id}`

🔗 Vous pouvez télécharger votre formation via ce lien sécurisé (valide 24h) :
{presigned_url}

💡 Sauvegardez ce fichier dès que possible.

❓ Problème ? Contactez le support avec votre ID de commande."""

                                await bot.send_message(
                                    chat_id=buyer_user_id,
                                    text=fallback_message,
                                    parse_mode='Markdown',
                                    reply_markup=library_keyboard
                                )

                                logger.info(f"✅ Presigned URL sent to user {buyer_user_id} as fallback")

                                # Mark as partially delivered (via URL)
                                cursor.execute('''UPDATE orders
                                                 SET file_delivered = TRUE,
                                                     download_count = 0
                                                 WHERE nowpayments_id = %s''', (payment_id,))
                                conn.commit()

                            else:
                                raise Exception("Failed to generate presigned URL")

                        except Exception as fallback_error:
                            logger.error(f"❌ Fallback presigned URL generation failed: {fallback_error}")
                            # Last resort: notify support
                            await bot.send_message(
                                chat_id=buyer_user_id,
                                text=f"❌ Erreur technique lors de l'envoi de votre formation.\n\n📦 Commande : `{order_id}`\n\n⚠️ Contactez immédiatement le support avec ce code.",
                                parse_mode='Markdown'
                            )

                            # TODO: Send alert to admin
                            logger.critical(f"🚨 CRITICAL: Failed to deliver file to user {buyer_user_id} for order {order_id} after all retries AND fallback URL failed")

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
                                seller_email_sent = email_service.send_sale_notification_seller(
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
                                if seller_email_sent:
                                    if email_service.smtp_configured:
                                        logger.info(f"📧 ✅ Email vente RÉEL envoyé au vendeur: {email_data['seller_email']}")
                                    else:
                                        logger.warning(f"📧 ⚠️ Email vente SIMULÉ (SMTP non configuré) - Vendeur: {email_data['seller_email']}")

                            # Email à l'acheteur (confirmation d'achat)
                            if email_data['buyer_email']:
                                buyer_email_sent = email_service.send_purchase_confirmation_buyer(
                                    buyer_email=email_data['buyer_email'],
                                    buyer_username=email_data['buyer_username'] or f'User_{buyer_user_id}',
                                    product_title=email_data['product_title'],
                                    product_price_usd=float(email_data['product_price_usd']),
                                    payment_currency=email_data['payment_currency'],
                                    order_id=order_id,
                                    seller_name=email_data['seller_name'] or 'Vendeur'
                                )
                                if buyer_email_sent:
                                    if email_service.smtp_configured:
                                        logger.info(f"📧 ✅ Email confirmation RÉEL envoyé à l'acheteur: {email_data['buyer_email']}")
                                    else:
                                        logger.warning(f"📧 ⚠️ Email confirmation SIMULÉ (SMTP non configuré) - Acheteur: {email_data['buyer_email']}")

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

        conn.commit()

    except (psycopg2.Error, Exception) as e:
        if conn:
            conn.rollback()
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
    finally:
        if conn:
            put_connection(conn)  # Return connection to pool

