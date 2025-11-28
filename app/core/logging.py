"""
Logging configuration optimisée pour Railway

Changements par rapport à logging.py:
- StreamHandler utilise explicitement sys.stdout (au lieu de stderr)
- Railway affichera correctement les niveaux de log (INFO = info, ERROR = error)
- Logs structurés avec timestamps ISO8601 pour Railway
"""
import logging
import sys
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

    # StreamHandler avec stdout explicite (pas stderr)
    # Cela permet à Railway de différencier INFO vs ERROR correctement
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    # File handler (reste inchangé)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            file_handler,
            console_handler  # ✅ Utilise stdout au lieu de stderr par défaut
        ]
    )

    # Réduire la verbosité de httpx (optionnel)
    # httpx log chaque requête HTTP en INFO, ce qui peut être trop verbeux
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Réduire la verbosité de telegram (optionnel)
    logging.getLogger("telegram").setLevel(logging.WARNING)
