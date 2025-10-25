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
        # Project root directory (absolute path to bot root)
        self.PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        # Telegram / Admin
        self.TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
        self.TELEGRAM_TOKEN: Optional[str] = self.TELEGRAM_BOT_TOKEN  # Compatibility
        self.ADMIN_USER_ID: Optional[int] = (
            int(os.getenv("ADMIN_USER_ID")) if os.getenv("ADMIN_USER_ID") else None
        )
        self.ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@marketplace.com")

        # SMTP
        self.SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_EMAIL")  # For authentication (support both env var names)
        self.SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.FROM_EMAIL: str = os.getenv("FROM_EMAIL", self.SMTP_USERNAME or "noreply@marketplace.com")

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

        # Storage and paths
        self.LOG_DIR: str = os.getenv("LOG_DIR", "logs")
        self.LOG_FILE_NAME: str = os.getenv("LOG_FILE_NAME", "marketplace.log")
        self.UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "uploads")
        self.WALLETS_DIR: str = os.getenv("WALLETS_DIR", "wallets")
        self.DATABASE_PATH: str = os.getenv("DATABASE_PATH", "marketplace_database.db")

        # Files constraints
        self.MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        self.SUPPORTED_FILE_TYPES: List[str] = (
            os.getenv("SUPPORTED_FILE_TYPES", ".pdf,.zip,.rar,.mp4,.txt,.docx")
            .split(",")
        )

        # Platform Commission (fixed 5%)
        self.PLATFORM_COMMISSION_RATE: float = 0.05

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

        # Admin Configuration
        self.ADMIN_USER_IDS = [int(x.strip()) for x in os.getenv('ADMIN_USER_IDS', '123456789').split(',') if x.strip()]

        # Business Logic Constants
        # Validation constants
        self.MIN_ADDRESS_LENGTH: int = 32
        self.MAX_ADDRESS_LENGTH: int = 44
        self.SALT_LENGTH: int = 16
        self.PRODUCT_ID_CODE_LENGTH: int = 6
        self.MAX_PRODUCT_ID_ATTEMPTS: int = 100

        # Address format validation
        self.ETHEREUM_ADDRESS_LENGTH: int = 42
        self.TRON_ADDRESS_LENGTHS: List[int] = [34, 35]

        # Product and pricing constants
        self.DEFAULT_SOL_PRICE_EUR: float = 100.0  # Fallback SOL price in EUR
        self.SELLER_REVENUE_RATE: float = 0.95  # 95% to seller after platform commission
        self.MAX_DESCRIPTION_PREVIEW_LENGTH: int = 300

        # Pagination and limits
        self.DEFAULT_PRODUCTS_LIMIT: int = 10
        self.DEFAULT_MESSAGES_LIMIT: int = 10
        self.DEFAULT_TICKETS_LIMIT: int = 10

        # Timeout and retry settings
        self.SOLANA_API_TIMEOUT: int = 10
        self.RECOVERY_CODE_VALIDITY_MINUTES: int = 15

        # Product status constants
        self.PRODUCT_STATUS_ACTIVE: str = "active"
        self.PRODUCT_STATUS_INACTIVE: str = "inactive"
        self.PRODUCT_STATUS_BANNED: str = "banned"

        # Payment status constants
        self.PAYMENT_STATUS_PENDING: str = "pending"
        self.PAYMENT_STATUS_COMPLETED: str = "completed"
        self.PAYMENT_STATUS_FAILED: str = "failed"

        # Payout status constants
        self.PAYOUT_STATUS_PENDING: str = "pending"
        self.PAYOUT_STATUS_PROCESSING: str = "processing"
        self.PAYOUT_STATUS_COMPLETED: str = "completed"
        self.PAYOUT_STATUS_FAILED: str = "failed"

        # User roles and types
        self.USER_ROLE_BUYER: str = "buyer"
        self.USER_ROLE_SELLER: str = "seller"
        self.USER_ROLE_ADMIN: str = "admin"

        # Default language
        self.DEFAULT_LANGUAGE: str = "fr"
        self.SUPPORTED_LANGUAGES: List[str] = ["fr", "en"]

        # Categories configuration
        self.DEFAULT_CATEGORIES: List[tuple] = [
            ('Finance & Crypto', 'Formations trading, blockchain, DeFi', '💰'),
            ('Marketing Digital', 'SEO, publicité, réseaux sociaux', '📈'),
            ('Développement', 'Programming, web dev, apps', '💻'),
            ('Design & Créatif', 'Graphisme, vidéo, arts', '🎨'),
            ('Business', 'Entrepreneuriat, management', '📊'),
            ('Formation Pro', 'Certifications, compétences', '🎓'),
            ('Outils & Tech', 'Logiciels, automatisation', '🔧')
        ]

        # Crypto display configuration
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

        # Network detection patterns
        self.NETWORK_PATTERNS: Dict[str, str] = {
            "EVM": "EVM (ex: ERC20)",
            "TRON": "TRC20 (TRON)",
            "SOLANA": "Solana (SPL)",
            "UNKNOWN": "inconnu"
        }

        # File handling constants
        self.ALLOWED_FILENAME_CHARS: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"

        # Product ID generation
        self.PRODUCT_ID_PREFIX: str = "TBF"
        self.PRODUCT_ID_ALPHABET: str = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # Avoid confusion O/0/I/1

        # State management constants
        self.CONFLICTING_STATES: List[str] = [
            'login_wait_email', 'login_wait_code', 'waiting_for_email',
            'waiting_for_recovery_code', 'waiting_new_password', 'creating_ticket',
            'waiting_for_product_id', 'adding_product', 'editing_product',
            'editing_product_price', 'editing_product_title', 'editing_product_description',
            'editing_seller_name', 'editing_seller_bio', 'creating_seller', 'waiting_seller_email',
            'waiting_seller_password', 'editing_settings', 'searching_user', 'searching_product',
            'suspending_product', 'suspending_user', 'restoring_user', 'admin_search_user',
            'admin_search_product', 'admin_suspend_product'
        ]

        # Markdown escape characters
        self.MARKDOWN_ESCAPE_CHARS: Dict[str, str] = {
            '_': r'\_', '*': r'\*', '[': r'\[', ']': r'\]', '(': r'\(', ')': r'\)',
            '~': r'\~', '`': r'\`', '>': r'\>', '#': r'\#', '+': r'\+', '-': r'\-',
            '=': r'\=', '|': r'\|', '{': r'\{', '}': r'\}', '.': r'\.', '!': r'\!'
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

