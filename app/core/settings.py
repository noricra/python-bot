import os
from typing import List, Dict, Optional

try:
    # Optional; present in this project
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class Settings:
    """Central application settings loaded from environment with safe defaults."""

    def __init__(self) -> None:
        # Telegram / Admin
        self.TELEGRAM_TOKEN: Optional[str] = os.getenv("TELEGRAM_TOKEN")
        self.ADMIN_USER_ID: Optional[int] = (
            int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
        )
        self.ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@votre-domaine.com")

        # Telegram networking & scaling
        self.TELEGRAM_POOL_SIZE: int = int(os.getenv("TELEGRAM_POOL_SIZE", "50"))
        self.TELEGRAM_CONNECT_TIMEOUT: float = float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "5.0"))
        self.TELEGRAM_READ_TIMEOUT: float = float(os.getenv("TELEGRAM_READ_TIMEOUT", "30.0"))
        self.TELEGRAM_WRITE_TIMEOUT: float = float(os.getenv("TELEGRAM_WRITE_TIMEOUT", "30.0"))
        self.TELEGRAM_POOL_TIMEOUT: float = float(os.getenv("TELEGRAM_POOL_TIMEOUT", "5.0"))
        self.TELEGRAM_PROXY_URL: Optional[str] = os.getenv("TELEGRAM_PROXY_URL")
        self.TELEGRAM_BASE_URL: Optional[str] = os.getenv("TELEGRAM_BASE_URL")
        self.TELEGRAM_CONCURRENT_UPDATES: bool = os.getenv("TELEGRAM_CONCURRENT_UPDATES", "true").lower() == "true"
        self.TELEGRAM_RATE_LIMITER: bool = os.getenv("TELEGRAM_RATE_LIMITER", "true").lower() == "true"

        # SMTP
        self.SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_EMAIL: Optional[str] = os.getenv("SMTP_EMAIL")
        self.SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")

        # Payments / NOWPayments
        self.NOWPAYMENTS_API_KEY: Optional[str] = os.getenv("NOWPAYMENTS_API_KEY")
        self.NOWPAYMENTS_IPN_SECRET: Optional[str] = os.getenv("NOWPAYMENTS_IPN_SECRET")
        # Public IPN callback URL (used when creating payments)
        self.IPN_CALLBACK_URL: Optional[str] = os.getenv(
            "IPN_CALLBACK_URL", "http://localhost:8000/ipn/nowpayments"
        )

        # IPN server settings
        self.IPN_HOST: str = os.getenv("IPN_HOST", "0.0.0.0")
        self.IPN_PORT: int = int(os.getenv("IPN_PORT", "8000"))

        # Webhook mode (optional)
        self.TELEGRAM_USE_WEBHOOK: bool = os.getenv("TELEGRAM_USE_WEBHOOK", "false").lower() == "true"
        self.TELEGRAM_WEBHOOK_URL: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")
        self.TELEGRAM_WEBHOOK_PORT: int = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8443"))
        self.TELEGRAM_WEBHOOK_LISTEN: str = os.getenv("TELEGRAM_WEBHOOK_LISTEN", "0.0.0.0")
        self.TELEGRAM_WEBHOOK_PATH: str = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook")

        # Storage and paths
        self.LOG_DIR: str = os.getenv("LOG_DIR", "logs")
        self.LOG_FILE_NAME: str = os.getenv("LOG_FILE_NAME", "marketplace.log")
        self.UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "uploads")
        self.WALLETS_DIR: str = os.getenv("WALLETS_DIR", "wallets")
        self.DATABASE_PATH: str = os.getenv("DATABASE_PATH", "marketplace_database.db")

        # Files constraints
        self.MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
        self.SUPPORTED_FILE_TYPES: List[str] = (
            os.getenv("SUPPORTED_FILE_TYPES", ".pdf,.zip,.rar,.mp4,.txt,.docx")
            .split(",")
        )

        # Commissions
        self.PLATFORM_COMMISSION_RATE: float = float(
            os.getenv("PLATFORM_COMMISSION_RATE", "0.05")
        )
        self.PARTNER_COMMISSION_RATE: float = float(
            os.getenv("PARTNER_COMMISSION_RATE", "0.10")
        )

        # Crypto marketplace config
        self.MARKETPLACE_CONFIG: Dict[str, object] = {
            "supported_payment_cryptos": [
                "btc",
                "eth",
                "usdt",
                "usdc",
                "bnb",
                "sol",
                "ltc",
                "xrp",
            ],
            "platform_commission_rate": self.PLATFORM_COMMISSION_RATE,
            "min_payout_amount": float(os.getenv("MIN_PAYOUT_AMOUNT_SOL", "0.1")),
        }

    @property
    def LOG_FILE_PATH(self) -> str:
        return os.path.join(self.LOG_DIR, self.LOG_FILE_NAME)

    def ensure_directories(self) -> None:
        os.makedirs(self.LOG_DIR, exist_ok=True)
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)
        os.makedirs(self.WALLETS_DIR, exist_ok=True)


# Singleton-like settings instance
settings = Settings()

