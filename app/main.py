import logging

from app.core import settings as core_settings, configure_logging
from app.integrations.telegram.app_builder import build_application
from bot_mlt import MarketplaceBot


def main() -> None:
    configure_logging(core_settings)
    if not core_settings.TELEGRAM_TOKEN:
        logging.getLogger(__name__).error("❌ TELEGRAM_TOKEN manquant dans .env")
        return
    bot = MarketplaceBot()
    app = build_application(bot)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

