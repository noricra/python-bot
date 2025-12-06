"""
IPN Server avec support Webhook Telegram et Mini App Auth (Corrigé)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
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

class UploadCompleteRequest(BaseModel):
    object_key: str
    file_name: str
    file_size: int
    user_id: int
    telegram_init_data: str

@app.post("/api/generate-upload-url")
async def generate_upload_url(request: GenerateUploadURLRequest):
    """Étape 1: Le frontend demande une URL d'upload B2 sécurisée"""
    if not verify_telegram_webapp_data(request.telegram_init_data):
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid Init Data")

    try:
        # Génération nom unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        # Nettoyage extension
        ext = request.file_name.split('.')[-1] if '.' in request.file_name else 'bin'

        # Structure: uploads/USER_ID/DATE_UID.ext
        object_key = f"uploads/{request.user_id}/{timestamp}_{unique_id}.{ext}"

        # Appel service B2
        b2 = B2StorageService()
        upload_url = b2.generate_presigned_upload_url(object_key, expires_in=3600)

        if not upload_url:
            raise HTTPException(status_code=500, detail="B2 Presigned URL generation failed")

        return {
            "upload_url": upload_url,
            "object_key": object_key,
            "expires_in": 3600
        }
    except Exception as e:
        logger.error(f"❌ Error generating URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-complete")
async def upload_complete(request: UploadCompleteRequest):
    """Étape 2: Le frontend confirme que l'upload est fini"""
    if not verify_telegram_webapp_data(request.telegram_init_data):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Vérification B2
        b2 = B2StorageService()
        if not b2.file_exists(request.object_key):
            raise HTTPException(status_code=404, detail="File not found on B2 after upload")

        # URL publique (ou privée selon bucket settings) pour référence interne
        b2_url = f"https://s3.{core_settings.B2_REGION}.backblazeb2.com/{core_settings.B2_BUCKET_NAME}/{request.object_key}"

        # Notification utilisateur via Bot
        global telegram_application
        if telegram_application:
            msg_text = (
                f"✅ **Fichier reçu avec succès !**\n\n"
                f"📁 Nom: `{request.file_name}`\n"
                f"📊 Taille: `{request.file_size / (1024*1024):.2f} MB`\n\n"
                f"Je prépare la suite..."
            )
            await telegram_application.bot.send_message(
                chat_id=request.user_id,
                text=msg_text,
                parse_mode='Markdown'
            )

            # --- ICI : LOGIQUE DE SUITE (Ex: FSM State Transition) ---
            # Vous pouvez déclencher une fonction du bot pour passer à l'étape "Set Price"
            # context.user_data['temp_file_url'] = b2_url ...

        return {"status": "success", "b2_url": b2_url}

    except Exception as e:
        logger.error(f"❌ Error completing upload: {e}")
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
