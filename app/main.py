import logging

import asyncio
import threading
from app.core import settings as core_settings, configure_logging
from app.integrations.telegram.app_builder import build_application
from bot_mlt import MarketplaceBot


def main() -> None:
    configure_logging(core_settings)
    if not core_settings.TELEGRAM_TOKEN:
        logging.getLogger(__name__).error("❌ TELEGRAM_TOKEN manquant dans .env")
        return

    # Démarrer le serveur IPN FastAPI en arrière-plan (uvicorn)
    def run_ipn_server():
        import uvicorn
        from app.integrations import ipn_server
        uvicorn.run(
            app=ipn_server.app,
            host=core_settings.IPN_HOST,
            port=core_settings.IPN_PORT,
            log_level="info",
        )

    threading.Thread(target=run_ipn_server, daemon=True).start()
    bot = MarketplaceBot()
    app = build_application(bot)
    if getattr(core_settings, "TELEGRAM_USE_WEBHOOK", False) and core_settings.TELEGRAM_WEBHOOK_URL:
        # Webhook mode for better scalability
        app.run_webhook(
            listen=core_settings.TELEGRAM_WEBHOOK_LISTEN,
            port=core_settings.TELEGRAM_WEBHOOK_PORT,
            url_path=core_settings.TELEGRAM_WEBHOOK_PATH.strip("/"),
            webhook_url=core_settings.TELEGRAM_WEBHOOK_URL.rstrip("/") + "/" + core_settings.TELEGRAM_WEBHOOK_PATH.strip("/"),
            drop_pending_updates=True,
        )
    else:
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

