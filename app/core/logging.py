import logging
import os
from typing import Optional


def configure_logging(settings) -> None:
    """Configure application-wide logging with file and console handlers."""
    # Ensure directories exist (delegates to settings)
    try:
        settings.ensure_directories()
    except Exception:
        # Fallback to local creation if settings has issues
        os.makedirs(getattr(settings, "LOG_DIR", "logs"), exist_ok=True)

    log_file_path = getattr(settings, "LOG_FILE_PATH", os.path.join("logs", "marketplace.log"))

    # Avoid duplicate handlers when reloading in dev
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )

