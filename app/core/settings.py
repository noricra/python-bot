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

        # SMTP
        self.SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_EMAIL: Optional[str] = os.getenv("SMTP_EMAIL")
        self.SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")

        # Payments / NOWPayments
        self.NOWPAYMENTS_API_KEY: Optional[str] = os.getenv("NOWPAYMENTS_API_KEY")
        self.NOWPAYMENTS_IPN_SECRET: Optional[str] = os.getenv("NOWPAYMENTS_IPN_SECRET")

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

