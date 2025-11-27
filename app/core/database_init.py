"""
Database Initialization Service - PostgreSQL on Railway
Migration from SQLite to PostgreSQL - Schema only (no data migration)
"""
import psycopg2
import psycopg2.extras
import logging
import os
from typing import Optional
from app.core.db_pool import get_connection, put_connection, PooledConnection, init_connection_pool

logger = logging.getLogger(__name__)


def get_postgresql_connection():
    """
    Get PostgreSQL connection from connection pool.

    IMPORTANT: You MUST call put_connection(conn) when done, or use PooledConnection context manager.

    Returns:
        psycopg2.connection: PostgreSQL database connection from pool

    Usage Option 1 (manual):
        conn = get_postgresql_connection()
        try:
            cursor = conn.cursor()
            # ... do work ...
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            put_connection(conn)  # IMPORTANT: Always return to pool

    Usage Option 2 (recommended - context manager):
        with PooledConnection() as conn:
            cursor = conn.cursor()
            # ... do work ...
            conn.commit()
        # Connection automatically returned to pool
    """
    try:
        return get_connection()
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        raise


class DatabaseInitService:
    """Service responsible for PostgreSQL database initialization"""

    def __init__(self):
        """Initialize database service for PostgreSQL"""
        pass

    def init_all_tables(self):
        """Initialize all PostgreSQL database tables"""
        conn = None
        try:
            logger.info("🗄️  Initializing PostgreSQL database...")
            conn = get_postgresql_connection()
            cursor = conn.cursor()

            # Create all tables (in correct order for foreign keys)
            logger.info("📋 Creating/verifying database tables...")
            self._create_users_table(cursor, conn)
            self._create_categories_table(cursor, conn)
            self._create_products_table(cursor, conn)
            self._create_orders_table(cursor, conn)
            self._create_reviews_table(cursor, conn)
            self._create_seller_payouts_table(cursor, conn)
            self._create_support_tickets_table(cursor, conn)

            # Insert default data
            logger.info("📦 Inserting default data...")
            self._insert_default_categories(cursor, conn)

            # Create triggers for automatic rating updates
            logger.info("⚙️  Creating database triggers...")
            self._create_rating_triggers(cursor, conn)

            logger.info("✅ PostgreSQL database initialization completed successfully")

        except Exception as e:
            logger.error(f"❌ PostgreSQL database initialization failed: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                put_connection(conn)  # Return connection to pool

    def _create_users_table(self, cursor, conn):
        """
        Create users table (PostgreSQL)
        Removed: recovery_code_hash, recovery_code_expiry (no password system)
        """
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language_code TEXT DEFAULT 'fr',
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_seller BOOLEAN DEFAULT FALSE,
                    seller_name TEXT,
                    seller_bio TEXT,
                    seller_rating REAL DEFAULT 0.0,
                    total_sales INTEGER DEFAULT 0,
                    total_revenue REAL DEFAULT 0.0,
                    email TEXT,
                    seller_solana_address TEXT,
                    password_salt TEXT,
                    password_hash TEXT,
                    is_suspended BOOLEAN DEFAULT FALSE,
                    suspension_reason TEXT,
                    suspended_at TIMESTAMP,
                    suspended_until TIMESTAMP,
                    storage_used_mb REAL DEFAULT 0.0,
                    storage_limit_mb REAL DEFAULT 100.0
                )
            ''')
            conn.commit()
            logger.debug("✅ Users table created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating users table: {e}")
            conn.rollback()
            raise

    def _create_categories_table(self, cursor, conn):
        """Create categories table (PostgreSQL)"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    icon TEXT,
                    products_count INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            logger.debug("✅ Categories table created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating categories table: {e}")
            conn.rollback()
            raise

    def _create_products_table(self, cursor, conn):
        """
        Create products table (PostgreSQL)
        - Removed: id (product_id is PRIMARY KEY)
        - Price stored in USD (column: price_usd), EUR shown in parentheses in UI
        - Updated: paths for object storage (Backblaze B2, not local files)
        """
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    product_id TEXT PRIMARY KEY,
                    seller_user_id BIGINT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    price_usd REAL NOT NULL,
                    main_file_url TEXT,
                    file_size_mb REAL,
                    cover_image_url TEXT,
                    thumbnail_url TEXT,
                    telegram_thumb_file_id TEXT,
                    telegram_cover_file_id TEXT,
                    views_count INTEGER DEFAULT 0,
                    sales_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    reviews_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    deactivated_by_admin BOOLEAN DEFAULT FALSE,
                    admin_deactivation_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (seller_user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')

            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_seller ON products(seller_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_status ON products(status)')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_telegram_thumb ON products(telegram_thumb_file_id) WHERE telegram_thumb_file_id IS NOT NULL")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_telegram_cover ON products(telegram_cover_file_id) WHERE telegram_cover_file_id IS NOT NULL")

            conn.commit()
            logger.debug("✅ Products table created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating products table: {e}")
            conn.rollback()
            raise

    def _create_orders_table(self, cursor, conn):
        """
        Create orders table (PostgreSQL)
        - Primary Key: order_id (removed id column)
        - All prices in USD (product_price_usd, seller_revenue_usd, platform_commission_usd)
        - payment_address: NOWPayments temporary wallet where buyer sends crypto
        - Unified: timestamps (all in TIMESTAMP format, not mixed)
        """
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    buyer_user_id BIGINT NOT NULL,
                    seller_user_id BIGINT NOT NULL,
                    product_id TEXT NOT NULL,
                    product_title TEXT NOT NULL,
                    product_price_usd REAL NOT NULL,
                    payment_id TEXT,
                    payment_address TEXT,
                    payment_currency TEXT,
                    payment_status TEXT DEFAULT 'pending',
                    nowpayments_id TEXT,
                    seller_revenue_usd REAL DEFAULT 0.0,
                    platform_commission_usd REAL DEFAULT 0.0,
                    file_delivered BOOLEAN DEFAULT FALSE,
                    download_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    last_download_at TIMESTAMP,
                    FOREIGN KEY (buyer_user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (seller_user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_buyer ON orders(buyer_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_seller ON orders(seller_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(payment_status)')

            conn.commit()
            logger.debug("✅ Orders table created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating orders table: {e}")
            conn.rollback()
            raise

    def _create_reviews_table(self, cursor, conn):
        """
        Create reviews table (PostgreSQL)
        - Primary Key: Composite (buyer_user_id, product_id) - removed id
        - Merged: comment and review_text into single review_text column
        - Removed: order_id (never used)
        """
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    product_id TEXT NOT NULL,
                    buyer_user_id BIGINT NOT NULL,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5) NOT NULL,
                    review_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (buyer_user_id, product_id),
                    FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE,
                    FOREIGN KEY (buyer_user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')

            # Create index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)')

            conn.commit()
            logger.debug("✅ Reviews table created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating reviews table: {e}")
            conn.rollback()
            raise

    def _create_seller_payouts_table(self, cursor, conn):
        """
        Create seller payouts table (PostgreSQL)
        Adapted for new NowPayments API (split payments)
        """
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seller_payouts (
                    id SERIAL PRIMARY KEY,
                    seller_user_id BIGINT NOT NULL,
                    order_ids TEXT,
                    total_amount_usdt REAL NOT NULL,
                    payout_status TEXT DEFAULT 'pending',
                    payout_tx_hash TEXT,
                    seller_wallet_address TEXT NOT NULL,
                    payment_currency TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    FOREIGN KEY (seller_user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')

            # Create index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_seller ON seller_payouts(seller_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_status ON seller_payouts(payout_status)')

            conn.commit()
            logger.debug("✅ Seller payouts table created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating seller_payouts table: {e}")
            conn.rollback()
            raise

    def _create_support_tickets_table(self, cursor, conn):
        """
        Create support tickets table (PostgreSQL)
        For customer support and issue tracking
        """
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    ticket_id VARCHAR(50) UNIQUE NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    client_email VARCHAR(255),
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_support_tickets_ticket_id ON support_tickets(ticket_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at DESC)')

            conn.commit()
            logger.debug("✅ Support tickets table created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating support_tickets table: {e}")
            conn.rollback()
            raise

    def _create_rating_triggers(self, cursor, conn):
        """
        Create triggers to auto-update product ratings (PostgreSQL)
        Note: PostgreSQL uses functions + triggers (different from SQLite)
        """
        try:
            # Create function for rating update
            cursor.execute('''
                CREATE OR REPLACE FUNCTION update_product_rating()
                RETURNS TRIGGER AS $$
                BEGIN
                    UPDATE products
                    SET rating = (
                        SELECT COALESCE(AVG(rating), 0.0)
                        FROM reviews
                        WHERE product_id = COALESCE(NEW.product_id, OLD.product_id)
                    ),
                    reviews_count = (
                        SELECT COUNT(*)
                        FROM reviews
                        WHERE product_id = COALESCE(NEW.product_id, OLD.product_id)
                    )
                    WHERE product_id = COALESCE(NEW.product_id, OLD.product_id);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            ''')

            # Create triggers
            cursor.execute('''
                DROP TRIGGER IF EXISTS trigger_update_rating_insert ON reviews;
                CREATE TRIGGER trigger_update_rating_insert
                AFTER INSERT ON reviews
                FOR EACH ROW
                EXECUTE FUNCTION update_product_rating();
            ''')

            cursor.execute('''
                DROP TRIGGER IF EXISTS trigger_update_rating_update ON reviews;
                CREATE TRIGGER trigger_update_rating_update
                AFTER UPDATE ON reviews
                FOR EACH ROW
                EXECUTE FUNCTION update_product_rating();
            ''')

            cursor.execute('''
                DROP TRIGGER IF EXISTS trigger_update_rating_delete ON reviews;
                CREATE TRIGGER trigger_update_rating_delete
                AFTER DELETE ON reviews
                FOR EACH ROW
                EXECUTE FUNCTION update_product_rating();
            ''')

            conn.commit()
            logger.debug("✅ Rating triggers created/verified (PostgreSQL)")
        except Exception as e:
            logger.error(f"❌ Error creating rating triggers: {e}")
            conn.rollback()
            raise

    def _insert_default_categories(self, cursor, conn):
        """Insert default categories (PostgreSQL)"""
        default_categories = [
            ('Finance & Crypto', 'Formations trading, blockchain, DeFi', '💰'),
            ('Marketing Digital', 'SEO, publicité, réseaux sociaux', '📈'),
            ('Développement', 'Programming, web dev, apps', '💻'),
            ('Design & Créatif', 'Graphisme, vidéo, arts', '🎨'),
            ('Business', 'Entrepreneuriat, management', '📊'),
            ('Formation Pro', 'Certifications, compétences', '🎓'),
            ('Outils & Tech', 'Logiciels, automatisation', '🔧')
        ]

        try:
            for cat_name, cat_desc, cat_icon in default_categories:
                cursor.execute(
                    '''INSERT INTO categories (name, description, icon)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (name) DO NOTHING''',
                    (cat_name, cat_desc, cat_icon)
                )
            conn.commit()
            logger.debug("✅ Default categories inserted/verified (PostgreSQL)")

        except Exception as e:
            logger.error(f"❌ Error inserting default categories: {e}")
            conn.rollback()
            raise


# Backward compatibility function (will be removed in next phase)
def get_sqlite_connection(db_path: Optional[str] = None):
    """
    DEPRECATED: This function is kept for backward compatibility only
    All new code should use get_postgresql_connection()
    """
    logger.warning("⚠️ get_sqlite_connection() is deprecated. Use get_postgresql_connection() instead.")
    raise NotImplementedError("SQLite is no longer supported. Please use PostgreSQL.")
