"""
Database Initialization Service - Centralized database setup and migrations
"""
import sqlite3
import logging
from app.core import get_sqlite_connection

logger = logging.getLogger(__name__)

class DatabaseInitService:
    """Service responsible for database initialization and migrations"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def init_all_tables(self):
        """Initialize all database tables and run migrations"""
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()

            # Create all tables
            self._create_users_table(cursor, conn)
            self._create_seller_payouts_table(cursor, conn)
            self._create_products_table(cursor, conn)
            self._create_orders_table(cursor, conn)
            self._create_reviews_table(cursor, conn)
            self._create_wallet_transactions_table(cursor, conn)
            self._create_support_tables(cursor, conn)
            self._create_categories_table(cursor, conn)
            self._create_telegram_mappings_table(cursor, conn)

            # Run migrations
            self._migrate_users_table(cursor, conn)
            self._migrate_support_tickets(cursor, conn)
            self._migrate_orders_table(cursor, conn)
            self._migrate_reviews_table(cursor, conn)
            self._migrate_products_table(cursor, conn)

            # Create triggers for automatic rating updates
            self._create_rating_triggers(cursor, conn)

            # Insert default data
            self._insert_default_categories(cursor, conn)

            conn.close()
            logger.info("✅ Database initialization completed successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    def _create_users_table(self, cursor, conn):
        """Create users table"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
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
                    recovery_code_hash TEXT,
                    recovery_code_expiry INTEGER,
                    password_salt TEXT,
                    password_hash TEXT
                )
            ''')
            conn.commit()
            logger.debug("✅ Users table created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating users table: {e}")
            conn.rollback()
            raise

    def _create_seller_payouts_table(self, cursor, conn):
        """Create seller payouts table"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seller_payouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seller_user_id INTEGER,
                    order_ids TEXT,  -- JSON array of order_ids
                    total_amount_sol REAL,
                    payout_status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
                    payout_tx_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    FOREIGN KEY (seller_user_id) REFERENCES users (user_id)
                )
            ''')
            conn.commit()
            logger.debug("✅ Seller payouts table created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating seller_payouts table: {e}")
            conn.rollback()
            raise

    def _create_products_table(self, cursor, conn):
        """Create products table"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT UNIQUE,
                    seller_user_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    price_eur REAL NOT NULL,
                    price_usd REAL NOT NULL,
                    main_file_path TEXT,
                    file_size_mb REAL,
                    cover_image_path TEXT,
                    thumbnail_path TEXT,
                    views_count INTEGER DEFAULT 0,
                    sales_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    reviews_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (seller_user_id) REFERENCES users (user_id)
                )
            ''')
            conn.commit()
            logger.debug("✅ Products table created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating products table: {e}")
            conn.rollback()
            raise

    def _create_orders_table(self, cursor, conn):
        """Create orders table - Clean version without platform_commission"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    buyer_user_id INTEGER NOT NULL,
                    seller_user_id INTEGER NOT NULL,
                    product_id TEXT NOT NULL,
                    product_title TEXT NOT NULL,
                    product_price_eur REAL NOT NULL,
                    payment_id TEXT,
                    payment_currency TEXT,
                    crypto_currency TEXT,
                    crypto_amount REAL,
                    payment_status TEXT DEFAULT 'pending',
                    payment_address TEXT,
                    nowpayments_id TEXT,
                    seller_revenue REAL DEFAULT 0.0,
                    file_delivered BOOLEAN DEFAULT FALSE,
                    download_count INTEGER DEFAULT 0,
                    last_download_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (buyer_user_id) REFERENCES users (user_id),
                    FOREIGN KEY (seller_user_id) REFERENCES users (user_id),
                    FOREIGN KEY (product_id) REFERENCES products (product_id)
                )
            ''')
            conn.commit()
            logger.debug("✅ Orders table created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating orders table: {e}")
            conn.rollback()
            raise

    def _create_reviews_table(self, cursor, conn):
        """Create reviews table"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT,
                    buyer_user_id INTEGER,
                    order_id TEXT,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    comment TEXT,
                    review_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (product_id),
                    FOREIGN KEY (buyer_user_id) REFERENCES users (user_id),
                    FOREIGN KEY (order_id) REFERENCES orders (order_id),
                    UNIQUE(buyer_user_id, product_id)
                )
            ''')
            conn.commit()
            logger.debug("✅ Reviews table created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating reviews table: {e}")
            conn.rollback()
            raise

    def _create_wallet_transactions_table(self, cursor, conn):
        """Create wallet transactions table"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    transaction_type TEXT,  -- receive, send, commission
                    crypto_currency TEXT,
                    amount REAL,
                    from_address TEXT,
                    to_address TEXT,
                    tx_hash TEXT,
                    status TEXT DEFAULT 'pending',  -- pending, confirmed, failed
                    related_order_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            conn.commit()
            logger.debug("✅ Wallet transactions table created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating wallet_transactions table: {e}")
            conn.rollback()
            raise

    def _create_support_tables(self, cursor, conn):
        """Create support related tables"""
        try:
            # Support tickets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ticket_id TEXT UNIQUE,
                    subject TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'open',
                    admin_response TEXT,
                    order_id TEXT,
                    product_id TEXT,
                    seller_user_id INTEGER,
                    assigned_to_user_id INTEGER,
                    issue_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Support messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT,
                    sender_user_id INTEGER,
                    sender_role TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.debug("✅ Support tables created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating support tables: {e}")
            conn.rollback()
            raise

    def _create_categories_table(self, cursor, conn):
        """Create categories table"""
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    icon TEXT,
                    products_count INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            logger.debug("✅ Categories table created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating categories table: {e}")
            conn.rollback()
            raise

    def _migrate_users_table(self, cursor, conn):
        """Clean users table from legacy fields"""
        try:
            cursor.execute("PRAGMA table_info(users)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            # Check if we have legacy fields that need cleanup (excluding seller_solana_address which is still needed)
            legacy_fields = ['recovery_email', 'is_partner', 'partner_code', 'referred_by', 'total_commission']
            has_legacy = any(field in existing_cols for field in legacy_fields)

            if has_legacy:
                logger.info("🔧 Cleaning legacy fields from users table...")

                # For existing databases, we need to recreate the table
                # First, backup data with conditional email handling
                email_field = "COALESCE(email, recovery_email) as email" if 'recovery_email' in existing_cols else "email"

                cursor.execute(f'''CREATE TEMPORARY TABLE users_backup AS
                                 SELECT user_id, username, first_name, language_code,
                                        registration_date, last_activity, is_seller, seller_name,
                                        seller_bio, seller_rating, total_sales, total_revenue,
                                        {email_field},
                                        seller_solana_address,
                                        recovery_code_hash, password_salt, password_hash
                                 FROM users''')

                # Drop old table
                cursor.execute('DROP TABLE users')

                # Recreate clean table
                cursor.execute('''
                    CREATE TABLE users (
                        user_id INTEGER PRIMARY KEY,
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
                        recovery_code_hash TEXT,
                        password_salt TEXT,
                        password_hash TEXT
                    )
                ''')

                # Restore data
                cursor.execute('''INSERT INTO users SELECT * FROM users_backup''')
                cursor.execute('DROP TABLE users_backup')

                logger.info("✅ Users table cleaned from legacy fields")
            else:
                logger.debug("✅ Users table structure is already clean")

        except sqlite3.Error as e:
            logger.error(f"❌ Error migrating users table: {e}")
            conn.rollback()
            raise

    def _migrate_support_tickets(self, cursor, conn):
        """Add missing columns to support_tickets table"""
        try:
            cursor.execute("PRAGMA table_info(support_tickets)")
            cols = {row[1] for row in cursor.fetchall()}
            altered = False

            migrations = [
                ('order_id', 'TEXT'),
                ('product_id', 'TEXT'),
                ('seller_user_id', 'INTEGER'),
                ('assigned_to_user_id', 'INTEGER'),
                ('issue_type', 'TEXT'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]

            for col_name, col_type in migrations:
                if col_name not in cols:
                    cursor.execute(f"ALTER TABLE support_tickets ADD COLUMN {col_name} {col_type}")
                    altered = True
                    logger.debug(f"✅ Added column {col_name} to support_tickets table")

            if altered:
                conn.commit()
                logger.debug("✅ Support tickets migration completed")

        except sqlite3.Error as e:
            logger.error(f"❌ Error migrating support_tickets table: {e}")
            conn.rollback()
            raise

    def _migrate_orders_table(self, cursor, conn):
        """Add missing columns to orders table"""
        try:
            cursor.execute("PRAGMA table_info(orders)")
            cols = {row[1] for row in cursor.fetchall()}

            if 'last_download_at' not in cols:
                cursor.execute("ALTER TABLE orders ADD COLUMN last_download_at TIMESTAMP")
                conn.commit()
                logger.debug("✅ Added column last_download_at to orders table")

        except sqlite3.Error as e:
            logger.error(f"❌ Error migrating orders table: {e}")
            conn.rollback()
            raise

    def _migrate_reviews_table(self, cursor, conn):
        """Add missing columns to reviews table"""
        try:
            cursor.execute("PRAGMA table_info(reviews)")
            cols = {row[1] for row in cursor.fetchall()}
            altered = False

            migrations = [
                ('review_text', 'TEXT'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]

            for col_name, col_type in migrations:
                if col_name not in cols:
                    cursor.execute(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_type}")
                    altered = True
                    logger.debug(f"✅ Added column {col_name} to reviews table")

            if altered:
                conn.commit()

            # Create unique index if it doesn't exist
            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_buyer_product ON reviews(buyer_user_id, product_id)")
                conn.commit()
                logger.debug("✅ Reviews table migration completed")
            except sqlite3.Error:
                # Index might already exist from table creation
                pass

        except sqlite3.Error as e:
            logger.error(f"❌ Error migrating reviews table: {e}")
            conn.rollback()
            raise

    def _migrate_products_table(self, cursor, conn):
        """Add missing columns to products table for image support"""
        try:
            cursor.execute("PRAGMA table_info(products)")
            cols = {row[1] for row in cursor.fetchall()}
            altered = False

            migrations = [
                ('cover_image_path', 'TEXT'),
                ('thumbnail_path', 'TEXT')
            ]

            for col_name, col_type in migrations:
                if col_name not in cols:
                    cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
                    altered = True
                    logger.debug(f"✅ Added column {col_name} to products table")

            if altered:
                conn.commit()
                logger.debug("✅ Products table migration completed")

        except sqlite3.Error as e:
            logger.error(f"❌ Error migrating products table: {e}")
            conn.rollback()
            raise

    def _create_telegram_mappings_table(self, cursor, conn):
        """Create telegram_mappings table for TRUE multi-account support"""
        try:
            # Check if old structure exists (PRIMARY KEY on telegram_id)
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='telegram_mappings'")
            result = cursor.fetchone()

            if result and 'telegram_id INTEGER PRIMARY KEY' in result[0]:
                logger.info("🔄 Migrating telegram_mappings to multi-account structure...")

                # 1. Backup old data
                cursor.execute('SELECT telegram_id, seller_user_id, created_at, last_login FROM telegram_mappings')
                old_data = cursor.fetchall()

                # 2. Drop old table
                cursor.execute('DROP TABLE telegram_mappings')

                # 3. Create new structure
                cursor.execute('''
                    CREATE TABLE telegram_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER NOT NULL,
                        seller_user_id INTEGER NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        account_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (seller_user_id) REFERENCES users (user_id),
                        UNIQUE(telegram_id, seller_user_id)
                    )
                ''')

                # 4. Migrate old data (all as active by default)
                for telegram_id, seller_user_id, created_at, last_login in old_data:
                    cursor.execute('''
                        INSERT INTO telegram_mappings (telegram_id, seller_user_id, is_active, created_at, last_login)
                        VALUES (?, ?, 1, ?, ?)
                    ''', (telegram_id, seller_user_id, created_at, last_login))

                conn.commit()
                logger.info(f"✅ Migrated {len(old_data)} accounts to new multi-account structure")
            else:
                # Create new structure directly
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS telegram_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER NOT NULL,
                        seller_user_id INTEGER NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        account_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (seller_user_id) REFERENCES users (user_id),
                        UNIQUE(telegram_id, seller_user_id)
                    )
                ''')
                conn.commit()
                logger.debug("✅ Telegram mappings table created with multi-account support")

        except sqlite3.Error as e:
            logger.error(f"❌ Error creating telegram_mappings table: {e}")
            conn.rollback()
            raise

    def _create_rating_triggers(self, cursor, conn):
        """Create triggers to auto-update product ratings when reviews change"""
        try:
            # Trigger after INSERT on reviews
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_rating_after_insert
                AFTER INSERT ON reviews
                BEGIN
                    UPDATE products
                    SET rating = (
                        SELECT AVG(rating) FROM reviews WHERE product_id = NEW.product_id
                    ),
                    reviews_count = (
                        SELECT COUNT(*) FROM reviews WHERE product_id = NEW.product_id
                    )
                    WHERE product_id = NEW.product_id;
                END;
            ''')

            # Trigger after UPDATE on reviews
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_rating_after_update
                AFTER UPDATE ON reviews
                BEGIN
                    UPDATE products
                    SET rating = (
                        SELECT AVG(rating) FROM reviews WHERE product_id = NEW.product_id
                    ),
                    reviews_count = (
                        SELECT COUNT(*) FROM reviews WHERE product_id = NEW.product_id
                    )
                    WHERE product_id = NEW.product_id;
                END;
            ''')

            # Trigger after DELETE on reviews
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_rating_after_delete
                AFTER DELETE ON reviews
                BEGIN
                    UPDATE products
                    SET rating = (
                        SELECT COALESCE(AVG(rating), 0.0) FROM reviews WHERE product_id = OLD.product_id
                    ),
                    reviews_count = (
                        SELECT COUNT(*) FROM reviews WHERE product_id = OLD.product_id
                    )
                    WHERE product_id = OLD.product_id;
                END;
            ''')

            conn.commit()
            logger.debug("✅ Rating triggers created/verified")
        except sqlite3.Error as e:
            logger.error(f"❌ Error creating rating triggers: {e}")
            conn.rollback()
            raise

    def _insert_default_categories(self, cursor, conn):
        """Insert default categories"""
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
                    '''INSERT OR IGNORE INTO categories (name, description, icon)
                       VALUES (?, ?, ?)''',
                    (cat_name, cat_desc, cat_icon)
                )
            conn.commit()
            logger.debug("✅ Default categories inserted/verified")

        except sqlite3.Error as e:
            logger.error(f"❌ Error inserting default categories: {e}")
            conn.rollback()
            raise