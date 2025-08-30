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
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

