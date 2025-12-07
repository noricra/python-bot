"""
IPN Server avec support Webhook Telegram (version corrigée Lifespan)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
import os
import psycopg2
import psycopg2.extras
import logging
import asyncio
import sys

# Ajout pour le path si nécessaire
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application

from app.core import settings as core_settings
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection
from app.core.file_utils import download_product_file_from_b2
from app.services.b2_storage_service import B2StorageService

# --- IMPORTS DU BOT ---
# Nécessaires pour construire le bot ici
from app.integrations.telegram.app_builder import build_application
from bot_mlt import MarketplaceBot

logger = logging.getLogger(__name__)

# Retry configuration
RETRY_DELAYS = [2, 5, 10]
MAX_RETRIES = len(RETRY_DELAYS)
PRESIGNED_URL_EXPIRY = 24 * 3600

# Variable globale
telegram_application: Application = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie (Remplace on_event startup/shutdown)
    Initialise le bot AVANT que le serveur n'accepte des requêtes.
    """
    global telegram_application

    # --- DÉMARRAGE ---
    logger.info("🚀 Initialisation du Bot Telegram dans le lifespan...")
    
    if not core_settings.TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN manquant !")
    else:
        try:
            # 1. Créer le bot et l'application
            bot_instance = MarketplaceBot()
            telegram_application = build_application(bot_instance)
            bot_instance.application = telegram_application
            
            # 2. Initialiser explicitement (CRITIQUE pour éviter l'erreur 500)
            await telegram_application.initialize()
            await telegram_application.start()
            
            # 3. Configurer le Webhook
            webhook_url = f"{core_settings.WEBHOOK_URL}/webhook/telegram"
            await telegram_application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )
            logger.info(f"✅ Telegram webhook configuré sur: {webhook_url}")
            
        except Exception as e:
            logger.error(f"❌ Erreur critique au démarrage du bot: {e}")

    # Rend la main à FastAPI
    yield 

    # --- ARRÊT ---
    logger.info("🛑 Arrêt du Bot Telegram...")
    if telegram_application:
        try:
            await telegram_application.stop()
            await telegram_application.shutdown()
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du bot: {e}")


# Initialisation de l'app avec le lifespan
app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    checks = {
        "status": "healthy",
        "postgres": False,
        "b2_configured": False,
        "telegram_configured": False,
        "webhook_mode": True,
        "bot_ready": telegram_application is not None # Check if bot is actually loaded
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

    checks["b2_configured"] = bool(core_settings.B2_KEY_ID and core_settings.B2_APPLICATION_KEY)
    checks["telegram_configured"] = bool(core_settings.TELEGRAM_BOT_TOKEN)

    all_healthy = all([checks["postgres"], checks["b2_configured"], checks["telegram_configured"]])

    if not all_healthy:
        checks["status"] = "degraded"
        return checks, 503

    return checks


@app.get("/")
async def root():
    return {
        "service": "Uzeur Marketplace Server (Lifespan Mode)",
        "status": "running",
        "bot_status": "active" if telegram_application else "inactive"
    }


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Webhook endpoint pour recevoir les messages Telegram"""
    global telegram_application

    # Cette vérification empêche le crash 500 si le bot a échoué au démarrage
    if telegram_application is None:
        logger.error("❌ Telegram application not initialized (Variable is None)")
        raise HTTPException(status_code=503, detail="Bot not initialized yet")

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_application.bot)
        
        # Traitement asynchrone
        await telegram_application.process_update(update)

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        # On renvoie 200 à Telegram même en cas d'erreur interne pour éviter qu'il ne réessaie en boucle
        return {"ok": False, "error": str(e)}


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not secret or not signature:
        return False
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha512).hexdigest()
    return hmac.compare_digest(mac, signature)


@app.post("/ipn/nowpayments")
async def nowpayments_ipn(request: Request):
    """
    Le reste de votre code IPN reste identique ici...
    (Je n'ai pas copié tout le bloc IPN pour raccourcir, mais gardez votre code existant en dessous)
    """
    # ... GARDEZ TOUT VOTRE CODE IPN EXISTANT ICI ...
    # (Copiez-collez simplement le reste de votre fonction nowpayments_ipn originale)
    return await original_nowpayments_logic(request) # Placeholder pour dire "gardez votre code"

# --- Pour que le copier-coller fonctionne, remettez tout le bloc IPN ci-dessous ---
# (Je remets le début pour que vous puissiez coller la suite de votre fichier original)
    raw = await request.body()
    signature = request.headers.get('x-nowpayments-sig') or request.headers.get('X-Nowpayments-Sig')
    if not verify_signature(core_settings.NOWPAYMENTS_IPN_SECRET or '', raw, signature or ''):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        data = json.loads(raw.decode())
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")
    
    # ... Continuez avec votre logique DB existante ...
    # Assurez-vous juste que 'telegram_application' est bien utilisé si besoin
    # ou recréez 'SimpleBot' comme vous le faisiez, ça marche aussi.
    
    # NOTE: Pour la fonction send_formation_to_buyer, pas de changement nécessaire
    # car elle crée sa propre instance de Bot(token=...) ce qui est thread-safe.