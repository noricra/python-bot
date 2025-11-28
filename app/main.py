#!/usr/bin/env python3
"""
Main entry point avec WEBHOOK (résout le conflit Telegram)

Différences avec main.py:
- Utilise webhook au lieu de polling
- Pas de threading, tout dans FastAPI
- Pas de conflit multi-instances
"""
import logging
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import settings as core_settings, configure_logging
from app.integrations.telegram.app_builder import build_application
from bot_mlt import MarketplaceBot


def main() -> None:
    configure_logging(core_settings)

    if not core_settings.TELEGRAM_TOKEN:
        logging.getLogger(__name__).error("❌ TELEGRAM_TOKEN manquant dans .env")
        return

    # Créer le bot et l'application Telegram
    bot = MarketplaceBot()
    telegram_app = build_application(bot)
    bot.application = telegram_app

    # Configurer le webhook Telegram
    async def setup_webhook():
        webhook_url = f"{core_settings.WEBHOOK_URL}/webhook/telegram"
        try:
            await telegram_app.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )
            logging.getLogger(__name__).info(f"✅ Telegram webhook configured: {webhook_url}")
        except Exception as e:
            logging.getLogger(__name__).error(f"❌ Failed to set webhook: {e}")

    # Exécuter le setup du webhook
    asyncio.run(setup_webhook())

    # Démarrer le serveur FastAPI (IPN + Webhook Telegram combinés)
    import uvicorn
    from app.integrations.ipn_server_webhook import app as fastapi_app, setup_telegram_webhook

    # Injecter l'app Telegram dans le serveur FastAPI
    setup_telegram_webhook(telegram_app)

    logging.getLogger(__name__).info(f"🚀 Starting server on {core_settings.IPN_HOST}:{core_settings.IPN_PORT}")

    uvicorn.run(
        app=fastapi_app,
        host=core_settings.IPN_HOST,
        port=core_settings.IPN_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
