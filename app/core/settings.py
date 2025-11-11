import os
from typing import List, Dict, Optional


def get_absolute_path(relative_path: str) -> str:
    """
    Convert relative path to absolute path based on project root.

    Args:
        relative_path: Relative path (e.g., 'data/product_images/...')

    Returns:
        Absolute path
    """
    if not relative_path:
        return None

    # If already absolute, return as-is
    if os.path.isabs(relative_path):
        return relative_path

    # Get project root (2 levels up from this file)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    # Join with project root
    absolute_path = os.path.join(project_root, relative_path)

    return absolute_path

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
        self.TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
        self.TELEGRAM_TOKEN: Optional[str] = self.TELEGRAM_BOT_TOKEN  # Compatibility
        self.ADMIN_USER_ID: Optional[int] = (
            int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
        )

        # SMTP (used by email_service.py)
        self.SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_EMAIL")
        self.SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.FROM_EMAIL: str = os.getenv("FROM_EMAIL", self.SMTP_USERNAME or "noreply@marketplace.com")

        # Payments / NOWPayments
        self.NOWPAYMENTS_API_KEY: Optional[str] = os.getenv("NOWPAYMENTS_API_KEY")
        self.NOWPAYMENTS_IPN_SECRET: Optional[str] = os.getenv("NOWPAYMENTS_IPN_SECRET")
        self.IPN_CALLBACK_URL: Optional[str] = os.getenv(
            "IPN_CALLBACK_URL", "http://localhost:8000/ipn/nowpayments"
        )

        # Platform commission (2.78%)
        self.PLATFORM_COMMISSION_PERCENT: float = float(os.getenv("PLATFORM_COMMISSION_PERCENT", "2.78"))

        # IPN server settings
        self.IPN_HOST: str = os.getenv("IPN_HOST", "0.0.0.0")
        # Railway uses PORT, but allow IPN_PORT for local dev
        self.IPN_PORT: int = int(os.getenv("PORT") or os.getenv("IPN_PORT", "8000"))

        # Backblaze B2 Object Storage
        self.B2_KEY_ID: Optional[str] = os.getenv("B2_KEY_ID")
        self.B2_APPLICATION_KEY: Optional[str] = os.getenv("B2_APPLICATION_KEY")
        self.B2_BUCKET_NAME: str = os.getenv("B2_BUCKET_NAME", "uzeur-marketplace")
        self.B2_ENDPOINT: str = os.getenv("B2_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")

        # Storage and paths
        self.UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "uploads")  # Local temp storage for images
        # Product files stored on Backblaze B2, only cover images kept locally

        # Admin Configuration
        self.ADMIN_USER_IDS = [int(x.strip()) for x in os.getenv('ADMIN_USER_IDS', '123456789').split(',') if x.strip()]

        # Categories configuration (used by buy_handlers.py)
        self.DEFAULT_CATEGORIES: List[tuple] = [
            ('Finance & Crypto', 'Formations trading, blockchain, DeFi', '💰'),
            ('Marketing Digital', 'SEO, publicité, réseaux sociaux', '📈'),
            ('Développement', 'Programming, web dev, apps', '💻'),
            ('Design & Créatif', 'Graphisme, vidéo, arts', '🎨'),
            ('Business', 'Entrepreneuriat, management', '📊'),
            ('Formation Pro', 'Certifications, compétences', '🎓'),
            ('Outils & Tech', 'Logiciels, automatisation', '🔧')
        ]

        # Crypto display configuration (used by buy_handlers.py for payment crypto selection)
        self.CRYPTO_DISPLAY_INFO: Dict[str, tuple] = {
            'btc': ('₿ Bitcoin', '⚡ 10-30 min'),
            'eth': ('⟠ Ethereum', '⚡ 5-15 min'),
            'usdt': ('₮ Tether USDT', '⚡ 5-10 min'),
            'usdc': ('🟢 USD Coin', '⚡ 5-10 min'),
            'bnb': ('🟡 BNB', '⚡ 2-5 min'),
            'sol': ('◎ Solana', '⚡ 1-3 min'),
            'ltc': ('Ł Litecoin', '⚡ 10-20 min'),
            'xrp': ('◈ XRP', '⚡ 3-5 min')
        }

        # File handling constants (used by file_utils.py)
        self.ALLOWED_FILENAME_CHARS: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"

        # State management constants (used by bot_mlt.py for clearing states)
        self.CONFLICTING_STATES: List[str] = [
            'waiting_for_product_id', 'adding_product', 'editing_product',
            'editing_product_price', 'editing_product_title', 'editing_product_description',
            'editing_seller_name', 'editing_seller_bio', 'creating_seller',
            'editing_settings', 'searching_user', 'searching_product',
            'suspending_product', 'suspending_user', 'restoring_user', 'admin_search_user',
            'admin_search_product', 'admin_suspend_product'
        ]

    @property
    def LOG_FILE_PATH(self) -> str:
        """Kept for backward compatibility even if LOG_DIR/LOG_FILE_NAME removed"""
        log_dir = os.getenv("LOG_DIR", "logs")
        log_file = os.getenv("LOG_FILE_NAME", "marketplace.log")
        return os.path.join(log_dir, log_file)

    def ensure_directories(self) -> None:
        """Ensure required directories exist"""
        log_dir = os.getenv("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)


# Singleton-like settings instance
settings = Settings()
