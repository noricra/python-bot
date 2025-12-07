#!/usr/bin/env python3
"""
Main entry point simplifié
Tout le lifecycle du Bot est maintenant géré dans app/integrations/ipn_server.py
"""
import logging
import sys
import os
import uvicorn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import settings as core_settings, configure_logging
# On importe juste l'app FastAPI qui contient déjà le lifespan configuré
from app.integrations.ipn_server import app as fastapi_app

def main() -> None:
    configure_logging(core_settings)
    
    host = core_settings.IPN_HOST
    port = core_settings.IPN_PORT
    
    logging.getLogger(__name__).info(f"🚀 Starting Unified Server (Web + Bot) on {host}:{port}")

    # Plus besoin de setup_telegram_webhook ici, c'est géré automatiquement par le lifespan
    
    uvicorn.run(
        app=fastapi_app,
        host=host,
        port=port,
        log_level="info",
        # workers=1  <-- Important: Gardez 1 worker si vous utilisez des variables globales pour le bot
    )

if __name__ == "__main__":
    main()
