"""
Core Configuration - Streamlined settings without validation logic
"""
import os
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class Config:
    """Streamlined application configuration"""

    # Telegram
    TELEGRAM_TOKEN: Optional[str] = os.getenv("TELEGRAM_TOKEN")
    ADMIN_USER_ID: Optional[int] = int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@domain.com")

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "marketplace_database.db")

    # Payments
    NOWPAYMENTS_API_KEY: Optional[str] = os.getenv("NOWPAYMENTS_API_KEY")
    NOWPAYMENTS_IPN_SECRET: Optional[str] = os.getenv("NOWPAYMENTS_IPN_SECRET")
    IPN_CALLBACK_URL: str = os.getenv("IPN_CALLBACK_URL", "http://localhost:8000/ipn/nowpayments")
    IPN_HOST: str = os.getenv("IPN_HOST", "0.0.0.0")
    IPN_PORT: int = int(os.getenv("IPN_PORT", "8000"))

    # SMTP
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL: Optional[str] = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")

    # Storage
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_FILE_NAME: str = os.getenv("LOG_FILE_NAME", "marketplace.log")
    UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "uploads")

    # Constraints
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    SUPPORTED_FILE_TYPES: List[str] = [
        "pdf", "doc", "docx", "txt", "md", "zip", "rar", "7z",
        "mp4", "avi", "mkv", "mp3", "wav", "jpg", "png", "gif"
    ]

    # Crypto
    SUPPORTED_CURRENCIES: List[str] = ["btc", "eth", "ltc", "bch", "sol"]
    PLATFORM_COMMISSION_RATE: float = float(os.getenv("PLATFORM_COMMISSION_RATE", "0.05"))

    # Limits
    MAX_PRODUCTS_PER_SELLER: int = int(os.getenv("MAX_PRODUCTS_PER_SELLER", "50"))
    MAX_DESCRIPTION_LENGTH: int = int(os.getenv("MAX_DESCRIPTION_LENGTH", "2000"))

    # Language
    DEFAULT_LANGUAGE: str = "fr"

    @classmethod
    def validate_required(cls) -> List[str]:
        """Validate required settings and return missing ones"""
        missing = []
        if not cls.TELEGRAM_TOKEN:
            missing.append("TELEGRAM_TOKEN")
        if not cls.ADMIN_USER_ID:
            missing.append("ADMIN_USER_ID")
        return missing


# Global instance
config = Config()