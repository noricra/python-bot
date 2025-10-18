import os
import tempfile

from app.domain.repositories.user_repo import UserRepository
from app.domain.repositories.product_repo import ProductRepository
from app.domain.repositories.order_repo import OrderRepository
from app.core.db import get_sqlite_connection


def setup_temp_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    conn = get_sqlite_connection(path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, language_code TEXT, is_seller BOOLEAN DEFAULT FALSE, seller_name TEXT, seller_bio TEXT, seller_rating REAL DEFAULT 0.0, total_sales INTEGER DEFAULT 0, total_revenue REAL DEFAULT 0.0, email TEXT, recovery_code_hash TEXT, password_salt TEXT, password_hash TEXT)')
    cur.execute('CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT UNIQUE, seller_user_id INTEGER, title TEXT NOT NULL, description TEXT, category TEXT, price_eur REAL NOT NULL, price_usd REAL NOT NULL, main_file_path TEXT, file_size_mb REAL, views_count INTEGER DEFAULT 0, sales_count INTEGER DEFAULT 0, rating REAL DEFAULT 0.0, reviews_count INTEGER DEFAULT 0, status TEXT DEFAULT "active", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    cur.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT UNIQUE, buyer_user_id INTEGER, product_id TEXT, seller_user_id INTEGER, product_price_eur REAL, seller_revenue REAL, payment_currency TEXT, crypto_amount REAL, payment_status TEXT DEFAULT "pending", nowpayments_id TEXT, payment_address TEXT, file_delivered BOOLEAN DEFAULT FALSE, download_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP)')
    conn.commit()
    conn.close()
    return path


def test_user_repo_add_and_get():
    db = setup_temp_db()
    repo = UserRepository(db)
    assert repo.add_user(1, 'alice', 'Alice', 'fr')
    user = repo.get_user(1)
    assert user is not None
    assert user['username'] == 'alice'


def test_product_repo_insert_and_fetch():
    db = setup_temp_db()
    # Need a seller
    UserRepository(db).add_user(2, 'bob', 'Bob', 'fr')
    prod = {
        'product_id': 'TBF-2501-ABC123',
        'seller_user_id': 2,
        'title': 'Cours 101',
        'description': 'Intro',
        'category': 'Dev',
        'price_eur': 49.0,
        'price_usd': 53.9,
        'main_file_path': '/tmp/file.pdf',
        'file_size_mb': 10.0,
        'status': 'active',
    }
    prepo = ProductRepository(db)
    assert prepo.insert_product(prod)
    out = prepo.get_product_by_id('TBF-2501-ABC123')
    assert out is not None
    assert out['title'] == 'Cours 101'


def test_order_repo_insert_and_get():
    db = setup_temp_db()
    UserRepository(db).add_user(10, 'buyer', 'Buyer', 'fr')
    UserRepository(db).add_user(20, 'seller', 'Seller', 'fr')
    ProductRepository(db).insert_product({'product_id': 'TBF-2501-ZZZ999','seller_user_id': 20,'title': 'Cours', 'description': 'X', 'category': 'Dev', 'price_eur': 20.0, 'price_usd': 22.0, 'main_file_path': '/tmp/f.pdf', 'file_size_mb': 1.0, 'status': 'active'})
    orepo = OrderRepository(db)
    ok = orepo.insert_order({'order_id': 'ORD1','buyer_user_id': 10,'product_id': 'TBF-2501-ZZZ999','seller_user_id': 20,'product_title': 'Cours','product_price_eur': 20.0,'seller_revenue': 19.0,'crypto_currency': 'usdc','crypto_amount': 5.0,'payment_status': 'pending','nowpayments_id': 'NP1','payment_address': '0xabc'})
    assert ok
    fetched = orepo.get_order_by_id('ORD1')
    assert fetched is not None
    assert fetched['crypto_currency'] == 'usdc'
