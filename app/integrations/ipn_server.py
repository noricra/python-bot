"""
IPN Server avec support Webhook Telegram et Mini App Auth (Corrigé)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import hmac
import hashlib
import json
import os
import logging
import asyncio
import sys
import uuid
# IMPORT CRITIQUE POUR LE FIX 401
from urllib.parse import parse_qsl

# Gestion du path pour les imports relatifs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import Bot, Update
from telegram.ext import Application

from app.core import settings as core_settings
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
from app.core.file_utils import get_b2_presigned_url
from app.services.b2_storage_service import B2StorageService

# --- IMPORTS DU BOT ---
from app.integrations.telegram.app_builder import build_application
from bot_mlt import MarketplaceBot

# Configuration Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variable globale pour l'application Telegram
telegram_application: Optional[Application] = None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. LIFESPAN (Démarrage/Arrêt)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie.
    Initialise le bot Telegram AVANT que le serveur n'accepte des requêtes.
    """
    global telegram_application

    logger.info("🚀 Initialisation du Bot Telegram dans le lifespan...")

    if not core_settings.TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN manquant !")
    else:
        try:
            # 1. Créer le bot et l'application
            bot_instance = MarketplaceBot()
            telegram_application = build_application(bot_instance)
            bot_instance.application = telegram_application

            # 2. Initialiser explicitement
            await telegram_application.initialize()
            await telegram_application.start()

            # 3. Configurer Webhook OU Polling
            webhook_url = core_settings.WEBHOOK_URL
            # On active le webhook seulement si c'est une URL https distante (pas localhost)
            use_webhook = webhook_url and 'localhost' not in webhook_url and webhook_url.startswith('https')

            if use_webhook:
                webhook_full_url = f"{webhook_url}/webhook/telegram"
                await telegram_application.bot.set_webhook(
                    url=webhook_full_url,
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES
                )
                logger.info(f"✅ Telegram webhook configuré sur: {webhook_full_url}")
            else:
                await telegram_application.bot.delete_webhook(drop_pending_updates=True)
                logger.info("🔄 Mode polling activé (développement local)")
                asyncio.create_task(telegram_application.updater.start_polling(
                    poll_interval=1.0,
                    timeout=10,
                    drop_pending_updates=True
                ))

        except Exception as e:
            logger.error(f"❌ Erreur critique au démarrage du bot: {e}")

    yield # Le serveur tourne ici

    # Arrêt propre
    logger.info("🛑 Arrêt du Bot Telegram...")
    if telegram_application:
        try:
            await telegram_application.stop()
            await telegram_application.shutdown()
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du bot: {e}")


app = FastAPI(lifespan=lifespan)

# Configuration CORS pour Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web.telegram.org",
        "https://oauth.telegram.org"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Montage des fichiers statiques pour la Mini App (JS/CSS)
# Assurez-vous que le dossier existe : app/integrations/telegram/static
app.mount("/static", StaticFiles(directory="app/integrations/telegram/static"), name="static")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. ROUTINES DE BASE & WEBHOOK TELEGRAM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "postgres": False,
        "bot_ready": telegram_application is not None
    }
    try:
        conn = get_postgresql_connection()
        put_connection(conn)
        checks["postgres"] = True
    except Exception:
        checks["postgres"] = False

    if not checks["postgres"]:
        return checks, 503
    return checks

@app.get("/")
async def root():
    return {"service": "Uzeur Marketplace Server", "status": "running"}

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Réception des messages Telegram (si mode Webhook actif)"""
    global telegram_application
    if telegram_application is None:
        # Évite le crash 500, renvoie 200 pour que Telegram arrête de réessayer
        logger.error("❌ Bot non initialisé")
        return {"ok": True}

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_application.bot)
        await telegram_application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return {"ok": False}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. AUTHENTIFICATION MINI APP (CORRIGÉE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def verify_telegram_webapp_data(init_data: str) -> bool:
    """
    Vérifie l'intégrité des données reçues de la WebApp Telegram.
    Utilise parse_qsl pour gérer correctement le décodage URL.
    """
    # SKIP AUTH EN DEV LOCAL
    webapp_url = os.getenv('WEBAPP_URL', '')
    if 'localhost' in webapp_url or '127.0.0.1' in webapp_url:
        logger.warning("⚠️ DEV MODE: Skipping WebApp auth")
        return True

    if not init_data:
        return False

    try:
        # 1. Parsing correct des données URL-encodées
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))

        # 2. Extraction du hash reçu
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return False

        # 3. Vérification expiration (24h max)
        auth_date = int(parsed_data.get('auth_date', 0))
        if (datetime.now().timestamp() - auth_date) > 86400:
             logger.warning("⚠️ Telegram WebApp data expired")
             return False

        # 4. Reconstruction de la chaîne de vérification
        # Format: key=value triés par clé, séparés par \n
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # 5. Calcul HMAC-SHA256
        secret_key = hmac.new(
            "WebAppData".encode(),
            core_settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # 6. Comparaison
        is_valid = calculated_hash == received_hash

        if is_valid:
            logger.info(f"✅ WebApp Auth Success User: {parsed_data.get('user')}")
        else:
            logger.warning(f"❌ WebApp Auth Failed. Calc: {calculated_hash} != Recv: {received_hash}")

        return is_valid

    except Exception as e:
        logger.error(f"❌ Auth Exception: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. API MINI APP (UPLOAD FLOW)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class GenerateUploadURLRequest(BaseModel):
    file_name: str
    file_type: str
    user_id: int
    telegram_init_data: str

class GetB2UploadURLRequest(BaseModel):
    object_key: str
    content_type: str
    user_id: int
    telegram_init_data: str

class UploadCompleteRequest(BaseModel):
    object_key: str
    file_name: str
    file_size: int
    user_id: int
    telegram_init_data: str
    preview_url: Optional[str] = None  # URL aperçu PDF généré côté client

class ClientErrorRequest(BaseModel):
    error_type: str
    details: dict
    user_id: int

@app.post("/api/generate-upload-url")
async def generate_upload_url(request: GenerateUploadURLRequest):
    """Étape 1: Le frontend demande une URL d'upload B2 Native API (CORS-compatible)"""
    if not verify_telegram_webapp_data(request.telegram_init_data):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid Init Data")

    try:
        from app.core.utils import generate_product_id
        from app.core.file_validation import validate_file_extension

        # 🔒 SÉCURITÉ: Valider l'extension AVANT tout traitement
        is_valid, error_msg = validate_file_extension(request.file_name)
        if not is_valid:
            logger.warning(f"🚫 MINIAPP: File rejected for user {request.user_id}: {request.file_name} - {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # Générer product_id AVANT l'upload (critique pour chemins cohérents)
        product_id = generate_product_id()
        logger.info(f"🆔 Generated product_id BEFORE upload: {product_id} for user {request.user_id}")

        # Stocker product_id dans user_state pour upload-complete
        global telegram_application
        if telegram_application:
            bot_instance = telegram_application.bot_data.get('bot_instance')
            if bot_instance:
                user_state = bot_instance.get_user_state(request.user_id)
                product_data = user_state.get('product_data', {})
                product_data['product_id'] = product_id  # ✅ Stocké pour plus tard
                user_state['product_data'] = product_data
                logger.info(f"✅ product_id stored in user_state: {product_id}")

        # Nettoyage du filename (garder l'extension)
        ext = request.file_name.split('.')[-1] if '.' in request.file_name else 'bin'
        clean_filename = f"main_file.{ext}"

        # ✅ NOUVELLE STRUCTURE: products/seller_id/product_id/main_file.ext
        object_key = f"products/{request.user_id}/{product_id}/{clean_filename}"

        # Appel service B2 Native API
        b2 = B2StorageService()
        upload_data = b2.get_native_upload_url(
            object_key,
            content_type=request.file_type or 'application/octet-stream'
        )

        if not upload_data:
            logger.error(
                f"❌ B2 Native upload URL generation failed\n"
                f"   User: {request.user_id}\n"
                f"   Product ID: {product_id}\n"
                f"   File: {request.file_name}\n"
                f"   Type: {request.file_type}\n"
                f"   Object key: {object_key}"
            )
            raise HTTPException(status_code=500, detail="B2 Upload URL generation failed")

        logger.info(f"✅ Generated B2 Native upload URL: {object_key}")

        return {
            "upload_url": upload_data['upload_url'],
            "authorization_token": upload_data['authorization_token'],
            "object_key": upload_data['object_key'],
            "content_type": upload_data['content_type'],
            "product_id": product_id  # ✅ Retourné au frontend pour preview
        }
    except Exception as e:
        logger.error(f"❌ Error generating URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/get-b2-upload-url")
async def get_b2_upload_url(request: GetB2UploadURLRequest):
    """Obtenir URL B2 pour un chemin spécifique (preview, etc.)"""
    if not verify_telegram_webapp_data(request.telegram_init_data):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Appel service B2 pour ce chemin spécifique
        b2 = B2StorageService()
        upload_data = b2.get_native_upload_url(
            request.object_key,
            content_type=request.content_type
        )

        if not upload_data:
            logger.error(f"❌ B2 upload URL failed for path: {request.object_key}")
            raise HTTPException(status_code=500, detail="B2 Upload URL failed")

        logger.info(f"✅ B2 upload URL generated for path: {request.object_key}")

        return {
            "upload_url": upload_data['upload_url'],
            "authorization_token": upload_data['authorization_token'],
            "object_key": upload_data['object_key'],
            "content_type": upload_data['content_type']
        }
    except Exception as e:
        logger.error(f"❌ Error getting B2 URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/log-client-error")
async def log_client_error(request: ClientErrorRequest):
    """Endpoint pour recevoir et logger les erreurs JavaScript côté client"""
    logger.error(
        f"❌ CLIENT ERROR - User {request.user_id} - Type: {request.error_type}\n"
        f"   Details: {json.dumps(request.details, indent=2)}"
    )
    return {"status": "logged"}

@app.post("/api/upload-complete")
async def upload_complete(request: UploadCompleteRequest):
    """Étape 2: Le frontend confirme que l'upload est fini - Création du produit"""
    logger.info(f"🔵 START upload-complete - User: {request.user_id}, File: {request.file_name}, Size: {request.file_size}")

    if not verify_telegram_webapp_data(request.telegram_init_data):
        logger.error(f"❌ Auth failed for user {request.user_id}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info(f"✅ Auth OK for user {request.user_id}")

    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        # Vérification B2
        logger.info(f"🔍 Checking B2 file existence: {request.object_key}")
        b2 = B2StorageService()
        if not b2.file_exists(request.object_key):
            logger.error(f"❌ File not found on B2: {request.object_key}")
            raise HTTPException(status_code=404, detail="File not found on B2 after upload")

        logger.info(f"✅ B2 file exists: {request.object_key}")

        # URL du fichier sur B2
        b2_url = f"{core_settings.B2_ENDPOINT}/{core_settings.B2_BUCKET_NAME}/{request.object_key}"
        logger.info(f"📦 B2 URL constructed: {b2_url}")

        global telegram_application
        logger.info(f"🤖 telegram_application exists: {telegram_application is not None}")

        if telegram_application:
            bot_instance = telegram_application.bot_data.get('bot_instance')
            logger.info(f"🤖 bot_instance exists: {bot_instance is not None}")

            if bot_instance:
                # Récupérer product_data qui contient déjà titre, description, prix, etc.
                logger.info(f"📊 Getting user state for user {request.user_id}")
                user_state = bot_instance.get_user_state(request.user_id)
                product_data = user_state.get('product_data', {})
                lang = user_state.get('lang', 'fr')

                logger.info(f"📦 Retrieved product_data: {product_data}")
                logger.info(f"🌐 Language: {lang}")

                # ✅ Utiliser product_id PRÉ-GÉNÉRÉ (stocké dans generate-upload-url)
                product_id = product_data.get('product_id')

                if not product_id:
                    logger.error(f"❌ product_id not found in product_data! This should never happen.")
                    raise HTTPException(status_code=500, detail="Product ID not found in state")

                logger.info(f"🆔 Using pre-generated product_id: {product_id}")

                # Ajouter les infos du fichier uploadé
                product_data['file_name'] = request.file_name
                product_data['file_size'] = request.file_size
                product_data['main_file_url'] = b2_url
                product_data['seller_id'] = request.user_id

                logger.info(f"📝 Updated product_data with file info: file_name={request.file_name}, file_size={request.file_size}")

                # Ajouter preview_url si fourni (PDF uniquement)
                if request.preview_url:
                    product_data['preview_url'] = request.preview_url
                    logger.info(f"📸 Preview URL received: {request.preview_url}")

                # ✅ Finaliser la création du produit avec product_id existant
                logger.info(f"🔨 Calling create_product with pre-generated ID: {product_id}")
                returned_product_id = bot_instance.create_product(product_data)
                logger.info(f"🎯 create_product returned: {returned_product_id}")

                # Vérifier que l'ID retourné correspond bien
                if returned_product_id != product_id:
                    logger.warning(f"⚠️ Mismatch: Expected {product_id}, got {returned_product_id}")
                    product_id = returned_product_id  # Utiliser celui retourné

                if product_id:
                    logger.info(f"✅ Product created successfully: {product_id}")

                    # Réinitialiser l'état utilisateur
                    logger.info(f"🔄 Resetting user state for {request.user_id}")
                    bot_instance.reset_user_state_preserve_login(request.user_id)

                    # Envoyer emails de notification
                    try:
                        from app.core.email_service import EmailService
                        from app.domain.repositories.user_repo import UserRepository
                        from app.domain.repositories.product_repo import ProductRepository

                        email_service = EmailService()
                        user_repo = UserRepository()
                        product_repo = ProductRepository()

                        user_data = user_repo.get_user(request.user_id)

                        if user_data and user_data.get('email'):
                            await email_service.send_product_added_email(
                                to_email=user_data['email'],
                                seller_name=user_data.get('seller_name', 'Vendeur'),
                                product_title=product_data['title'],
                                product_price=f"{product_data['price_usd']:.2f}",
                                product_id=product_id
                            )

                            # Email premier produit si applicable
                            total_products = product_repo.count_products_by_seller(request.user_id)
                            if total_products == 1:
                                await email_service.send_first_product_published_notification(
                                    to_email=user_data['email'],
                                    seller_name=user_data.get('seller_name', 'Vendeur'),
                                    product_title=product_data['title'],
                                    product_price=product_data['price_usd']
                                )
                    except Exception as e:
                        logger.error(f"Erreur envoi emails produit: {e}")

                    # Message de succès
                    success_msg = f"✅ **Produit créé avec succès!**\n\n**ID:** {product_id}\n**Titre:** {product_data['title']}\n**Prix:** ${product_data['price_usd']:.2f}"
                    logger.info(f"💬 Preparing success message: {success_msg}")

                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏪 Dashboard" if lang == 'en' else "🏪 Dashboard", callback_data='seller_dashboard'),
                        InlineKeyboardButton("📦 Mes produits" if lang == 'fr' else "📦 My Products", callback_data='my_products')
                    ]])

                    logger.info(f"📤 Sending Telegram message to {request.user_id}")
                    await telegram_application.bot.send_message(
                        chat_id=request.user_id,
                        text=success_msg,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                    logger.info(f"✅ Telegram message sent successfully to {request.user_id}")
                else:
                    logger.error(f"❌ create_product returned None for user {request.user_id}")
                    # Erreur création produit
                    await telegram_application.bot.send_message(
                        chat_id=request.user_id,
                        text="❌ Erreur lors de la création du produit"
                    )
            else:
                logger.error(f"❌ bot_instance is None!")
        else:
            logger.error(f"❌ telegram_application is None!")

        logger.info(f"🎉 END upload-complete - Success!")
        return {"status": "success", "product_id": product_id if 'product_id' in locals() else None}

    except Exception as e:
        logger.error(f"❌ Error completing upload: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. IPN NOWPAYMENTS (PAIEMENTS)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def verify_ipn_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not secret or not signature:
        return False
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha512).hexdigest()
    return hmac.compare_digest(mac, signature)

async def send_formation_to_buyer(buyer_user_id: int, order_id: str, product_id: str):
    """Logique métier: Délivre le fichier acheté"""
    from app.domain.repositories.product_repo import ProductRepository

    repo = ProductRepository()
    product = repo.get_product_by_id(product_id)

    if not product or not product.get('main_file_url'):
        logger.error(f"❌ Produit introuvable ou sans fichier: {product_id}")
        return False

    # Génération lien temporaire de téléchargement (24h)
    download_link = get_b2_presigned_url(product['main_file_url'], expires_in=86400)

    msg = (
        f"🎉 **Paiement confirmé !** (Commande #{order_id})\n\n"
        f"Voici votre formation : **{product.get('title')}**\n"
        f"🔗 [Télécharger ici]({download_link})\n\n"
        f"⚠️ Lien valide 24h."
    )

    global telegram_application
    # Utilise le bot global s'il est là, sinon une instance temporaire
    bot = telegram_application.bot if telegram_application else Bot(core_settings.TELEGRAM_BOT_TOKEN)

    try:
        await bot.send_message(chat_id=buyer_user_id, text=msg, parse_mode='Markdown')
        logger.info(f"✅ Fichier envoyé à {buyer_user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Echec envoi fichier: {e}")
        return False

@app.post("/ipn/nowpayments")
async def nowpayments_ipn(request: Request):
    """Réception des notifications de paiement NowPayments"""
    # 1. Vérification Signature
    raw_body = await request.body()
    signature = request.headers.get('x-nowpayments-sig')

    if not verify_ipn_signature(core_settings.NOWPAYMENTS_IPN_SECRET, raw_body, signature):
        logger.warning("⚠️ IPN Invalid Signature")
        raise HTTPException(status_code=401, detail="Invalid Signature")

    try:
        data = json.loads(raw_body.decode())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 2. Analyse du statut
    payment_status = data.get('payment_status')
    order_id = data.get('order_id') # ID interne
    payment_id = data.get('payment_id') # ID NowPayments

    logger.info(f"💰 IPN reçu: Order {order_id} - Status {payment_status}")

    # On ne traite que les succès
    if payment_status not in ['finished', 'confirmed']:
        return {"status": "ignored", "reason": f"Status is {payment_status}"}

    # 3. Mise à jour Base de Données
    conn = get_postgresql_connection()
    try:
        cursor = conn.cursor()

        # Vérifier si déjà traité
        cursor.execute("SELECT status, buyer_id, product_id FROM orders WHERE order_id = %s", (order_id,))
        row = cursor.fetchone()

        if not row:
            logger.error(f"❌ Order {order_id} not found in DB")
            return {"status": "error", "message": "Order not found"}

        current_status, buyer_id, product_id = row

        if current_status == 'completed':
            logger.info(f"ℹ️ Commande {order_id} déjà complétée")
            return {"status": "ok", "message": "Already completed"}

        # Update Status
        cursor.execute("""
            UPDATE orders
            SET status = 'completed',
                payment_id = %s,
                updated_at = NOW()
            WHERE order_id = %s
        """, (payment_id, order_id))

        conn.commit()

        # 4. Livraison du produit
        await send_formation_to_buyer(buyer_id, order_id, product_id)

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ DB Error processing IPN: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        put_connection(conn)

    return {"status": "ok"}
