#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechBot Marketplace - Plateforme de Formations Digitales
Version 2.0 - Marketplace sécurisée avec paiements crypto
"""

import os
import sys
import logging
import sqlite3
import requests
import json
import hashlib
import uuid
import asyncio
import hmac
import time
import random
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from dotenv import load_dotenv
import re
import base58
from contextlib import contextmanager
from functools import wraps
from collections import defaultdict
import aiohttp
import gzip
import shutil
from dataclasses import dataclass

# Charger les variables d'environnement
load_dotenv()

# Configuration
@dataclass
class Config:
    token: str
    nowpayments_api_key: str
    nowpayments_ipn_secret: str
    admin_user_id: Optional[int]
    admin_email: str
    smtp_server: str
    smtp_port: int
    smtp_email: str
    smtp_password: str
    max_connections: int
    cache_ttl: int
    max_file_size_mb: int
    rate_limit_requests: int
    rate_limit_window: int
    
    @classmethod
    def from_env(cls):
        return cls(
            token=os.getenv('TELEGRAM_TOKEN'),
            nowpayments_api_key=os.getenv('NOWPAYMENTS_API_KEY'),
            nowpayments_ipn_secret=os.getenv('NOWPAYMENTS_IPN_SECRET'),
            admin_user_id=int(os.getenv('ADMIN_USER_ID')) if os.getenv('ADMIN_USER_ID') else None,
            admin_email=os.getenv('ADMIN_EMAIL', 'admin@votre-domaine.com'),
            smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', '587')),
            smtp_email=os.getenv('SMTP_EMAIL'),
            smtp_password=os.getenv('SMTP_PASSWORD'),
            max_connections=int(os.getenv('MAX_CONNECTIONS', '10')),
            cache_ttl=int(os.getenv('CACHE_TTL', '3600')),
            max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', '100')),
            rate_limit_requests=int(os.getenv('RATE_LIMIT_REQUESTS', '10')),
            rate_limit_window=int(os.getenv('RATE_LIMIT_WINDOW', '60'))
        )

config = Config.from_env()

# Configuration marketplace
PLATFORM_COMMISSION_RATE = 0.05  # 5%
SUPPORTED_FILE_TYPES = ['.pdf', '.zip', '.rar', '.mp4', '.txt', '.docx']

# Configuration crypto
MARKETPLACE_CONFIG = {
    'supported_payment_cryptos': ['btc', 'eth', 'usdt', 'usdc', 'bnb', 'sol', 'ltc', 'xrp'],
    'platform_commission_rate': 0.05,  # 5%
    'min_payout_amount': 0.1,  # SOL minimum pour payout
}

# Configuration logging
os.makedirs('logs', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs('wallets', exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/marketplace.log'),
        logging.StreamHandler()
    ])
logger = logging.getLogger(__name__)

# ==========================================
# CLASSES DE PERFORMANCE ET OPTIMISATION
# ==========================================

class DatabaseManager:
    """Gestionnaire de base de données optimisé avec pool de connexions"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = []
        self.lock = asyncio.Lock()
    
    @contextmanager
    def get_connection(self):
        """Obtient une connexion du pool"""
        conn = None
        try:
            if self.connections:
                conn = self.connections.pop()
            else:
                conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
                conn.execute('PRAGMA journal_mode=WAL;')
                conn.execute('PRAGMA synchronous=NORMAL;')
                conn.execute('PRAGMA foreign_keys=ON;')
                conn.execute('PRAGMA busy_timeout=5000;')
            yield conn
        finally:
            if conn:
                if len(self.connections) < self.max_connections:
                    self.connections.append(conn)
                else:
                    conn.close()

class SmartCache:
    """Cache intelligent avec TTL et gestion mémoire"""
    
    def __init__(self, default_ttl: int = 3600):
        self.cache = {}
        self.ttl = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str):
        """Récupère une valeur du cache"""
        if key in self.cache:
            if time.time() < self.ttl.get(key, 0):
                return self.cache[key]
            else:
                del self.cache[key]
                del self.ttl[key]
        return None
    
    def set(self, key: str, value, ttl: int = None):
        """Définit une valeur dans le cache"""
        if ttl is None:
            ttl = self.default_ttl
        self.cache[key] = value
        self.ttl[key] = time.time() + ttl
    
    def clear_expired(self):
        """Nettoie les entrées expirées"""
        current_time = time.time()
        expired_keys = [k for k, v in self.ttl.items() if current_time > v]
        for key in expired_keys:
            del self.cache[key]
            del self.ttl[key]

class HTTPClient:
    """Client HTTP asynchrone avec retry et circuit breaker"""
    
    def __init__(self, retry_attempts: int = 3):
        self.session = None
        self.retry_attempts = retry_attempts
        self.failure_count = 0
        self.failure_threshold = 5
        self.recovery_timeout = 60
        self.last_failure_time = 0
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    async def get_session(self):
        """Obtient ou crée une session HTTP"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def make_request(self, url: str, method: str = 'GET', **kwargs):
        """Effectue une requête HTTP avec retry"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        session = await self.get_session()
        for attempt in range(self.retry_attempts):
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        self.state = 'CLOSED'
                        self.failure_count = 0
                        return await response.json()
                    else:
                        raise Exception(f"HTTP {response.status}")
            except Exception as e:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.state = 'OPEN'
                    self.last_failure_time = time.time()
                
                if attempt == self.retry_attempts - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)  # Backoff exponentiel

class RateLimiter:
    """Rate limiter pour protéger contre les abus"""
    
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """Vérifie si un utilisateur peut faire une requête"""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Nettoyer les anciennes requêtes
        user_requests[:] = [req for req in user_requests if now - req < self.window]
        
        if len(user_requests) < self.max_requests:
            user_requests.append(now)
            return True
        return False

class TaskQueue:
    """Queue de tâches asynchrone pour le traitement en arrière-plan"""
    
    def __init__(self, max_workers: int = 5):
        self.queue = asyncio.Queue()
        self.workers = []
        self.max_workers = max_workers
        self.running = False
    
    async def start(self):
        """Démarre les workers"""
        self.running = True
        for _ in range(self.max_workers):
            worker = asyncio.create_task(self.worker())
            self.workers.append(worker)
    
    async def stop(self):
        """Arrête les workers"""
        self.running = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
    
    async def add_task(self, task):
        """Ajoute une tâche à la queue"""
        await self.queue.put(task)
    
    async def worker(self):
        """Worker qui traite les tâches"""
        while self.running:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                try:
                    await task()
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                finally:
                    self.queue.task_done()
            except asyncio.TimeoutError:
                continue

def measure_performance(func):
    """Décorateur pour mesurer les performances"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise
    return wrapper


# SUPPRIMER ENTIÈREMENT la classe CryptoWalletManager
# REMPLACER PAR ces fonctions simples :

def validate_solana_address(address: str) -> bool:
    """Valide une adresse Solana"""
    try:
        # Vérification basique format
        if len(address) < 32 or len(address) > 44:
            return False

        # Caractères valides Base58
        base58.b58decode(address)
        return True
    except:
        return False

async def get_solana_balance_display(address: str, http_client: HTTPClient) -> float:
    """Récupère solde Solana pour affichage (optionnel) - Version asynchrone"""
    try:
        # API publique Solana avec client HTTP optimisé
        response = await http_client.make_request(
            "https://api.mainnet-beta.solana.com",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": 1, 
                "method": "getBalance",
                "params": [address]
            }
        )
        
        balance_lamports = response.get('result', {}).get('value', 0)
        return balance_lamports / 1_000_000_000  # Lamports to SOL
    except Exception as e:
        logger.warning(f"Erreur récupération solde Solana: {e}")
        return 0.0  # En cas d'erreur, afficher 0

def validate_email(email: str) -> bool:
    """Valide un email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email or '') is not None


class MarketplaceBot:

    def __init__(self):
        self.db_path = "marketplace_database.db"
        self.db_manager = DatabaseManager(self.db_path, config.max_connections)
        self.cache = SmartCache(config.cache_ttl)
        self.http_client = HTTPClient()
        self.rate_limiter = RateLimiter(config.rate_limit_requests, config.rate_limit_window)
        self.task_queue = TaskQueue()
        self.memory_cache = {}
        
        # Initialiser la base de données
        asyncio.create_task(self.init_database())
        # Démarrer la queue de tâches
        asyncio.create_task(self.task_queue.start())
        # Démarrer le nettoyage automatique du cache
        asyncio.create_task(self.cache_cleanup_task())

    def is_seller_logged_in(self, user_id: int) -> bool:
        state = self.memory_cache.get(user_id, {})
        return bool(state.get('seller_logged_in'))

    def set_seller_logged_in(self, user_id: int, logged_in: bool) -> None:
        state = self.memory_cache.setdefault(user_id, {})
        state['seller_logged_in'] = logged_in

    def reset_user_state_preserve_login(self, user_id: int) -> None:
        """Nettoie l'état utilisateur tout en préservant le flag de connexion vendeur."""
        current = self.memory_cache.get(user_id, {})
        logged = bool(current.get('seller_logged_in'))
        self.memory_cache[user_id] = {'seller_logged_in': logged}
    
    async def cache_cleanup_task(self):
        """Tâche de nettoyage automatique du cache"""
        while True:
            try:
                await asyncio.sleep(3600)  # Nettoyer toutes les heures
                self.cache.clear_expired()
                logger.info("Cache nettoyé automatiquement")
            except Exception as e:
                logger.error(f"Erreur nettoyage cache: {e}")
                await asyncio.sleep(300)  # Réessayer dans 5 minutes en cas d'erreur

    def get_db_connection(self):
        """Obtient une connexion de la base de données via le pool"""
        return self.db_manager.get_connection()

    def escape_markdown(self, text: str) -> str:
        if text is None:
            return ''
        replacements = {
            '_': r'\_', '*': r'\*', '[': r'\[', ']': r'\]', '(': r'\(', ')': r'\)',
            '~': r'\~', '`': r'\`', '>': r'\>', '#': r'\#', '+': r'\+', '-': r'\-',
            '=': r'\=', '|': r'\|', '{': r'\{', '}': r'\}', '.': r'\.', '!': r'\!'
        }
        return ''.join(replacements.get(ch, ch) for ch in text)

    def sanitize_filename(self, name: str) -> str:
        safe_name = os.path.basename(name or '')
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        sanitized = ''.join(ch if ch in allowed else '_' for ch in safe_name)
        return sanitized or f"file_{int(time.time())}"

    async def init_database(self):
        """Base de données simplifiée avec optimisations"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Table utilisateurs SIMPLIFIÉE
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        language_code TEXT DEFAULT 'fr',
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        -- Vendeur (SIMPLIFIÉ)
                        is_seller BOOLEAN DEFAULT FALSE,
                        seller_name TEXT,
                        seller_bio TEXT,
                        seller_solana_address TEXT,  -- JUSTE L'ADRESSE, pas de seed phrase
                        seller_rating REAL DEFAULT 0.0,
                        total_sales INTEGER DEFAULT 0,
                        total_revenue REAL DEFAULT 0.0,

                        -- Système de récupération
                        recovery_email TEXT,
                        recovery_code_hash TEXT,

                        email TEXT
                    )
                ''')
                
                # Index pour optimiser les recherches
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_seller ON users(is_seller)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_recovery_email ON users(recovery_email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table users: {e}")
                conn.rollback()

            # Table des payouts vendeurs (NOUVELLE)
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS seller_payouts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        seller_user_id INTEGER,
                        order_ids TEXT,  -- JSON array des order_ids
                        total_amount_sol REAL,
                        payout_status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
                        payout_tx_hash TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        FOREIGN KEY (seller_user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Index pour les payouts
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_seller ON seller_payouts(seller_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_status ON seller_payouts(payout_status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_created ON seller_payouts(created_at)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table seller_payouts: {e}")
                conn.rollback()

            # Table products (garder l'existante mais corriger generate_product_id)
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
                
                # Index pour les produits
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_status ON products(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_seller ON products(seller_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_sales ON products(sales_count)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_created ON products(created_at)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table products: {e}")
                conn.rollback()

            # Table orders (garder existante)
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id TEXT UNIQUE,
                        buyer_user_id INTEGER,
                        product_id TEXT,
                        seller_user_id INTEGER,
                        product_price_eur REAL,
                        platform_commission REAL,
                        seller_revenue REAL,

                        crypto_currency TEXT,
                        crypto_amount REAL,
                        payment_status TEXT DEFAULT 'pending',
                        nowpayments_id TEXT,
                        payment_address TEXT,

                        commission_paid BOOLEAN DEFAULT FALSE,
                        file_delivered BOOLEAN DEFAULT FALSE,
                        download_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        FOREIGN KEY (buyer_user_id) REFERENCES users (user_id),
                        FOREIGN KEY (seller_user_id) REFERENCES users (user_id),
                        FOREIGN KEY (product_id) REFERENCES products (product_id)
                    )
                ''')
                
                # Index pour les commandes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_buyer ON orders(buyer_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_seller ON orders(seller_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table orders: {e}")
                conn.rollback()

            # Table avis/reviews
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id TEXT,
                        buyer_user_id INTEGER,
                        order_id TEXT,

                        rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                        comment TEXT,

                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (product_id) REFERENCES products (product_id),
                        FOREIGN KEY (buyer_user_id) REFERENCES users (user_id),
                        FOREIGN KEY (order_id) REFERENCES orders (order_id)
                    )
                ''')
                
                # Index pour les avis
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_buyer ON reviews(buyer_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table reviews: {e}")
                conn.rollback()

            # Table transactions wallet
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

                        -- Lié aux commissions
                        related_order_id TEXT,

                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confirmed_at TIMESTAMP,

                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Index pour les transactions
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON wallet_transactions(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON wallet_transactions(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created ON wallet_transactions(created_at)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table wallet_transactions: {e}")
                conn.rollback()

            # Table support tickets (gardée de l'original)
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS support_tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        ticket_id TEXT UNIQUE,
                        subject TEXT,
                        message TEXT,
                        status TEXT DEFAULT 'open',
                        admin_response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Index pour les tickets
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_user ON support_tickets(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_created ON support_tickets(created_at)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table support_tickets: {e}")
                conn.rollback()

            # Table catégories
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
                
                # Index pour les catégories
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_products_count ON categories(products_count)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Erreur création table categories: {e}")
                conn.rollback()

            # Insérer catégories par défaut
            default_categories = [
                ('Finance & Crypto', 'Formations trading, blockchain, DeFi', '💰'),
                ('Marketing Digital', 'SEO, publicité, réseaux sociaux', '📈'),
                ('Développement', 'Programming, web dev, apps', '💻'),
                ('Design & Créatif', 'Graphisme, vidéo, arts', '🎨'),
                ('Business', 'Entrepreneuriat, management', '📊'),
                ('Formation Pro', 'Certifications, compétences', '🎓'),
                ('Outils & Tech', 'Logiciels, automatisation', '🔧')
            ]

            for cat_name, cat_desc, cat_icon in default_categories:
                try:
                    cursor.execute(
                        '''
                        INSERT OR IGNORE INTO categories (name, description, icon)
                        VALUES (?, ?, ?)
                    ''', (cat_name, cat_desc, cat_icon))
                    conn.commit()
                except sqlite3.Error as e:
                    logger.error(f"Erreur insertion catégorie {cat_name}: {e}")
                    conn.rollback()

    async def generate_product_id(self) -> str:
        """Génère un ID produit vraiment unique - Version asynchrone"""
        import secrets

        # Format aligné avec la recherche: TBF-YYMM-XXXXXX
        yymm = datetime.utcnow().strftime('%y%m')

        def random_code(length: int = 6) -> str:
            alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # éviter confusions O/0/I/1
            return ''.join(random.choice(alphabet) for _ in range(length))

        # Double vérification d'unicité
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            max_attempts = 100
            for attempt in range(max_attempts):
                product_id = f"TBF-{yymm}-{random_code()}"

                try:
                    cursor.execute('SELECT COUNT(*) FROM products WHERE product_id = ?', (product_id,))
                    if cursor.fetchone()[0] == 0:
                        return product_id
                except sqlite3.Error as e:
                    logger.error(f"Erreur vérification ID produit: {e}")
                    raise e

                # Si collision, générer nouveau random
                yymm = datetime.utcnow().strftime('%y%m')

            raise Exception("Impossible de générer un ID unique après 100 tentatives")

    async def add_user(self,
                 user_id: int,
                 username: str,
                 first_name: str,
                 language_code: str = 'fr') -> bool:
        """Ajoute un utilisateur - Version asynchrone"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT OR IGNORE INTO users 
                    (user_id, username, first_name, language_code)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, language_code))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Erreur ajout utilisateur: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Récupère un utilisateur - Version asynchrone"""
        try:
            with self.get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id, ))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération utilisateur: {e}")
            return None

    def create_seller_account_with_recovery(self, user_id: int, seller_name: str, 
                                      seller_bio: str, recovery_email: str, 
                                      solana_address: str) -> dict:
        """Crée un compte vendeur avec email + code de récupération"""
        try:
            # Valider adresse Solana
            if not validate_solana_address(solana_address):
                return {'success': False, 'error': 'Adresse Solana invalide'}

            # Générer code de récupération 6 chiffres
            recovery_code = f"{random.randint(100000, 999999)}"

            # Hash du code (ne jamais stocker en clair)
            code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()

            with self.get_db_connection() as conn:
                cursor = conn.cursor()

                # Vérifier que l'adresse n'est pas déjà utilisée
                try:
                    cursor.execute(
                        'SELECT COUNT(*) FROM users WHERE seller_solana_address = ?',
                        (solana_address,)
                    )
                    if cursor.fetchone()[0] > 0:
                        return {'success': False, 'error': 'Adresse déjà utilisée'}
                except sqlite3.Error as e:
                    logger.error(f"Erreur vérification adresse: {e}")
                    return {'success': False, 'error': 'Erreur interne'}

                # Créer le compte vendeur
                try:
                    cursor.execute('''
                        UPDATE users 
                        SET is_seller = TRUE,
                            seller_name = ?,
                            seller_bio = ?,
                            seller_solana_address = ?,
                            recovery_email = ?,
                            recovery_code_hash = ?
                        WHERE user_id = ?
                    ''', (seller_name, seller_bio, solana_address, recovery_email, code_hash, user_id))

                    if cursor.rowcount > 0:
                        conn.commit()
                        return {
                            'success': True,
                            'recovery_code': recovery_code
                        }
                    else:
                        return {'success': False, 'error': 'Échec mise à jour'}
                except sqlite3.Error as e:
                    logger.error(f"Erreur création vendeur: {e}")
                    return {'success': False, 'error': 'Erreur interne'}

        except Exception as e:
            logger.error(f"Erreur création vendeur: {e}")
            return {'success': False, 'error': str(e)}

    def authenticate_seller(self, user_id: int, _ignored: str) -> bool:
        """Authentifie un vendeur.

        Note: l'ancien mécanisme par seed phrase n'est plus utilisé.
        On valide simplement que l'utilisateur a un compte vendeur actif.
        La récupération sécurisée se fait via email + code.
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT is_seller FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            return bool(row and row[0])
        except sqlite3.Error as e:
            logger.error(f"Erreur authentification vendeur: {e}")
            try:
                conn.close()
            except Exception:
                pass
            return False

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Récupère un produit par son ID"""
        conn = self.get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                SELECT p.*, u.seller_name, u.seller_rating
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.product_id = ? AND p.status = 'active'
            ''', (product_id, ))

            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération produit: {e}")
            conn.close()
            return None

    def get_available_referral_codes(self) -> List[str]:
        """Récupère les codes de parrainage disponibles"""
        # Codes fixes pour simplifier - plus descriptifs
        return [
            'TECH2025', 'CRYPTO57', 'BITCOIN', 'PROFIT42', 'MONEY57', 'GAIN420',
            'TRADE25', 'SOLANA', 'ETHEREUM', 'BLOCKCHAIN', 'DEFI2025', 'NFT2025'
        ]

    def validate_referral_code(self, code: str) -> bool:
        """Valide un code de parrainage"""
        available_codes = self.get_available_referral_codes()
        return code in available_codes

    async def create_payment(self, amount_usd: float, currency: str,
                       order_id: str) -> Optional[Dict]:
        """Crée un paiement NOWPayments - Version asynchrone optimisée"""
        try:
            if not config.nowpayments_api_key:
                logger.error("NOWPAYMENTS_API_KEY manquant!")
                return None

            headers = {
                "x-api-key": config.nowpayments_api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "price_amount": float(amount_usd),
                "price_currency": "usd",
                "pay_currency": currency.lower(),
                "order_id": order_id,
                "order_description": "Formation TechBot Marketplace"
            }

            response = await self.http_client.make_request(
                "https://api.nowpayments.io/v1/payment",
                method="POST",
                headers=headers,
                json=payload
            )

            if response:
                return response
            else:
                logger.error("Erreur paiement NOWPayments")
                return None
        except Exception as e:
            logger.error(f"Erreur PaymentManager: {e}")
            return None

    async def check_payment_status(self, payment_id: str) -> Optional[Dict]:
        """Vérifie le statut d'un paiement - Version asynchrone optimisée"""
        try:
            if not config.nowpayments_api_key:
                return None

            # Vérifier le cache d'abord
            cache_key = f"payment_status_{payment_id}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                return cached_result

            headers = {"x-api-key": config.nowpayments_api_key}
            response = await self.http_client.make_request(
                f"https://api.nowpayments.io/v1/payment/{payment_id}",
                method="GET",
                headers=headers
            )

            # Mettre en cache pour 30 secondes
            self.cache.set(cache_key, response, 30)
            return response
        except Exception as e:
            logger.error(f"Erreur vérification paiement: {e}")
            return None

    async def get_exchange_rate(self) -> float:
        """Récupère le taux EUR/USD - Version asynchrone optimisée"""
        try:
            # Vérifier le cache d'abord
            cached_rate = self.cache.get('eur_usd_rate')
            if cached_rate:
                return cached_rate

            response = await self.http_client.make_request(
                "https://api.exchangerate-api.com/v4/latest/EUR",
                method="GET"
            )
            
            if response and 'rates' in response:
                rate = response['rates']['USD']
                # Mettre en cache pour 1 heure
                self.cache.set('eur_usd_rate', rate, 3600)
                return rate
            return 1.10
        except Exception as e:
            logger.warning(f"Erreur récupération taux de change: {e}")
            return 1.10

    async def get_available_currencies(self) -> List[str]:
        """Récupère les cryptos disponibles - Version asynchrone optimisée"""
        try:
            # Vérifier le cache d'abord
            cached_currencies = self.cache.get('available_currencies')
            if cached_currencies:
                return cached_currencies

            if not config.nowpayments_api_key:
                return ['btc', 'eth', 'usdt', 'usdc']

            headers = {"x-api-key": config.nowpayments_api_key}
            response = await self.http_client.make_request(
                "https://api.nowpayments.io/v1/currencies",
                method="GET",
                headers=headers
            )
            
            if response and 'currencies' in response:
                currencies = response['currencies']
                main_cryptos = [
                    'btc', 'eth', 'usdt', 'usdc', 'bnb', 'sol', 'ltc', 'xrp'
                ]
                available = [c for c in currencies if c in main_cryptos]
                # Mettre en cache pour 1 heure
                self.cache.set('available_currencies', available, 3600)
                return available
            return ['btc', 'eth', 'usdt', 'usdc']
        except Exception as e:
            logger.warning(f"Erreur récupération devises: {e}")
            return ['btc', 'eth', 'usdt', 'usdc']

    async def create_seller_payout(self, seller_user_id: int, order_ids: list, 
                        total_amount_sol: float) -> Optional[int]:
        """Crée un payout vendeur en attente - Version asynchrone optimisée"""
        try:
            async with self.get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO seller_payouts 
                    (seller_user_id, order_ids, total_amount_sol, payout_status)
                    VALUES (?, ?, ?, 'pending')
                ''', (seller_user_id, json.dumps(order_ids), total_amount_sol))

                payout_id = cursor.lastrowid
                conn.commit()

                return payout_id

        except Exception as e:
            logger.error(f"Erreur création payout: {e}")
            return None

    async def auto_create_seller_payout(self, order_id: str) -> bool:
        """Crée automatiquement un payout vendeur après confirmation paiement"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Récupérer infos commande
            cursor.execute('''
                SELECT seller_user_id, product_price_eur
                FROM orders 
                WHERE order_id = ? AND payment_status = 'completed'
            ''', (order_id,))

            result = cursor.fetchone()
            if not result:
                return False

            seller_user_id, total_amount_eur = result

            # Calculer montant vendeur (95%)
            seller_amount_eur = total_amount_eur * 0.95

            # Convertir EUR → SOL (taux approximatif, à améliorer)
            sol_price_eur = 100  # À récupérer via API CoinGecko
            seller_amount_sol = seller_amount_eur / sol_price_eur

            # Créer le payout
            payout_id = self.create_seller_payout(
                seller_user_id, 
                [order_id], 
                seller_amount_sol
            )

            conn.close()
            return payout_id is not None

        except Exception as e:
            logger.error(f"Erreur auto payout: {e}")
            return False

    @measure_performance
    async def start_command(self, update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
        """Nouveau menu d'accueil marketplace"""
        user = update.effective_user
        user_id = user.id
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text(
                "⚠️ **Trop de requêtes**\n\nVeuillez patienter quelques secondes avant de réessayer."
            )
            return
        
        await self.add_user(user_id, user.username, user.first_name,
                      user.language_code or 'fr')

        # Ne pas déconnecter automatiquement à chaque /start
        # Garder l'état de connexion vendeur

        welcome_text = """🏪 **TECHBOT MARKETPLACE**
*Plateforme de formations digitales avec paiements crypto*

🎯 **Découvrez des formations premium**
📚 **Monétisez votre expertise**  
💳 **Paiements sécurisés en crypto**

Choisissez une option pour commencer :"""

        keyboard = [
            [InlineKeyboardButton("🛒 Acheter une formation", callback_data='buy_menu')],
            [InlineKeyboardButton("📚 Vendre vos formations", callback_data='sell_menu')],
            [InlineKeyboardButton("🔑 Accéder à mon compte", callback_data='access_account')],
            [InlineKeyboardButton("📊 Stats marketplace", callback_data='marketplace_stats')],
            [InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'), InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')]
        ]

        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire principal des boutons - COMPLET"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        user_data = await self.get_user(user_id)
        lang = user_data['language_code'] if user_data else 'fr'

        try:
            # Navigation principale
            if query.data == 'buy_menu':
                await self.buy_menu(query, lang)
            elif query.data == 'sell_menu':
                await self.sell_menu(query, lang)
            elif query.data == 'seller_dashboard':
                await self.seller_dashboard(query, lang)
            elif query.data == 'marketplace_stats':
                await self.marketplace_stats(query, lang)
            elif query.data == 'support_menu':
                await self.show_support_menu(query, lang)
            elif query.data == 'back_main':
                await self.back_to_main(query)
            elif query.data.startswith('lang_'):
                await self.change_language(query, query.data[5:])

            # Accès compte (unifié)
            elif query.data == 'access_account':
                await self.access_account_prompt(query, lang)
            elif query.data == 'seller_login':
                # Démarrer explicitement le flux de connexion (email puis code)
                self.memory_cache[user_id] = {'login_wait_email': True}
                await query.edit_message_text("🔑 Entrez votre email de récupération :")
            # Plus de saisie de code seul: on impose email + code

            # Achat
            elif query.data == 'search_product':
                await self.search_product_prompt(query, lang)
            elif query.data == 'browse_categories':
                await self.browse_categories(query, lang)
            elif query.data.startswith('category_'):
                category_key = query.data[9:]
                await self.show_category_products(query, category_key, lang)
            elif query.data.startswith('product_'):
                product_id = query.data[8:]
                await self.show_product_details(query, product_id, lang)
            elif query.data.startswith('buy_product_'):
                product_id = query.data[12:]
                await self.buy_product_prompt(query, product_id, lang)

            # Vente
            elif query.data == 'create_seller':
                await self.create_seller_prompt(query, lang)
            elif query.data == 'add_product':
                await self.add_product_prompt(query, lang)
            elif query.data == 'my_products':
                await self.show_my_products(query, lang)
            elif query.data == 'my_wallet':
                await self.show_wallet(query, lang)
            elif query.data == 'seller_logout':
                await self.seller_logout(query)
            elif query.data == 'seller_back':
                await self.seller_back(query)
            elif query.data == 'delete_seller':
                await self.delete_seller_prompt(query)
            elif query.data == 'delete_seller_confirm':
                await self.delete_seller_confirm(query)

            # NOUVEAU : Création produit avec catégories
            elif query.data.startswith('set_product_category_'):
                category_key = query.data[21:]
                category_name = category_key.replace('_', ' ').replace('and', '&')

                if user_id in self.memory_cache and self.memory_cache[user_id].get('adding_product'):
                    user_state = self.memory_cache[user_id]
                    user_state['product_data']['category'] = category_name
                    user_state['step'] = 'price'

                    await query.edit_message_text(
                        f"✅ **Catégorie :** {category_name}\n\n💰 **Étape 4/5 : Prix**\n\nFixez le prix en euros (ex: 49.99) :",
                        parse_mode='Markdown'
                    )

            # Récupération compte
            # (ancienne entrée de récupération retirée)
            elif query.data == 'recovery_by_email':
                await self.recovery_by_email_prompt(query, lang)

            # Parrainage (si gardé)
            elif query.data == 'enter_referral_manual':
                await self.enter_referral_manual(query, lang)
            elif query.data == 'choose_random_referral':
                await self.choose_random_referral(query, lang)
            elif query.data.startswith('use_referral_'):
                code = query.data[13:]
                await self.validate_and_proceed(query, code, lang)


            # Paiement
            elif query.data == 'proceed_to_payment':
                await self.show_crypto_options(query, lang)
            elif query.data.startswith('pay_'):
                crypto = query.data[4:]
                await self.process_payment(query, crypto, lang)
            elif query.data.startswith('check_payment_'):
                order_id = query.data[14:]
                await self.check_payment_handler(query, order_id, lang)

            # Téléchargement et bibliothèque
            elif query.data.startswith('download_product_'):
                product_id = query.data[17:]
                await self.download_product(query, context, product_id, lang)
            elif query.data == 'my_library':
                await self.show_my_library(query, lang)

            # Admin
            elif query.data == 'admin_menu':
                await self.admin_menu(query)
            elif query.data == 'admin_commissions':
                await self.admin_commissions_handler(query)
            elif query.data == 'admin_payouts':
                await self.admin_payouts_handler(query)
            elif query.data == 'admin_mark_all_payouts_paid':
                await self.admin_mark_all_payouts_paid(query)
            elif query.data == 'admin_export_payouts':
                await self.admin_export_payouts(query)
            elif query.data == 'admin_users':
                await self.admin_users_handler(query)
            elif query.data == 'admin_search_user':
                await self.admin_search_user(query)
            elif query.data == 'admin_export_users':
                await self.admin_export_users(query)
            elif query.data == 'admin_products':
                await self.admin_products_handler(query)
            elif query.data == 'admin_search_product':
                await self.admin_search_product(query)
            elif query.data == 'admin_suspend_product':
                await self.admin_suspend_product(query)
            elif query.data == 'admin_export_products':
                await self.admin_export_products(query)
            elif query.data == 'admin_marketplace_stats':
                await self.admin_marketplace_stats(query)

            # Support
            elif query.data == 'faq':
                await self.show_faq(query, lang)
            elif query.data == 'create_ticket':
                await self.create_ticket(query, lang)
            elif query.data == 'my_tickets':
                await self.show_my_tickets(query, lang)

            # Wallet vendeur actions
            elif query.data == 'payout_history':
                await self.payout_history(query)
            elif query.data == 'copy_address':
                await self.copy_address(query)

            # Autres écrans vendeur
            elif query.data == 'seller_analytics':
                await self.seller_analytics(query, lang)
            elif query.data == 'seller_settings':
                await self.seller_settings(query, lang)
            elif query.data == 'edit_seller_name':
                self.memory_cache[user_id] = {'editing_settings': True, 'step': 'edit_name'}
                await query.edit_message_text("Entrez le nouveau nom vendeur:")
            elif query.data == 'edit_seller_bio':
                self.memory_cache[user_id] = {'editing_settings': True, 'step': 'edit_bio'}
                await query.edit_message_text("Entrez la nouvelle biographie:")
            elif query.data == 'seller_info':
                await self.seller_info(query, lang)

            else:
                await query.edit_message_text(
                    "🚧 Fonction en cours de développement...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
                    ]]))

        except Exception as e:
            logger.error(f"Erreur button_handler: {e}")
            await query.edit_message_text(
                "❌ Erreur temporaire. Retour au menu principal.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
                ]]))

    async def buy_menu(self, query, lang):
        """Menu d'achat"""
        keyboard = [
            [InlineKeyboardButton("🔍 Rechercher par ID", callback_data='search_product')],
            [InlineKeyboardButton("📂 Parcourir catégories", callback_data='browse_categories')],
            [InlineKeyboardButton("🔥 Meilleures ventes", callback_data='category_bestsellers')],
            [InlineKeyboardButton("🆕 Nouveautés", callback_data='category_new')],
            [InlineKeyboardButton("💰 Mon wallet", callback_data='my_wallet')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        buy_text = """🛒 **ACHETER UNE FORMATION**

Plusieurs façons de découvrir nos formations :

🔍 **Recherche directe** - Si vous avez un ID produit
📂 **Par catégories** - Explorez par domaine
🔥 **Tendances** - Les plus populaires
🆕 **Nouveautés** - Dernières publications

💳 **Paiement sécurisé** en crypto-monnaies"""

        await query.edit_message_text(
            buy_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def search_product_prompt(self, query, lang):
        """Demande de saisir un ID produit"""
        self.memory_cache[query.from_user.id] = {
            'waiting_for_product_id': True,
            'lang': lang
        }

        await query.edit_message_text(
            """🔍 **RECHERCHE PAR ID PRODUIT**

Saisissez l'ID de la formation que vous souhaitez acheter.

💡 **Format attendu :** `TBF-2501-ABC123`

✍️ **Tapez l'ID produit :**""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
            ]),
            parse_mode='Markdown')

    async def browse_categories(self, query, lang):
        """Affiche les catégories disponibles"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT name, icon, products_count FROM categories ORDER BY products_count DESC'
            )
            categories = cursor.fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération catégories: {e}")
            conn.close()
            return

        keyboard = []
        for cat_name, cat_icon, products_count in categories:
            keyboard.append([
                InlineKeyboardButton(
                    f"{cat_icon} {cat_name} ({products_count})",
                    callback_data=
                    f'category_{cat_name.replace(" ", "_").replace("&", "and")}'
                )
            ])

        keyboard.append(
            [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')])

        keyboard.append(
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')])

        categories_text = """📂 **CATÉGORIES DE FORMATIONS**

Choisissez votre domaine d'intérêt :"""

        await query.edit_message_text(
            categories_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def show_category_products(self, query, category_key, lang):
        """Affiche les produits d'une catégorie - CORRIGÉ"""

        # CORRIGER la logique des catégories spéciales
        if category_key == 'bestsellers':
            category_name = 'Meilleures ventes'
            base_query = '''
                SELECT p.product_id, p.title, p.price_eur, p.sales_count, p.rating, u.seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.status = 'active'
                ORDER BY p.sales_count DESC
            '''
            query_params = ()
        elif category_key == 'new':
            category_name = 'Nouveautés'
            base_query = '''
                SELECT p.product_id, p.title, p.price_eur, p.sales_count, p.rating, u.seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.status = 'active'
                ORDER BY p.created_at DESC
            '''
            query_params = ()
        else:
            # Catégorie normale
            category_name = category_key.replace('_', ' ').replace('and', '&')
            base_query = '''
                SELECT p.product_id, p.title, p.price_eur, p.sales_count, p.rating, u.seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.status = 'active' AND p.category = ?
                ORDER BY p.sales_count DESC
            '''
            query_params = (category_name,)

        # Pagination optimisée
        page = 1
        limit = 10
        offset = (page - 1) * limit
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()

            # Exécuter la requête appropriée avec pagination
            try:
                cursor.execute(f"{base_query} LIMIT {limit} OFFSET {offset}", query_params)
                products = cursor.fetchall()
                
                # Compter le total pour la pagination
                count_query = base_query.replace("SELECT p.product_id, p.title, p.price_eur, p.sales_count, p.rating, u.seller_name", "SELECT COUNT(*)")
                cursor.execute(count_query, query_params)
                total_count = cursor.fetchone()[0]
                
            except sqlite3.Error as e:
                logger.error(f"Erreur récupération produits catégorie: {e}")
                return

        # Reste du code identique pour l'affichage...

        if not products:
            products_text = f"""📂 **{category_name.upper()}**

Aucune formation disponible dans cette catégorie pour le moment.

Soyez le premier à publier dans ce domaine !"""

            keyboard = [
                [InlineKeyboardButton("🚀 Créer une formation", callback_data='sell_menu')],
                [InlineKeyboardButton("📂 Autres catégories", callback_data='browse_categories')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
            ]
        else:
            products_text = f"📂 **{category_name.upper()}** ({len(products)} formations)\n\n"

            keyboard = []
            for product in products:
                product_id, title, price, sales, rating, seller = product
                stars = "⭐" * int(rating) if rating > 0 else "⭐⭐⭐⭐⭐"
                products_text += f"📦 **{title}**\n"
                products_text += f"💰 {price}€ • 👤 {seller} • {stars} • 🛒 {sales} ventes\n\n"

                keyboard.append([
                    InlineKeyboardButton(f"📖 {title[:40]}...",
                                         callback_data=f'product_{product_id}')
                ])

            keyboard.extend([[
                InlineKeyboardButton("📂 Autres catégories",
                                     callback_data='browse_categories')
            ], [
                InlineKeyboardButton("🔙 Menu achat", callback_data='buy_menu')
            ], [
                InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
            ]])

        await query.edit_message_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def show_product_details(self, query, product_id, lang):
        """Affiche les détails d'un produit"""
        product = self.get_product_by_id(product_id)

        if not product:
            await query.edit_message_text(
                f"❌ **Produit introuvable :** `{product_id}`\n\nVérifiez l'ID ou cherchez dans les catégories.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Rechercher",
                                         callback_data='search_product'),
                    InlineKeyboardButton("📂 Catégories",
                                         callback_data='browse_categories')
                ]]),
                parse_mode='Markdown')
            return

        # Mettre à jour compteur de vues
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE products SET views_count = views_count + 1 WHERE product_id = ?',
                (product_id, ))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur mise à jour vues produit: {e}")
            conn.close()

        stars = "⭐" * int(
            product['rating']) if product['rating'] > 0 else "⭐⭐⭐⭐⭐"

        product_text = f"""📦 **{product['title']}**

👤 **Vendeur :** {product['seller_name']} ({product['seller_rating']:.1f}/5)
📂 **Catégorie :** {product['category']}
💰 **Prix :** {product['price_eur']}€

📖 **Description :**
{product['description'] or 'Aucune description disponible'}

📊 **Statistiques :**
• {stars} ({product['reviews_count']} avis)
• 👁️ {product['views_count']} vues
• 🛒 {product['sales_count']} ventes

📁 **Fichier :** {product['file_size_mb']:.1f} MB"""

        keyboard = [
            [InlineKeyboardButton("🛒 Acheter maintenant", callback_data=f'buy_product_{product_id}')],
            [InlineKeyboardButton("📂 Autres produits", callback_data='browse_categories')],
            [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        await query.edit_message_text(
            product_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def buy_product_prompt(self, query, product_id, lang):
        """Demande code de parrainage pour un produit"""
        user_id = query.from_user.id

        # Vérifier si déjà acheté
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM orders WHERE buyer_user_id = ? AND product_id = ? AND payment_status = "completed"',
                (user_id, product_id))
            if cursor.fetchone()[0] > 0:
                conn.close()
                await query.edit_message_text(
                    "✅ **VOUS POSSÉDEZ DÉJÀ CE PRODUIT**\n\nAccédez-y depuis votre bibliothèque.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📚 Ma bibliothèque",
                                             callback_data='my_library'),
                        InlineKeyboardButton("🔙 Retour",
                                             callback_data=f'product_{product_id}')
                    ]]))
                return
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur vérification achat produit: {e}")
            conn.close()
            return

        # Stocker le produit à acheter
        self.memory_cache[user_id] = {
            'buying_product_id': product_id,
            'lang': lang
        }

        keyboard = [
            [
                InlineKeyboardButton("✍️ Saisir mon code",
                                     callback_data='enter_referral_manual')
            ],
            [
                InlineKeyboardButton("🎲 Choisir un code aléatoire",
                                     callback_data='choose_random_referral')
            ],

            [
                InlineKeyboardButton("🔙 Retour",
                                     callback_data=f'product_{product_id}')
            ]
        ]

        referral_text = """🎯 **CODE DE PARRAINAGE REQUIS**

⚠️ **IMPORTANT :** Un code de parrainage est requis pour acheter.

💡 **2 OPTIONS DISPONIBLES :**

1️⃣ **Vous avez un code ?** Saisissez-le !

2️⃣ **Pas de code ?** Choisissez-en un gratuitement !"""

        await query.edit_message_text(
            referral_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def enter_referral_manual(self, query, lang):
        """Demander la saisie manuelle du code"""
        self.memory_cache[query.from_user.id]['waiting_for_referral'] = True

        await query.edit_message_text(
            "✍️ **Veuillez saisir votre code de parrainage :**\n\nTapez le code exactement comme vous l'avez reçu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
            ]))

    async def check_payment_handler(self, query, order_id, lang):
        """Vérification paiement + création payout vendeur"""
        await query.edit_message_text("🔍 Vérification en cours...")

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
            order = cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération commande: {e}")
            conn.close()
            return

        if not order:
            await query.edit_message_text("❌ Commande introuvable!")
            return

        payment_id = order[13]  # nowpayments_id
        payment_status = self.check_payment_status(payment_id)

        if payment_status:
            status = payment_status.get('payment_status', 'waiting')

            if status in ['finished', 'confirmed']:
                # Paiement confirmé
                try:
                    cursor.execute('''
                        UPDATE orders 
                        SET payment_status = 'completed', 
                            completed_at = CURRENT_TIMESTAMP,
                            file_delivered = TRUE
                        WHERE order_id = ?
                    ''', (order_id,))

                    # ⭐ NOUVEAU : Créer payout vendeur automatique
                    payout_created = await self.auto_create_seller_payout(order_id)

                    # Mettre à jour stats produit
                    cursor.execute('''
                        UPDATE products 
                        SET sales_count = sales_count + 1
                        WHERE product_id = ?
                    ''', (order[3],))

                    # Mettre à jour stats vendeur
                    cursor.execute('''
                        UPDATE users 
                        SET total_sales = total_sales + 1,
                            total_revenue = total_revenue + ?
                        WHERE user_id = ?
                    ''', (order[7], order[4]))

                    conn.commit()
                    conn.close()
                except sqlite3.Error as e:
                    logger.error(f"Erreur mise à jour après paiement: {e}")
                    conn.close()
                    return

                # Message de succès
                payout_text = "✅ Payout vendeur créé automatiquement" if payout_created else "⚠️ Payout vendeur en attente"

                success_text = f"""🎉 **FÉLICITATIONS !**

    ✅ **Paiement confirmé** - Commande : {order_id}
    {payout_text}

    📚 **ACCÈS IMMÉDIAT À VOTRE FORMATION**"""

                keyboard = [
                    [InlineKeyboardButton("📥 Télécharger maintenant", callback_data=f'download_product_{order[3]}')],
                    [InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')]
                ]

                await query.edit_message_text(
                    success_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown')
            else:
                # Paiement en cours
                conn.close()
                await query.edit_message_text(
                    f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Confirmations en cours...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Rafraîchir", 
                                        callback_data=f'check_payment_{order_id}')
                    ]]))
        else:
            conn.close()
            await query.edit_message_text("❌ Erreur de vérification. Réessayez.")

    async def choose_random_referral(self, query, lang):
        """Choisir un code de parrainage aléatoire"""
        available_codes = self.get_available_referral_codes()

        if not available_codes:
            await query.edit_message_text(
                "❌ Aucun code disponible actuellement.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
                ]]))
            return

        # Prendre 3 codes aléatoires
        random_codes = random.sample(available_codes,
                                     min(3, len(available_codes)))

        keyboard = []
        for code in random_codes:
            keyboard.append([
                InlineKeyboardButton(f"🎯 Utiliser {code}",
                                     callback_data=f'use_referral_{code}')
            ])

        keyboard.extend([[
            InlineKeyboardButton("🔄 Autres codes",
                                 callback_data='choose_random_referral')
        ], [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')], [
            InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
        ]])

        codes_text = """🎲 **CODES DE PARRAINAGE DISPONIBLES**

Choisissez un code pour continuer votre achat :

💡 **Tous les codes sont équivalents**
🎁 **Votre parrain recevra sa commission**"""

        await query.edit_message_text(
            codes_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def validate_and_proceed(self, query, referral_code, lang):
        """Valider le code et procéder à l'achat"""
        if not self.validate_referral_code(referral_code):
            await query.edit_message_text(
                f"❌ **Code invalide :** `{referral_code}`\n\nVeuillez réessayer avec un code valide.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
                ]]),
                parse_mode='Markdown')
            return

        # Stocker le code validé
        user_cache = self.memory_cache.get(query.from_user.id, {})
        user_cache['validated_referral'] = referral_code
        user_cache['lang'] = lang
        self.memory_cache[query.from_user.id] = user_cache

        await query.edit_message_text(
            f"✅ **Code validé :** `{referral_code}`\n\nProcédons au paiement !",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Continuer vers le paiement", callback_data='proceed_to_payment')],
                [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
            ]),
            parse_mode='Markdown')



    async def show_crypto_options(self, query, lang):
        """Affiche les options de crypto pour le paiement"""
        user_id = query.from_user.id
        user_cache = self.memory_cache.get(user_id, {})

        # Vérifier le code de parrainage validé
        if 'validated_referral' not in user_cache:
            await query.edit_message_text("❌ Code de parrainage requis !",
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton(
                                                  "🎯 Entrer un code",
                                                  callback_data='buy_menu')
                                          ]]))
            return

        # Récupérer le produit
        product_id = user_cache.get('buying_product_id')
        if not product_id:
            await query.edit_message_text(
                "❌ Produit non trouvé !",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Chercher produit",
                                         callback_data='search_product')
                ]]))
            return

        product = self.get_product_by_id(product_id)
        if not product:
            await query.edit_message_text(
                "❌ Produit indisponible !",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 Chercher produit",
                                         callback_data='search_product')
                ]]))
            return

        cryptos = self.get_available_currencies()

        keyboard = []
        crypto_info = {
            'btc': ('₿ Bitcoin', '⚡ 10-30 min'),
            'eth': ('⟠ Ethereum', '⚡ 5-15 min'),
            'usdt': ('₮ Tether USDT', '⚡ 5-10 min'),
            'usdc': ('🟢 USD Coin (Ethereum)', '⚡ 5-10 min'),
            'bnb': ('🟡 BNB', '⚡ 2-5 min'),
            'sol': ('◎ Solana', '⚡ 1-2 min'),
            'ltc': ('Ł Litecoin', '⚡ 10-20 min'),
            'xrp': ('✕ XRP', '⚡ 1-3 min')
        }

        # Organiser en 2 colonnes
        for i in range(0, len(cryptos), 2):
            row = []
            for j in range(2):
                if i + j < len(cryptos):
                    crypto = cryptos[i + j]
                    name, speed = crypto_info.get(
                        crypto, (crypto.upper(), '⚡ 5-15 min'))
                    row.append(
                        InlineKeyboardButton(f"{name} {speed}",
                                             callback_data=f'pay_{crypto}'))
            keyboard.append(row)

        keyboard.append(
            [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')])
        keyboard.append(
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')])

        crypto_text = f"""💳 **CHOISIR VOTRE MOYEN DE PAIEMENT**

📦 **Produit :** {product['title']}
💰 **Prix :** {product['price_eur']}€
🎯 **Code parrainage :** `{user_cache['validated_referral']}`

🔐 **Sélectionnez votre crypto-monnaie préférée :**

✅ **Avantages :**
• Paiement 100% sécurisé
• Confirmation automatique
• Livraison instantanée après paiement
• Support prioritaire 24/7"""

        await query.edit_message_text(
            crypto_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def process_payment(self, query, crypto_currency, lang):
        """Traite le paiement avec code de parrainage"""
        user_id = query.from_user.id
        user_cache = self.memory_cache.get(user_id, {})

        # Vérifier les données nécessaires
        if 'validated_referral' not in user_cache or 'buying_product_id' not in user_cache:
            await query.edit_message_text("❌ Données de commande manquantes !",
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton(
                                                  "🔙 Recommencer",
                                                  callback_data='buy_menu')
                                          ]]))
            return

        product_id = user_cache['buying_product_id']
        referral_code = user_cache['validated_referral']

        product = self.get_product_by_id(product_id)
        if not product:
            await query.edit_message_text("❌ Produit indisponible !")
            return

        await query.edit_message_text("⏳ Création de votre commande...")

        # Générer order_id unique
        order_id = f"MP{datetime.now().strftime('%y%m%d')}{user_id}{uuid.uuid4().hex[:4].upper()}"

        # Calculer les montants
        product_price_eur = product['price_eur']
        # Éviter de bloquer la boucle avec requests
        rate = await asyncio.to_thread(self.get_exchange_rate)
        product_price_usd = product_price_eur * rate

        platform_commission = product_price_eur * PLATFORM_COMMISSION_RATE
        seller_revenue = product_price_eur - platform_commission

        # Créer paiement NOWPayments
        payment_data = await asyncio.to_thread(
            self.create_payment, product_price_usd, crypto_currency, order_id
        )

        if payment_data:
            # Sauver en base
            conn = self.get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    '''
                    INSERT INTO orders 
                    (order_id, buyer_user_id, product_id, seller_user_id,
                     product_price_eur, platform_commission, seller_revenue,
                     crypto_currency, crypto_amount, nowpayments_id, payment_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_id, user_id, product_id, product['seller_user_id'],
                      product_price_eur, platform_commission, seller_revenue,
                      crypto_currency,
                      payment_data.get('pay_amount', 0), payment_data.get('payment_id'),
                      payment_data.get('pay_address', '')))
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                logger.error(f"Erreur création commande: {e}")
                conn.close()
                return

            # Nettoyer le cache
            if user_id in self.memory_cache:
                del self.memory_cache[user_id]

            crypto_amount = payment_data.get('pay_amount', 0)
            payment_address = payment_data.get('pay_address', '')

            payment_text = f"""💳 **PAIEMENT EN COURS**

📋 **Commande :** `{order_id}`
📦 **Produit :** {product['title']}
💰 **Montant exact :** `{crypto_amount}` {crypto_currency.upper()}

📍 **Adresse de paiement :**
`{payment_address}`

⏰ **Validité :** 30 minutes
🔄 **Confirmations :** 1-3 selon réseau

⚠️ **IMPORTANT :**
• Envoyez **exactement** le montant indiqué
• Utilisez uniquement du {crypto_currency.upper()}
• La détection est automatique"""

            keyboard = [
                [InlineKeyboardButton("🔄 Vérifier paiement", callback_data=f'check_payment_{order_id}')],
                [InlineKeyboardButton("💬 Support", callback_data='support_menu')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
            ]

            await query.edit_message_text(
                payment_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        else:
            await query.edit_message_text(
                "❌ Erreur lors de la création du paiement. Vérifiez la configuration NOWPayments.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Réessayer",
                                         callback_data='proceed_to_payment')
                ]]))

    async def check_payment_handler(self, query, order_id, lang):
        """Vérifie le statut du paiement, met à jour les entités et crée un payout vendeur."""
        await query.edit_message_text("🔍 Vérification en cours...")

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id, ))
            order = cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération commande: {e}")
            conn.close()
            return

        if not order:
            await query.edit_message_text("❌ Commande introuvable!")
            return

        # Index corrects: nowpayments_id = 11
        payment_id = order[11]
        # Exécuter l'appel bloquant dans un thread pour ne pas bloquer la boucle
        payment_status = await asyncio.to_thread(self.check_payment_status, payment_id)

        if payment_status:
            status = payment_status.get('payment_status', 'waiting')

            if status in ['finished', 'confirmed']:
                try:
                    cursor.execute(
                        '''
                        UPDATE orders 
                        SET payment_status = 'completed', 
                            completed_at = CURRENT_TIMESTAMP,
                            file_delivered = TRUE
                        WHERE order_id = ?
                    ''', (order_id, ))

                    cursor.execute(
                        '''
                        UPDATE products 
                        SET sales_count = sales_count + 1
                        WHERE product_id = ?
                    ''', (order[3], ))

                    cursor.execute(
                        '''
                        UPDATE users 
                        SET total_sales = total_sales + 1,
                            total_revenue = total_revenue + ?
                        WHERE user_id = ?
                    ''', (order[6], order[4]))



                    conn.commit()
                except sqlite3.Error as e:
                    logger.error(f"Erreur mise à jour après paiement: {e}")
                    conn.rollback()
                    conn.close()
                    return

                try:
                    payout_created = await self.auto_create_seller_payout(order_id)
                except Exception as e:
                    logger.error(f"Erreur auto payout: {e}")
                    payout_created = False
                finally:
                    conn.close()

                success_text = f"""🎉 **FÉLICITATIONS !**

✅ **Paiement confirmé** - Commande : {order_id}
{"✅ Paiement vendeur créé automatiquement" if payout_created else "⚠️ Paiement vendeur en attente"}

📚 **ACCÈS IMMÉDIAT À VOTRE FORMATION**"""

                keyboard = [[
                    InlineKeyboardButton(
                        "📥 Télécharger maintenant",
                        callback_data=f'download_product_{order[3]}')
                ], [
                    InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')
                ]]

                await query.edit_message_text(
                    success_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown')
            else:
                conn.close()
                await query.edit_message_text(
                    f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Les confirmations peuvent prendre 5-30 min",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Rafraîchir", callback_data=f'check_payment_{order_id}')],
                        [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
                    ]))
        else:
            conn.close()
            await query.edit_message_text(
                "❌ Erreur de vérification. Réessayez.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Réessayer", callback_data=f'check_payment_{order_id}')],
                    [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
                ]))

    async def sell_menu(self, query, lang):
        """Menu vendeur"""
        user_data = await self.get_user(query.from_user.id)

        if user_data and user_data['is_seller']:
            await self.seller_dashboard(query, lang)
            return

        keyboard = [
            [InlineKeyboardButton("🚀 Devenir vendeur", callback_data='create_seller')],
            [InlineKeyboardButton("📋 Conditions & avantages", callback_data='seller_info')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        sell_text = """📚 **VENDRE VOS FORMATIONS**

🎯 **Monétisez votre expertise**

💰 **Avantages vendeur :**
• 95% des revenus pour vous (5% commission plateforme)
• Paiements automatiques en crypto
• Gestion complète de vos produits
• Support marketing inclus
• Interface intuitive

🔐 **Sécurité**
• Récupération via email + code
• Adresse Solana de paiement sécurisée
• Contrôle total de vos fonds

Prêt à commencer ?"""

        await query.edit_message_text(
            sell_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def create_seller_prompt(self, query, lang):
        """Demande les informations pour créer un compte vendeur"""
        self.memory_cache[query.from_user.id] = {
            'creating_seller': True,
            'step': 'name',
            'lang': lang
        }

        await query.edit_message_text("""🚀 **CRÉATION COMPTE VENDEUR**

Pour créer votre compte vendeur, nous avons besoin de quelques informations.

👤 **Étape 1/4 : Nom public**

Saisissez le nom qui apparaîtra sur vos formations :""",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton(
                                              "❌ Annuler",
                                              callback_data='sell_menu')
                                      ]]))

    async def seller_login_menu(self, query, lang):
        """Menu de connexion vendeur"""
        await query.edit_message_text(
            """🔐 **CONNEXION VENDEUR**

Aucune action requise: votre identité Telegram est utilisée.

Si votre compte vendeur est déjà activé, vous accéderez directement à votre dashboard.

Sinon, créez votre compte vendeur en quelques étapes.""",
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("🏪 Mon dashboard", callback_data='seller_dashboard'),
                InlineKeyboardButton("🚀 Créer un compte", callback_data='create_seller')
            ], [
                InlineKeyboardButton("🔙 Retour", callback_data='back_main')
            ]]),
            parse_mode='Markdown')

    async def seller_dashboard(self, query, lang):
        """Dashboard vendeur complet"""
        user_data = await self.get_user(query.from_user.id)
        # Si on arrive via un bouton et que le flag login est set, on autorise;
        # sinon on redirige vers la connexion
        if not user_data or not user_data['is_seller']:
            await query.edit_message_text(
                "❌ Accès non autorisé.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Accéder à mon compte", callback_data='access_account')]])
            )
            return
        if not self.is_seller_logged_in(query.from_user.id):
            # Ne plus forcer la saisie: proposer le menu d'accès compte
            await self.access_account_prompt(query, lang)
            return

        # Récupérer les stats vendeur
        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Produits actifs
        try:
            cursor.execute(
                '''
                SELECT COUNT(*) FROM products 
                WHERE seller_user_id = ? AND status = 'active'
            ''', (query.from_user.id, ))
            active_products = cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération produits actifs: {e}")
            active_products = 0

        # Ventes du mois
        try:
            cursor.execute(
                '''
                SELECT COUNT(*), COALESCE(SUM(seller_revenue), 0)
                FROM orders 
                WHERE seller_user_id = ? AND payment_status = 'completed'
                AND datetime(created_at) >= datetime('now', 'start of month')
            ''', (query.from_user.id, ))
            month_stats = cursor.fetchone()
            month_sales = month_stats[0]
            month_revenue = month_stats[1]
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération ventes mois: {e}")
            month_sales = 0
            month_revenue = 0

        conn.close()

        dashboard_text = f"""🏪 **DASHBOARD VENDEUR**

👋 Bienvenue **{user_data['seller_name']}** !

📊 **Statistiques :**
• 📦 Produits actifs : {active_products}
• 🛒 Ventes ce mois : {month_sales}
• 💰 Revenus ce mois : {month_revenue:.2f}€
• ⭐ Note moyenne : {user_data['seller_rating']:.1f}/5

💳 **Wallet :** {'✅ Configuré' if user_data['seller_solana_address'] else '❌ À configurer'}"""

        keyboard = [
            [InlineKeyboardButton("➕ Ajouter un produit", callback_data='add_product')],
            [InlineKeyboardButton("📦 Mes produits", callback_data='my_products')],
            [InlineKeyboardButton("💰 Mon wallet", callback_data='my_wallet')],
            [InlineKeyboardButton("📊 Analytics", callback_data='seller_analytics')],
            [InlineKeyboardButton("⚙️ Paramètres", callback_data='seller_settings')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        await query.edit_message_text(
            dashboard_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def add_product_prompt(self, query, lang):
        """Demande les informations pour ajouter un produit"""
        user_data = await self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            await query.edit_message_text(
                "❌ Connectez-vous d'abord (email + code)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Accéder à mon compte", callback_data='access_account')]])
            )
            return

        self.memory_cache[query.from_user.id] = {
            'adding_product': True,
            'step': 'title',
            'product_data': {},
            'lang': lang
        }

        await query.edit_message_text("""➕ **AJOUTER UN NOUVEAU PRODUIT**

📝 **Étape 1/5 : Titre**

Saisissez le titre de votre formation :

💡 **Conseil :** Soyez précis et accrocheur
*Exemple : "Guide Complet Trading Crypto 2025"*""",
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton(
                                              "❌ Annuler",
                                              callback_data='seller_dashboard')
                                      ]]),
                                      parse_mode='Markdown')

    async def show_my_products(self, query, lang):
        """Affiche les produits du vendeur"""
        user_data = await self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            await query.edit_message_text(
                "❌ Connectez-vous d'abord (email + code)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Accéder à mon compte", callback_data='access_account')]])
            )
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                SELECT product_id, title, price_eur, sales_count, status, created_at
                FROM products 
                WHERE seller_user_id = ?
                ORDER BY created_at DESC
            ''', (query.from_user.id, ))

            products = cursor.fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération produits vendeur: {e}")
            conn.close()
            return

        if not products:
            products_text = """📦 **MES PRODUITS**

Aucun produit créé pour le moment.

Commencez dès maintenant à monétiser votre expertise !"""

            keyboard = [
                [InlineKeyboardButton("➕ Créer mon premier produit", callback_data='add_product')],
                [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
            ]
        else:
            products_text = f"📦 **MES PRODUITS** ({len(products)})\n\n"

            keyboard = []
            for product in products[:10]:  # Limiter à 10 pour l'affichage
                status_icon = {
                    "active": "✅",
                    "inactive": "⏸️",
                    "banned": "❌"
                }.get(product[4], "❓")
                products_text += f"{status_icon} `{product[0]}`\n"
                products_text += f"💰 {product[2]}€ • 🛒 {product[3]} ventes\n\n"

                keyboard.append([
                    InlineKeyboardButton(
                        f"✏️ {product[1][:30]}...",
                        callback_data=f'edit_product_{product[0]}')
                ])

            keyboard.extend([[
                InlineKeyboardButton("➕ Nouveau produit",
                                     callback_data='add_product')
            ],
                             [
                                 InlineKeyboardButton(
                                     "🔙 Dashboard",
                                     callback_data='seller_dashboard')
                             ], [
                                 InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
                             ]])

        await query.edit_message_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def show_wallet(self, query, lang):
        """Affiche l'adresse Solana du vendeur"""
        user_data = await self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            await query.edit_message_text(
                "❌ Connectez-vous d'abord (email + code)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Accéder à mon compte", callback_data='access_account')]])
            )
            return

        if not user_data['seller_solana_address']:
            await query.edit_message_text(
                """💳 **COMPTE DE PAIEMENT NON CONFIGURÉ**

Pour configurer votre compte de paiement, vous devez d'abord devenir vendeur.

Votre adresse Solana sera configurée lors de l'inscription.""",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Devenir vendeur", callback_data='create_seller')],
                    [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')],
                    [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
                ])
            )
            return

        solana_address = user_data['seller_solana_address']

        # Récupérer solde (optionnel)
        balance = await get_solana_balance_display(solana_address, self.http_client)

        # Calculer payouts en attente
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COALESCE(SUM(total_amount_sol), 0) 
                    FROM seller_payouts 
                    WHERE seller_user_id = ? AND payout_status = 'pending'
                ''', (query.from_user.id,))
                pending_amount = cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération payouts en attente: {e}")
            pending_amount = 0

        wallet_text = f"""💰 **MON COMPTE DE PAIEMENT**

📍 **Adresse Solana :** `{solana_address}`

💎 **Solde actuel :** {balance:.6f} SOL
⏳ **Paiements en attente :** {pending_amount:.6f} SOL

💸 **Système de paiements :**
- Traités quotidiennement
- 95% de vos ventes
- Commission plateforme : 5%"""

        keyboard = [
            [InlineKeyboardButton("📊 Historique payouts", callback_data='payout_history')],
            [InlineKeyboardButton("📋 Copier adresse", callback_data='copy_address')],
            [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        await query.edit_message_text(
            wallet_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def marketplace_stats(self, query, lang):
        """Statistiques globales de la marketplace"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()

                # Stats générales
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM users WHERE is_seller = TRUE')
                total_sellers = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM products WHERE status = "active"')
                total_products = cursor.fetchone()[0]

                cursor.execute(
                    'SELECT COUNT(*) FROM orders WHERE payment_status = "completed"')
                total_sales = cursor.fetchone()[0]

                cursor.execute(
                    'SELECT COALESCE(SUM(product_price_eur), 0) FROM orders WHERE payment_status = "completed"'
                )
                total_volume = cursor.fetchone()[0]

                # Top catégories
                cursor.execute('''
                    SELECT c.name, c.icon, COUNT(p.id) as product_count
                    FROM categories c
                    LEFT JOIN products p ON c.name = p.category
                    GROUP BY c.name
                    ORDER BY product_count DESC
                    LIMIT 5
                ''')
                top_categories = cursor.fetchall()

        except sqlite3.Error as e:
            logger.error(f"Erreur récupération stats marketplace: {e}")
            return

        stats_text = f"""📊 **STATISTIQUES MARKETPLACE**

🎯 **Vue d'ensemble :**
• 👥 Utilisateurs : {total_users:,}
• 🏪 Vendeurs actifs : {total_sellers:,}
• 📦 Formations disponibles : {total_products:,}
• 🛒 Ventes totales : {total_sales:,}
• 💰 Volume échangé : {total_volume:,.2f}€

🔥 **Top catégories :**"""

        for cat in top_categories:
            stats_text += f"\n{cat[1]} {cat[0]} : {cat[2]} formations"

        keyboard = [
            [InlineKeyboardButton("🔥 Meilleures ventes", callback_data='category_bestsellers')],
            [InlineKeyboardButton("🆕 Nouveautés", callback_data='category_new')],
            [InlineKeyboardButton("🏪 Devenir vendeur", callback_data='sell_menu')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def handle_text_message(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire principal des messages texte"""
        user_id = update.effective_user.id
        message_text = update.message.text

        if user_id not in self.memory_cache:
            await update.message.reply_text(
                "💬 Utilisez le menu principal pour naviguer.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu principal",
                                         callback_data='back_main')
                ]]))
            return

        user_state = self.memory_cache[user_id]

        # === RECHERCHE PRODUIT ===
        if user_state.get('waiting_for_product_id'):
            await self.process_product_search(update, message_text)

        # === CRÉATION VENDEUR ===
        elif user_state.get('creating_seller'):
            await self.process_seller_creation(update, message_text)

        # === CONNEXION VENDEUR ===
        elif user_state.get('seller_login'):
            await self.process_seller_login(update, message_text)

        # === AJOUT PRODUIT ===
        elif user_state.get('adding_product'):
            await self.process_product_addition(update, message_text)

        # === SAISIE CODE PARRAINAGE ===
        elif user_state.get('waiting_for_referral'):
            await self.process_referral_input(update, message_text)

        # === CRÉATION TICKET SUPPORT ===
        elif user_state.get('creating_ticket'):
            await self.process_support_ticket(update, message_text)

        # === RÉCUPÉRATION PAR EMAIL ===
        elif user_state.get('waiting_for_recovery_email'):
            await self.process_recovery_email(update, message_text)

        # === RÉCUPÉRATION CODE ===
        elif user_state.get('waiting_for_recovery_code'):
            await self.process_recovery_code(update, message_text)

        # === CONNEXION (email + code fourni lors de la création) ===
        elif user_state.get('login_wait_email'):
            await self.process_login_email(update, message_text)
        elif user_state.get('login_wait_code'):
            await self.process_login_code(update, message_text)

        # === PARAMÈTRES VENDEUR ===
        elif user_state.get('editing_settings'):
            await self.process_seller_settings(update, message_text)

        # === ADMIN RECHERCHES/SUSPENSIONS ===
        elif user_state.get('admin_search_user'):
            await self.process_admin_search_user(update, message_text)
        elif user_state.get('admin_search_product'):
            await self.process_admin_search_product(update, message_text)
        elif user_state.get('admin_suspend_product'):
            await self.process_admin_suspend_product(update, message_text)

        # === DÉFAUT ===
        else:
            await update.message.reply_text(
                "💬 Pour nous contacter, utilisez le système de support.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎫 Créer un ticket",
                                         callback_data='create_ticket'),
                    InlineKeyboardButton("🏠 Menu principal",
                                         callback_data='back_main')
                ]]))

    async def process_product_search(self, update, message_text):
        """Traite la recherche de produit par ID"""
        user_id = update.effective_user.id
        user_state = self.memory_cache[user_id]

        # Nettoyer et valider l'ID
        product_id = message_text.strip().upper()

        # Format attendu: TBF-YYMM-XXXXXX (lettres sans I/O et chiffres sans 0/1)
        if not re.match(r'^TBF-\d{4}-[A-HJ-NP-Z2-9]{6}$', product_id):
            await update.message.reply_text(
                f"❌ **Format ID invalide :** `{product_id}`\n\n💡 **Format attendu :** `TBF-2501-ABC123`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
                ]]),
                parse_mode='Markdown')
            return

        # Chercher le produit
        product = self.get_product_by_id(product_id)

        # Nettoyer cache
        del self.memory_cache[user_id]

        if product:
            await self.show_product_details_from_search(update, product)
        else:
            await update.message.reply_text(
                f"❌ **Produit introuvable :** `{product_id}`\n\nVérifiez l'ID ou explorez les catégories.",
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("📂 Parcourir catégories",
                                             callback_data='browse_categories')
                    ],
                     [
                         InlineKeyboardButton("🔙 Menu achat",
                                              callback_data='buy_menu')
                     ]]),
                parse_mode='Markdown')

    async def show_product_details_from_search(self, update, product):
        """Affiche les détails d'un produit trouvé par recherche"""
        stars = "⭐" * int(
            product['rating']) if product['rating'] > 0 else "⭐⭐⭐⭐⭐"

        product_text = f"""📦 **{product['title']}**

👤 **Vendeur :** {product['seller_name']} ({product['seller_rating']:.1f}/5)
📂 **Catégorie :** {product['category']}
💰 **Prix :** {product['price_eur']}€

📖 **Description :**
{product['description'] or 'Aucune description disponible'}

📊 **Statistiques :**
• {stars} ({product['reviews_count']} avis)
• 👁️ {product['views_count']} vues
• 🛒 {product['sales_count']} ventes

📁 **Fichier :** {product['file_size_mb']:.1f} MB"""

        keyboard = [[
            InlineKeyboardButton(
                "🛒 Acheter maintenant",
                callback_data=f'buy_product_{product["product_id"]}')
        ],
                    [
                        InlineKeyboardButton("📂 Autres produits",
                                             callback_data='browse_categories')
                    ],
                    [
                        InlineKeyboardButton("🔙 Menu achat",
                                             callback_data='buy_menu')
                    ]]

        await update.message.reply_text(
            product_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def process_seller_creation(self, update, message_text):
        """Flow création vendeur : nom → bio → email → adresse solana"""
        user_id = update.effective_user.id
        user_state = self.memory_cache[user_id]
        step = user_state.get('step')

        if step == 'name':
            # Étape 1 : Nom vendeur
            if len(message_text) < 2 or len(message_text) > 50:
                await update.message.reply_text("❌ Le nom doit contenir entre 2 et 50 caractères.")
                return

            user_state['seller_name'] = message_text
            user_state['step'] = 'bio'

            await update.message.reply_text(
                f"✅ **Nom :** {message_text}\n\n📝 **Étape 2/4 : Biographie**\n\nDecrivez votre expertise :",
                parse_mode='Markdown'
            )

        elif step == 'bio':
            # Étape 2 : Bio
            user_state['seller_bio'] = message_text[:500]
            user_state['step'] = 'email'

            await update.message.reply_text(
                f"""✅ **Bio sauvegardée**

    📧 **Étape 3/4 : Email de récupération**

    Saisissez un email valide pour récupérer votre compte :

    ⚠️ **Important :** Cet email servira à récupérer votre compte vendeur""",
                parse_mode='Markdown'
            )

        elif step == 'email':
            # Étape 3 : Email
            email = message_text.strip().lower()

            if not validate_email(email):
                await update.message.reply_text("❌ **Email invalide**\n\nFormat attendu : exemple@domaine.com")
                return

            user_state['recovery_email'] = email
            user_state['step'] = 'solana_address'

            await update.message.reply_text(
                f"""✅ **Email :** {email}

    📍 **Étape 4/4 : Adresse Solana**

    Saisissez votre adresse Solana pour recevoir vos paiements :

    💡 **Comment trouver votre adresse :**
    - Ouvrez Phantom, Solflare ou votre wallet Solana
    - Cliquez "Receive" ou "Recevoir"
    - Copiez l'adresse (format : `5Fxk...abc`)""",
                parse_mode='Markdown'
            )

        elif step == 'solana_address':
            # Étape 4 : Adresse Solana
            solana_address = message_text.strip()

            if not validate_solana_address(solana_address):
                await update.message.reply_text("❌ **Adresse Solana invalide**\n\nVérifiez le format depuis votre wallet")
                return

            # Créer le compte vendeur
            user_cache = self.memory_cache[user_id]
            result = self.create_seller_account_with_recovery(
                user_id,
                user_cache['seller_name'],
                user_cache['seller_bio'],
                user_cache['recovery_email'],
                solana_address
            )

            # Nettoyer le cache mais conserver l'état de connexion
            self.reset_user_state_preserve_login(user_id)

            if result['success']:
                # Marquer l'utilisateur comme connecté (évite la boucle d'accès)
                self.set_seller_logged_in(user_id, True)
                await update.message.reply_text(f"""🎉 **COMPTE VENDEUR CRÉÉ !**

    ✅ **Nom :** {user_cache['seller_name']}
    ✅ **Email :** {user_cache['recovery_email']}
    ✅ **Adresse :** `{solana_address}`

    🔐 **CODE DE RÉCUPÉRATION :** `{result['recovery_code']}`

    ⚠️ **SAUVEGARDEZ CE CODE !**
    - Notez-le dans un endroit sûr
    - Il vous permet de récupérer votre compte
    - Ne le partagez jamais

    💰 **Comment ça marche :**
    1. Vos clients paient en BTC/ETH/USDT/etc.
    2. Nous recevons en Solana
    3. Nous vous envoyons 95% sur votre adresse
    4. Commission plateforme : 5%""",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ J'ai sauvegardé mon code", 
                                            callback_data='seller_dashboard')]
                    ]),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Erreur création compte")

    async def process_seller_login(self, update, message_text):
        """Traite la connexion vendeur"""
        user_id = update.effective_user.id
        # Auth: on vérifie simplement que l'utilisateur est vendeur
        if self.authenticate_seller(user_id, ""):
            await update.message.reply_text(
                "✅ **Connexion réussie !**\n\nBienvenue dans votre espace vendeur.",
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton("🏪 Mon dashboard",
                                         callback_data='seller_dashboard'),
                    InlineKeyboardButton("💰 Mon wallet",
                                         callback_data='my_wallet')
                ]]))
        else:
            await update.message.reply_text(
                "❌ **Vous n'êtes pas encore vendeur**\n\nCréez votre compte en quelques étapes.",
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton("🚀 Créer un compte",
                                         callback_data='create_seller'),
                    InlineKeyboardButton("🔙 Retour",
                                         callback_data='back_main')
                ]]))

    async def process_product_addition(self, update, message_text):
        """Traite l'ajout de produit étape par étape"""
        user_id = update.effective_user.id
        user_state = self.memory_cache[user_id]
        step = user_state.get('step')
        product_data = user_state.get('product_data', {})

        if step == 'title':
            if len(message_text) < 5 or len(message_text) > 100:
                await update.message.reply_text(
                    "❌ Le titre doit contenir entre 5 et 100 caractères.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Annuler",
                                             callback_data='seller_dashboard')
                    ]]))
                return

            product_data['title'] = message_text
            user_state['step'] = 'description'

            await update.message.reply_text(
                f"✅ **Titre :** {message_text}\n\n📝 **Étape 2/5 : Description**\n\nDecrivez votre formation (contenu, objectifs, prérequis...) :",
                parse_mode='Markdown')

# Dans process_product_addition(), REMPLACER la section step == 'description' :

        elif step == 'description':
            product_data['description'] = message_text[:1000]
            user_state['step'] = 'category'

            # Afficher les catégories avec des boutons
            conn = self.get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT name, icon FROM categories ORDER BY name')
                categories = cursor.fetchall()
                conn.close()
            except sqlite3.Error as e:
                logger.error(f"Erreur récupération catégories: {e}")
                conn.close()
                return

            keyboard = []
            for cat_name, cat_icon in categories:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{cat_icon} {cat_name}",
                        callback_data=f'set_product_category_{cat_name.replace(" ", "_").replace("&", "and")}'
                    )
                ])

            keyboard.append([
                InlineKeyboardButton("❌ Annuler", callback_data='seller_dashboard')
            ])

            await update.message.reply_text(
                "✅ **Description sauvegardée**\n\n📂 **Étape 3/5 : Catégorie**\n\nChoisissez la catégorie :",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')

        elif step == 'price':
            try:
                price = float(message_text.replace(',', '.'))
                if price < 1 or price > 5000:
                    raise ValueError("Prix hors limites")

                product_data['price_eur'] = price
                product_data['price_usd'] = price * self.get_exchange_rate()
                user_state['step'] = 'file'

                await update.message.reply_text(
                    f"✅ **Prix :** {price}€\n\n📁 **Étape 5/5 : Fichier**\n\nEnvoyez maintenant votre fichier de formation :\n\n📎 **Formats acceptés :** {', '.join(SUPPORTED_FILE_TYPES)}\n📏 **Taille max :** {MAX_FILE_SIZE_MB}MB",
                    parse_mode='Markdown')

            except (ValueError, TypeError):
                await update.message.reply_text(
                    "❌ **Prix invalide**\n\nSaisissez un nombre entre 1 et 5000.\n*Exemples : 29.99 ou 150*",
                    parse_mode='Markdown')

    async def process_support_ticket(self, update: Update, message_text: str):
        user_id = update.effective_user.id
        state = self.memory_cache[user_id]
        step = state.get('step')

        if step == 'subject':
            state['subject'] = message_text[:100]
            state['step'] = 'message'
            await update.message.reply_text("Entrez votre message détaillé:")
            return

        if step == 'message':
            subject = state.get('subject', 'Sans sujet')
            content = message_text[:2000]

            ticket_id = f"TKT-{datetime.utcnow().strftime('%y%m%d')}-{random.randint(1000,9999)}"
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO support_tickets (user_id, ticket_id, subject, message)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, ticket_id, subject, content))
                conn.commit()
                conn.close()
                self.memory_cache.pop(user_id, None)
                await update.message.reply_text(
                    f"🎫 Ticket créé: {ticket_id}\nNotre équipe vous répondra bientôt.")
            except Exception as e:
                logger.error(f"Erreur création ticket: {e}")
                await update.message.reply_text("❌ Erreur lors de la création du ticket.")

    async def process_seller_settings(self, update: Update, message_text: str):
        user_id = update.effective_user.id
        state = self.memory_cache.get(user_id, {})
        step = state.get('step')
        if step == 'edit_name':
            new_name = message_text.strip()[:50]
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET seller_name = ? WHERE user_id = ?', (new_name, user_id))
                conn.commit()
                conn.close()
                self.memory_cache.pop(user_id, None)
                await update.message.reply_text("✅ Nom mis à jour.")
            except Exception as e:
                logger.error(f"Erreur maj nom vendeur: {e}")
                await update.message.reply_text("❌ Erreur mise à jour nom.")
        elif step == 'edit_bio':
            new_bio = message_text.strip()[:500]
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET seller_bio = ? WHERE user_id = ?', (new_bio, user_id))
                conn.commit()
                conn.close()
                self.memory_cache.pop(user_id, None)
                await update.message.reply_text("✅ Biographie mise à jour.")
            except Exception as e:
                logger.error(f"Erreur maj bio vendeur: {e}")
                await update.message.reply_text("❌ Erreur mise à jour bio.")

    async def process_admin_search_user(self, update: Update, message_text: str):
        admin_id = update.effective_user.id
        self.memory_cache.pop(admin_id, None)
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                # Essayer par user_id
                if message_text.isdigit():
                    cursor.execute('SELECT user_id, username, first_name, is_seller FROM users WHERE user_id = ?', (int(message_text),))
                else:
                    cursor.execute('SELECT user_id, username, first_name, is_seller FROM users WHERE user_id = ?', (0,))
                
                row = cursor.fetchone()
                if not row:
                    await update.message.reply_text("❌ Utilisateur non trouvé.")
                    return
                await update.message.reply_text(f"ID: {row[0]}\nUser: {row[1]}\nNom: {row[2]}\nVendeur: {bool(row[3])}")
        except Exception as e:
            logger.error(f"Erreur admin search user: {e}")
            await update.message.reply_text("❌ Erreur recherche utilisateur.")

    async def process_admin_search_product(self, update: Update, message_text: str):
        admin_id = update.effective_user.id
        self.memory_cache.pop(admin_id, None)
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT product_id, title, price_eur, status FROM products WHERE product_id = ?', (message_text.strip(),))
                row = cursor.fetchone()
                if not row:
                    await update.message.reply_text("❌ Produit non trouvé.")
                    return
                await update.message.reply_text(f"{row[0]} — {row[1]} — {row[2]}€ — {row[3]}")
        except Exception as e:
            logger.error(f"Erreur admin search product: {e}")
            await update.message.reply_text("❌ Erreur recherche produit.")

    async def process_admin_suspend_product(self, update: Update, message_text: str):
        admin_id = update.effective_user.id
        self.memory_cache.pop(admin_id, None)
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE products SET status='inactive' WHERE product_id = ?", (message_text.strip(),))
                conn.commit()
                await update.message.reply_text("✅ Produit suspendu si trouvé.")
        except Exception as e:
            logger.error(f"Erreur suspend product: {e}")
            await update.message.reply_text("❌ Erreur suspension produit.")

    async def process_referral_input(self, update, message_text):
        """Traite la saisie du code de parrainage"""
        user_id = update.effective_user.id
        user_cache = self.memory_cache.get(user_id, {})

        if self.validate_referral_code(message_text.strip()):
            # Code valide
            user_cache['validated_referral'] = message_text.strip()
            user_cache.pop('waiting_for_referral', None)
            self.memory_cache[user_id] = user_cache

            await update.message.reply_text(
                f"✅ **Code validé :** `{message_text.strip()}`\n\nProcédons au paiement !",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💳 Continuer vers le paiement",
                                         callback_data='proceed_to_payment'),
                    InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
                ]]),
                parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"❌ **Code invalide :** `{message_text.strip()}`\n\nVeuillez réessayer avec un code valide.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🎲 Choisir un code aléatoire",
                        callback_data='choose_random_referral'),
                    InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
                ]]),
                parse_mode='Markdown')

    async def change_language(self, query, lang):
        """Change la langue - CORRIGÉ"""
        user_id = query.from_user.id

        # Valider la langue
        supported_languages = ['fr', 'en']
        if lang not in supported_languages:
            await query.answer("❌ Langue non supportée")
            return

        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET language_code = ? WHERE user_id = ?', (lang, user_id))
                conn.commit()

            await query.answer(f"✅ Language changed to {lang}")
            await self.back_to_main(query)

        except Exception as e:
            logger.error(f"Erreur changement langue: {e}")
            await query.answer("❌ Erreur changement langue")

    # AJOUTER des textes anglais dans get_text() :
    def get_text(self, key: str, lang: str = 'fr') -> str:
        """Textes multilingues - COMPLÉTÉ"""
        texts = {
            'fr': {
                'welcome': """🏪 **TECHBOT MARKETPLACE**
    *La première marketplace crypto pour formations*

    🎯 **Découvrez des formations premium**
    📚 **Vendez vos connaissances**

    💰 **Wallet Solana intégré**

    Choisissez une option pour commencer :""",
                'buy_menu': '🛒 Acheter une formation',
                'sell_menu': '📚 Vendre vos formations',
                'seller_login': '🔐 Espace vendeur',
                'marketplace_stats': '📊 Stats marketplace',
                'back': '🔙 Retour',
                'error_occurred': '❌ Une erreur est survenue. Réessayez plus tard.',
            },
            'en': {
                'welcome': """🏪 **TECHBOT MARKETPLACE**
    *The first crypto marketplace for training courses*

    🎯 **Discover premium training courses**
    📚 **Sell your knowledge**  
    💰 **Integrated Solana wallet**

    Choose an option to start:""",
                'buy_menu': '🛒 Buy a course',
                'sell_menu': '📚 Sell your courses',
                'seller_login': '🔐 Seller space',
                'marketplace_stats': '📊 Marketplace stats',
                'back': '🔙 Back',
                'error_occurred': '❌ An error occurred. Please try again later.',
            }
        }
        return texts.get(lang, texts['fr']).get(key, key)

    async def back_to_main(self, query):
        """Menu principal avec récupération - NE DÉCONNECTE JAMAIS"""
        user_id = query.from_user.id
        user_data = self.get_user(user_id)
        lang = user_data['language_code'] if user_data else 'fr'
        is_seller = user_data and user_data['is_seller']
        is_logged = self.is_seller_logged_in(user_id)

        # Ne jamais déconnecter automatiquement
        # L'état de connexion est préservé

        keyboard = [
            [InlineKeyboardButton("🛒 Acheter une formation", callback_data='buy_menu')],
            [InlineKeyboardButton("📚 Vendre vos formations", callback_data='sell_menu')],
            [InlineKeyboardButton("🔑 Accéder à mon compte", callback_data='access_account')]
        ]

        # Accès rapide espace vendeur si déjà vendeur ET connecté
        if is_seller and is_logged:
            keyboard.append([
                InlineKeyboardButton("🏪 Mon espace vendeur", callback_data='seller_dashboard')
            ])

        keyboard.extend([
            [InlineKeyboardButton("📊 Stats marketplace", callback_data='marketplace_stats')],
            [InlineKeyboardButton("🆘 Support & aide", callback_data='support_menu')],
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data='lang_fr'),
                InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')
            ]
        ])

        await query.edit_message_text(
            """🏪 **TECHBOT MARKETPLACE**
*Plateforme de formations digitales avec paiements crypto*

🎯 **Découvrez des formations premium**
📚 **Monétisez votre expertise**  
💳 **Paiements sécurisés en crypto**

Choisissez une option pour commencer :""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def account_recovery_menu(self, query, lang):
        """Menu de récupération de compte"""
        await query.edit_message_text("""🔐 **RÉCUPÉRATION COMPTE VENDEUR**

Si vous avez perdu l'accès à votre compte :

📧 **Récupération automatique :**
- Saisissez votre email de récupération
- Entrez votre code à 6 chiffres
- Accès restauré instantanément

🎫 **Support manuel :**
- Contactez notre équipe avec preuves""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📧 Récupération par email", callback_data='recovery_by_email')],
                [InlineKeyboardButton("🎫 Contacter support", callback_data='create_ticket')],
                [InlineKeyboardButton("🔙 Retour", callback_data='back_main')]
            ]),
            parse_mode='Markdown'
        )

    async def recovery_by_email_prompt(self, query, lang):
        """Demande l'email pour récupération"""
        self.memory_cache[query.from_user.id] = {
            'waiting_for_recovery_email': True,
            'lang': lang
        }

        await query.edit_message_text("""📧 **RÉCUPÉRATION PAR EMAIL**

Saisissez l'email de votre compte vendeur :

✍️ **Tapez votre email :**""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Retour", callback_data='account_recovery')]
            ]))

    async def process_recovery_email(self, update: Update, message_text: str):
        """Traite l'entrée d'email et envoie un code si l'email existe."""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        if not validate_email(email):
            await update.message.reply_text("❌ Email invalide. Recommencez.")
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT user_id FROM users WHERE recovery_email = ?', (email,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                await update.message.reply_text("❌ Email non trouvé.")
                self.memory_cache.pop(user_id, None)
                return

            # Générer un nouveau code (stocké en hash)
            recovery_code = f"{random.randint(100000, 999999)}"
            code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()
            cursor.execute('UPDATE users SET recovery_code_hash = ? WHERE recovery_email = ?', (code_hash, email))
            conn.commit()
            conn.close()

            # Envoyer l'email si SMTP configuré
            if SMTP_SERVER and SMTP_EMAIL and SMTP_PASSWORD:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = SMTP_EMAIL
                    msg['To'] = email
                    msg['Subject'] = "Code de récupération TechBot"
                    body = f"Votre code de récupération: {recovery_code}"
                    msg.attach(MIMEText(body, 'plain'))

                    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                    server.starttls()
                    server.login(SMTP_EMAIL, SMTP_PASSWORD)
                    server.sendmail(SMTP_EMAIL, email, msg.as_string())
                    server.quit()
                except Exception as e:
                    logger.error(f"Erreur envoi email: {e}")

            # Poursuivre le flow: demander le code à l'utilisateur
            self.memory_cache[user_id] = {'waiting_for_recovery_code': True, 'email': email}
            await update.message.reply_text(
                "📧 Code envoyé. Entrez votre code à 6 chiffres:")
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération par email: {e}")
            conn.close()
            await update.message.reply_text("❌ Erreur interne.")

    async def process_recovery_code(self, update: Update, message_text: str):
        """Valide le code de récupération et réactive l'accès vendeur."""
        user_id = update.effective_user.id
        code = message_text.strip()
        state = self.memory_cache.get(user_id, {})
        email = state.get('email')
        if not email or not code.isdigit() or len(code) != 6:
            await update.message.reply_text("❌ Code invalide.")
            return

        code_hash = hashlib.sha256(code.encode()).hexdigest()
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE recovery_email = ? AND recovery_code_hash = ?', (email, code_hash))
            row = cursor.fetchone()
            if not row:
                conn.close()
                await update.message.reply_text("❌ Code incorrect.")
                return

            # Réactiver vendeur si besoin (ici on s'assure qu'il reste vendeur)
            cursor.execute('UPDATE users SET is_seller = TRUE WHERE user_id = ?', (row[0],))
            conn.commit()
            conn.close()

            # Marquer l'utilisateur comme connecté pour éviter toute boucle
            self.set_seller_logged_in(user_id, True)

            self.reset_user_state_preserve_login(user_id)
            await update.message.reply_text(
                "✅ Vérification réussie. Accédez à votre dashboard.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Mon dashboard", callback_data='seller_dashboard')]])
            )
        except Exception as e:
            logger.error(f"Erreur vérification code: {e}")
            await update.message.reply_text("❌ Erreur interne.")

    async def process_login_email(self, update: Update, message_text: str):
        """Étape 1 du login: saisir l'email enregistré lors de la création vendeur."""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        if not validate_email(email):
            await update.message.reply_text("❌ Email invalide. Recommencez.")
            return
        # Vérifier l'existence de l'email
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_id = ? AND recovery_email = ?', (user_id, email))
            row = cursor.fetchone()
            conn.close()
            if not row:
                await update.message.reply_text("❌ Email non associé à votre compte Telegram.")
                return
            # Passer à l'étape code
            self.memory_cache[user_id] = {'login_wait_code': True, 'login_email': email}
            await update.message.reply_text("✉️ Email validé. Entrez votre code de récupération (6 chiffres):")
        except Exception as e:
            logger.error(f"Erreur login email: {e}")
            await update.message.reply_text("❌ Erreur interne.")

    async def process_login_code(self, update: Update, message_text: str):
        """Étape 2 du login: vérifier email + code stocké lors de la création."""
        user_id = update.effective_user.id
        state = self.memory_cache.get(user_id, {})
        email = state.get('login_email')
        code = message_text.strip()
        if not email or not code.isdigit() or len(code) != 6:
            await update.message.reply_text("❌ Code invalide.")
            return
        try:
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_id = ? AND recovery_email = ? AND recovery_code_hash = ?', (user_id, email, code_hash))
            row = cursor.fetchone()
            conn.close()
            if not row:
                await update.message.reply_text("❌ Email ou code incorrect.")
                return
            # Login ok
            self.set_seller_logged_in(user_id, True)
            self.reset_user_state_preserve_login(user_id)
            await update.message.reply_text(
                "✅ Connecté. Accédez à votre espace vendeur.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Mon dashboard", callback_data='seller_dashboard')]])
            )
        except Exception as e:
            logger.error(f"Erreur login code: {e}")
            await update.message.reply_text("❌ Erreur interne.")


    # ==========================================
    # PANEL ADMIN
    # ==========================================

    async def admin_command(self, update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
        """Panel admin marketplace"""
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("❌ Accès non autorisé")
            return

        await self.admin_menu_display(update)

    async def admin_payouts_handler(self, query):
        """Gestion des payouts vendeurs - VRAIE implémentation"""
        if query.from_user.id != ADMIN_USER_ID:
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Payouts en attente
        try:
            cursor.execute('''
                SELECT p.id, p.seller_user_id, p.total_amount_sol, u.seller_name, u.seller_solana_address
                FROM seller_payouts p
                JOIN users u ON p.seller_user_id = u.user_id
                WHERE p.payout_status = 'pending'
                ORDER BY p.created_at ASC
            ''')
            pending_payouts = cursor.fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération payouts en attente (admin): {e}")
            conn.close()
            return

        if not pending_payouts:
            text = "💸 **PAYOUTS VENDEURS**\n\n✅ Aucun payout en attente !"
        else:
            text = f"💸 **PAYOUTS VENDEURS** ({len(pending_payouts)} en attente)\n\n"

            total_sol = 0
            for payout in pending_payouts:
                payout_id, seller_id, amount_sol, name, address = payout
                total_sol += amount_sol

                text += f"💰 **{name}** (ID: {seller_id})\n"
                text += f"   📍 `{address}`\n"
                text += f"   💎 {amount_sol:.4f} SOL\n\n"

            text += f"💎 **Total à payer : {total_sol:.4f} SOL**"

        keyboard = [
            [InlineKeyboardButton("✅ Marquer tous comme payés", 
                                callback_data='admin_mark_all_payouts_paid')],
            [InlineKeyboardButton("📊 Export CSV", callback_data='admin_export_payouts')],
            [InlineKeyboardButton("🔙 Admin panel", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def admin_users_handler(self, query):
        """Gestion des utilisateurs - VRAIE implémentation"""
        if query.from_user.id != ADMIN_USER_ID:
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Stats utilisateurs
        try:
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM users WHERE is_seller = TRUE')
            total_sellers = cursor.fetchone()[0]

            # Derniers utilisateurs
            cursor.execute('''
                SELECT user_id, first_name, is_seller, is_partner, registration_date
                FROM users 
                ORDER BY registration_date DESC 
                LIMIT 10
            ''')
            recent_users = cursor.fetchall()

            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération stats/utilisateurs (admin): {e}")
            conn.close()
            return

        text = f"""👥 **GESTION UTILISATEURS**

    📊 **Statistiques :**
    - Total : {total_users:,}
    - Vendeurs : {total_sellers:,}

    👥 **Derniers inscrits :**
    """

        for user in recent_users:
            status = []
            if user[2]: status.append("Vendeur")
            if user[3]: status.append("Partenaire")
            status_str = " | ".join(status) if status else "Acheteur"

            text += f"• {user[1]} (ID: {user[0]}) - {status_str}\n"

        keyboard = [
            [InlineKeyboardButton("🔍 Rechercher utilisateur", callback_data='admin_search_user')],
            [InlineKeyboardButton("📊 Export utilisateurs", callback_data='admin_export_users')],
            [InlineKeyboardButton("🔙 Admin panel", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def admin_products_handler(self, query):
        """Gestion des produits - VRAIE implémentation"""
        if query.from_user.id != ADMIN_USER_ID:
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Stats produits
        try:
            cursor.execute('SELECT COUNT(*) FROM products WHERE status = "active"')
            active_products = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM products')
            total_products = cursor.fetchone()[0]

            # Derniers produits
            cursor.execute('''
                SELECT p.product_id, p.title, p.price_eur, p.sales_count, u.seller_name, p.status
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                ORDER BY p.created_at DESC
                LIMIT 8
            ''')
            recent_products = cursor.fetchall()

            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération stats/produits (admin): {e}")
            conn.close()
            return

        text = f"""📦 **GESTION PRODUITS**

    📊 **Statistiques :**
    - Total : {total_products:,}
    - Actifs : {active_products:,}

    📦 **Derniers produits :**
    """

        for product in recent_products:
            status_icon = "✅" if product[5] == "active" else "⏸️"
            text += f"{status_icon} `{product[0]}` - {product[1][:30]}...\n"
            text += f"   💰 {product[2]}€ • 🛒 {product[3]} ventes • 👤 {product[4]}\n\n"

        keyboard = [
            [InlineKeyboardButton("🔍 Rechercher produit", callback_data='admin_search_product')],
            [InlineKeyboardButton("⛔ Suspendre produit", callback_data='admin_suspend_product')],
            [InlineKeyboardButton("📊 Export produits", callback_data='admin_export_products')],
            [InlineKeyboardButton("🔙 Admin panel", callback_data='admin_menu')]
        ]

        await query.edit_message_text(
            text[:4000],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def admin_menu_display(self, update):
        """Affiche le menu admin"""
        keyboard = [[
            InlineKeyboardButton("💰 Commissions à payer",
                                 callback_data='admin_commissions')
        ],
                    [
                        InlineKeyboardButton(
                            "📊 Stats marketplace",
                            callback_data='admin_marketplace_stats')
                    ],
                    [
                        InlineKeyboardButton("👥 Gestion utilisateurs",
                                             callback_data='admin_users')
                    ],
                    [
                        InlineKeyboardButton("📦 Gestion produits",
                                             callback_data='admin_products')
                    ],
                    [
                        InlineKeyboardButton("🎫 Tickets support",
                                             callback_data='admin_tickets')
                    ]]

        await update.message.reply_text(
            "🔧 **PANEL ADMIN MARKETPLACE**\n\nChoisissez une option :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def admin_menu(self, query):
        """Menu admin depuis callback"""
        if query.from_user.id != ADMIN_USER_ID:
            return

        keyboard = [[
            InlineKeyboardButton("💰 Commissions à payer",
                                 callback_data='admin_commissions')
        ],
                    [
                        InlineKeyboardButton(
                            "📊 Stats marketplace",
                            callback_data='admin_marketplace_stats')
                    ],
                    [
                        InlineKeyboardButton("👥 Gestion utilisateurs",
                                             callback_data='admin_users')
                    ],
                    [
                        InlineKeyboardButton("📦 Gestion produits",
                                             callback_data='admin_products')
                    ],
                    [
                        InlineKeyboardButton("🎫 Tickets support",
                                             callback_data='admin_tickets')
                    ]]

        await query.edit_message_text(
            "🔧 **PANEL ADMIN MARKETPLACE**\n\nChoisissez une option :",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def admin_commissions_handler(self, query):
        """Affiche les commissions à payer - Système supprimé"""
        if query.from_user.id != ADMIN_USER_ID:
            return

        await query.edit_message_text(
            "💰 **COMMISSIONS**\n\n✅ Système de commissions supprimé",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour admin", callback_data='admin_menu')
            ]]),
            parse_mode='Markdown')

    async def admin_marketplace_stats(self, query):
        """Statistiques admin marketplace"""
        if query.from_user.id != ADMIN_USER_ID:
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Stats générales
        try:
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM users WHERE is_seller = TRUE')
            total_sellers = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM products WHERE status = "active"')
            total_products = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COUNT(*) FROM orders WHERE payment_status = "completed"')
            total_sales = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COALESCE(SUM(product_price_eur), 0) FROM orders WHERE payment_status = "completed"'
            )
            total_volume = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COALESCE(SUM(platform_commission), 0) FROM orders WHERE payment_status = "completed"'
            )
            platform_revenue = cursor.fetchone()[0]



            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération stats (admin): {e}")
            conn.close()
            return

        stats_text = f"""📊 **STATISTIQUES ADMIN MARKETPLACE**

👥 **Utilisateurs :** {total_users:,}
🏪 **Vendeurs :** {total_sellers:,}
📦 **Produits actifs :** {total_products:,}
🛒 **Ventes totales :** {total_sales:,}

💰 **Finances :**
• Volume total : {total_volume:,.2f}€
• Revenus plateforme : {platform_revenue:.2f}€

📈 **Taux plateforme :** {PLATFORM_COMMISSION_RATE*100}%
💸 **Moyenne par vente :** {total_volume/max(total_sales,1):.2f}€"""

        keyboard = [
                    [
                        InlineKeyboardButton("📦 Gérer produits",
                                             callback_data='admin_products')
                    ],
                    [
                        InlineKeyboardButton("🔙 Panel admin",
                                             callback_data='admin_menu')
                    ]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    # ==========================================
    # GESTION DES FICHIERS (Upload/Download)
    # ==========================================

    async def handle_document_upload(self, update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
        """Gère l'upload de fichiers pour les formations"""
        user_id = update.effective_user.id

        # Vérifier si l'utilisateur est en cours d'ajout de produit
        if user_id not in self.memory_cache:
            await update.message.reply_text(
                "❌ **Session expirée**\n\nRecommencez l'ajout de produit.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Ajouter produit", callback_data='add_product')
                ]])
            )
            return

        user_state = self.memory_cache[user_id]

        if not user_state.get('adding_product') or user_state.get('step') != 'file':
            await update.message.reply_text(
                "❌ **Étape incorrecte**\n\nVous devez d'abord remplir les informations du produit.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Ajouter produit", callback_data='add_product')
                ]])
            )
            return

        document = update.message.document
        if not document:
            await update.message.reply_text(
                "❌ **Aucun fichier détecté**\n\nEnvoyez un fichier en pièce jointe."
            )
            return

        # Vérifier taille avec gestion d'erreur
        try:
            file_size_mb = document.file_size / (1024 * 1024)
            if document.file_size > config.max_file_size_mb * 1024 * 1024:
                await update.message.reply_text(
                    f"❌ **Fichier trop volumineux**\n\nTaille max : {config.max_file_size_mb}MB\nVotre fichier : {file_size_mb:.1f}MB",
                    parse_mode='Markdown'
                )
                return
        except Exception as e:
            logger.error(f"Erreur vérification taille fichier: {e}")
            await update.message.reply_text("❌ **Erreur lors de la vérification de la taille du fichier**")
            return

        # Vérifier extension avec gestion d'erreur
        try:
            if not document.file_name:
                await update.message.reply_text("❌ **Nom de fichier invalide**")
                return

            file_ext = os.path.splitext(document.file_name)[1].lower()
            if file_ext not in SUPPORTED_FILE_TYPES:
                await update.message.reply_text(
                    f"❌ **Format non supporté :** {file_ext}\n\n✅ **Formats acceptés :** {', '.join(SUPPORTED_FILE_TYPES)}",
                    parse_mode='Markdown'
                )
                return
        except Exception as e:
            logger.error(f"Erreur vérification extension fichier: {e}")
            await update.message.reply_text("❌ **Erreur lors de la vérification du format de fichier**")
            return

        try:
            await update.message.reply_text("📤 **Upload en cours...**", parse_mode='Markdown')

            # Vérifier que le dossier uploads existe
            # Centraliser le répertoire d'uploads à la racine du projet
            uploads_dir = os.path.join('uploads')
            os.makedirs(uploads_dir, exist_ok=True)

            # Télécharger le fichier
            file = await document.get_file()

            # Générer nom de fichier unique
            product_id = self.generate_product_id()
            filename = f"{product_id}_{self.sanitize_filename(document.file_name)}"
            filepath = os.path.join(uploads_dir, filename)

            # Télécharger avec gestion d'erreur spécifique
            try:
                await file.download_to_drive(filepath)
                logger.info(f"Fichier téléchargé avec succès: {filepath}")
                
                # Compression automatique pour les gros fichiers
                if file_size_mb > 10:  # Compresser si > 10MB
                    compressed_filepath = f"{filepath}.gz"
                    with open(filepath, 'rb') as f_in:
                        with gzip.open(compressed_filepath, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remplacer le fichier original par la version compressée
                    os.remove(filepath)
                    filepath = compressed_filepath
                    logger.info(f"Fichier compressé: {filepath}")
                    
            except Exception as download_error:
                logger.error(f"Erreur téléchargement fichier: {download_error}")
                await update.message.reply_text(
                    f"❌ **Erreur de téléchargement**\n\nDétail: {str(download_error)[:100]}...",
                    parse_mode='Markdown'
                )
                return

            # Vérifier que le fichier a bien été téléchargé
            if not os.path.exists(filepath):
                await update.message.reply_text("❌ **Fichier non sauvegardé**")
                return

            # Finaliser création produit
            product_data = user_state['product_data']
            product_data['main_file_path'] = filepath
            product_data['file_size_mb'] = file_size_mb

            # Sauvegarder en base avec gestion d'erreur
            try:
                success = await self.create_product_in_database(user_id, product_id, product_data)
            except Exception as db_error:
                logger.error(f"Erreur base de données: {db_error}")
                # Supprimer le fichier si échec BDD
                if os.path.exists(filepath):
                    os.remove(filepath)
                await update.message.reply_text(
                    f"❌ **Erreur base de données**\n\nDétail: {str(db_error)[:100]}...",
                    parse_mode='Markdown'
                )
                return

            if success:
                # Nettoyer cache
                del self.memory_cache[user_id]

                # Échapper Markdown via utilitaire
                safe_filename = self.escape_markdown(filename)
                safe_title = self.escape_markdown(product_data['title'])
                safe_category = self.escape_markdown(product_data['category'])

                success_text = f"""🎉 **FORMATION CRÉÉE AVEC SUCCÈS \\!**

✅ **ID Produit :** `{product_id}`
📦 **Titre :** {safe_title}
💰 **Prix :** {product_data['price_eur']}€
📂 **Catégorie :** {safe_category}
📁 **Fichier :** {safe_filename}

🚀 **Votre formation est maintenant en vente \\!**

🔗 **Lien direct :** Les clients peuvent la trouver avec l'ID `{product_id}`"""

                keyboard = [[
                    InlineKeyboardButton("📊 Voir mon produit",
                                         callback_data=f'product_{product_id}')
                ],
                            [
                                InlineKeyboardButton(
                                    "🏪 Mon dashboard",
                                    callback_data='seller_dashboard')
                            ],
                            [
                                InlineKeyboardButton(
                                    "➕ Créer un autre",
                                    callback_data='add_product')
                            ]]

                await update.message.reply_text(
                    success_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown')
            else:
                # Supprimer fichier en cas d'erreur
                if os.path.exists(filepath):
                    os.remove(filepath)

                await update.message.reply_text(
                    "❌ **Erreur lors de la création du produit**\n\nVérifiez que tous les champs sont remplis.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Réessayer",
                                             callback_data='add_product')
                    ]]),
                    parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erreur upload fichier (général): {e}")
            await update.message.reply_text(
                f"❌ **Erreur lors de l'upload**\n\nDétail: {str(e)[:100]}...\n\nVérifiez:\n• Format de fichier supporté\n• Taille < {MAX_FILE_SIZE_MB}MB\n• Connexion stable",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Réessayer",
                                         callback_data='add_product')
                ]]),
                parse_mode='Markdown')

    async def create_product_in_database(self, user_id: int, product_id: str,
                                         product_data: Dict) -> bool:
        """Crée le produit en base de données"""
        try:
            # Vérifier que toutes les données requises sont présentes
            required_fields = ['title', 'description', 'category', 'price_eur', 'price_usd', 'main_file_path', 'file_size_mb']
            for field in required_fields:
                if field not in product_data:
                    logger.error(f"Champ manquant dans product_data: {field}")
                    return False

            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                '''
                INSERT INTO products 
                (product_id, seller_user_id, title, description, category, 
                 price_eur, price_usd, main_file_path, file_size_mb, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            ''',
                (product_id, user_id, product_data['title'],
                 product_data['description'], product_data['category'],
                 product_data['price_eur'], product_data['price_usd'],
                 product_data['main_file_path'], product_data['file_size_mb']))

            # Mettre à jour compteur catégorie
            cursor.execute(
                '''
                UPDATE categories 
                SET products_count = products_count + 1 
                WHERE name = ?
            ''', (product_data['category'], ))

            conn.commit()
            conn.close()

            logger.info(f"Produit créé avec succès: {product_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur création produit en base: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False

    async def show_support_menu(self, query, lang):
        """Affiche le menu support"""
        keyboard = [
            [InlineKeyboardButton("FAQ", callback_data='faq')],
            [InlineKeyboardButton("Créer un ticket", callback_data='create_ticket')],
            [InlineKeyboardButton("Mes tickets", callback_data='my_tickets')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        support_text = """Assistance et support

Comment pouvons-nous vous aider ?"""

        await query.edit_message_text(
            support_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def show_faq(self, query, lang):
        """Affiche la FAQ"""
        faq_text = """**FAQ**

Q: Comment acheter une formation ?
R: Parcourez les catégories ou recherchez par ID.

Q: Comment vendre une formation ?
R: Devenez vendeur et ajoutez vos produits.

Q: Comment récupérer mon compte ?
R: Utilisez l'email de récupération."""

        keyboard = [[InlineKeyboardButton("Retour", callback_data='support_menu')]]

        await query.edit_message_text(
            faq_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def create_ticket(self, query, lang):
        """Crée un ticket de support"""
        self.memory_cache[query.from_user.id] = {
            'creating_ticket': True,
            'step': 'subject',
            'lang': lang
        }
        await query.edit_message_text(
            "🆘 Nouveau ticket\n\nEntrez un sujet pour votre demande:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='support_menu')]])
        )

    async def show_my_tickets(self, query, lang):
        """Affiche les tickets de support de l'utilisateur"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ticket_id, subject, status, created_at
                FROM support_tickets
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            ''', (query.from_user.id,))
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur tickets: {e}")
            await query.edit_message_text("❌ Erreur récupération tickets.")
            return

        if not rows:
            await query.edit_message_text("🎫 Aucun ticket.")
            return

        text = "🎫 Vos tickets:\n\n"
        for t in rows:
            text += f"• {t[0]} — {t[1]} — {t[2]}\n"
        await query.edit_message_text(text)

    # ==== Stubs ajoutés pour les routes câblées ====
    async def download_product(self, query, context, product_id: str, lang: str):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            # Vérifier que l'utilisateur a acheté ce produit
            cursor.execute('''
                SELECT COUNT(*) FROM orders
                WHERE buyer_user_id = ? AND product_id = ? AND payment_status = 'completed'
            ''', (query.from_user.id, product_id))
            ok = cursor.fetchone()[0] > 0
            if not ok:
                conn.close()
                await query.edit_message_text("❌ Accès refusé. Achetez d'abord ce produit.")
                return
            cursor.execute('SELECT main_file_path FROM products WHERE product_id = ?', (product_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                await query.edit_message_text("❌ Fichier introuvable.")
                return
            file_path = row[0]
            conn.close()

            if not os.path.exists(file_path):
                await query.edit_message_text("❌ Fichier manquant sur le serveur.")
                return

            # Incrémenter le compteur de téléchargements
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE orders SET download_count = download_count + 1 WHERE product_id = ? AND buyer_user_id = ?', (product_id, query.from_user.id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"Maj compteur download échouée: {e}")

            await query.message.reply_document(document=open(file_path, 'rb'))
        except Exception as e:
            logger.error(f"Erreur download: {e}")
            await query.edit_message_text("❌ Erreur lors du téléchargement.")

    async def show_my_library(self, query, lang: str):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.product_id, p.title, p.price_eur
                FROM orders o
                JOIN products p ON p.product_id = o.product_id
                WHERE o.buyer_user_id = ? AND o.payment_status = 'completed'
                ORDER BY o.completed_at DESC
            ''', (query.from_user.id,))
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur bibliothèque: {e}")
            await query.edit_message_text("❌ Erreur lors de la récupération de votre bibliothèque.")
            return

        if not rows:
            await query.edit_message_text("📚 Votre bibliothèque est vide.")
            return

        text = "📚 Vos achats:\n\n"
        keyboard = []
        for product_id, title, price in rows[:10]:
            text += f"• {title} — {price}€\n"
            keyboard.append([InlineKeyboardButton("📥 Télécharger", callback_data=f'download_product_{product_id}')])

        keyboard.append([InlineKeyboardButton("🏠 Accueil", callback_data='back_main')])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def payout_history(self, query):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, total_amount_sol, payout_status, created_at, processed_at
                FROM seller_payouts
                WHERE seller_user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            ''', (query.from_user.id,))
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur payouts: {e}")
            await query.edit_message_text("❌ Erreur récupération payouts.")
            return

        if not rows:
            await query.edit_message_text("💸 Aucun payout pour le moment.")
            return

        text = "💸 Vos payouts:\n\n"
        for r in rows:
            text += f"• #{r[0]} — {r[1]:.6f} SOL — {r[2]} — {str(r[3])[:19]}\n"
        await query.edit_message_text(text)

    async def copy_address(self, query):
        await query.answer("Adresse copiée", show_alert=False)

    async def seller_analytics(self, query, lang):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(seller_revenue), 0)
                FROM orders
                WHERE seller_user_id = ? AND payment_status = 'completed'
            ''', (query.from_user.id,))
            total = cursor.fetchone()
            cursor.execute('''
                SELECT p.title, COALESCE(COUNT(o.id),0) as sales
                FROM products p
                LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status='completed'
                WHERE p.seller_user_id = ?
                GROUP BY p.product_id
                ORDER BY sales DESC
                LIMIT 5
            ''', (query.from_user.id,))
            top = cursor.fetchall()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur analytics: {e}")
            await query.edit_message_text("❌ Erreur analytics.")
            return

        text = f"""📊 Analytics vendeur

Ventes totales: {total[0]}\nRevenus totaux: {total[1]:.2f}€\n
Top produits:\n"""
        for t in top:
            text += f"• {t[0]} — {t[1]} ventes\n"
        await query.edit_message_text(text)

    async def seller_settings(self, query, lang):
        """Paramètres vendeur"""
        user_data = self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            await query.edit_message_text(
                "❌ Connectez-vous d'abord (email + code)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Accéder à mon compte", callback_data='access_account')]])
            )
            return

        settings_text = f"""⚙️ **PARAMÈTRES VENDEUR**

👤 **Nom actuel :** {user_data['seller_name']}
📝 **Bio actuelle :** {user_data['seller_bio'][:100]}{'...' if len(user_data['seller_bio']) > 100 else ''}

Choisissez ce que vous voulez modifier :"""

        keyboard = [
            [InlineKeyboardButton("✏️ Modifier nom", callback_data='edit_seller_name')],
            [InlineKeyboardButton("📝 Modifier bio", callback_data='edit_seller_bio')],
            [InlineKeyboardButton("🚪 Se déconnecter", callback_data='seller_logout')],
            [InlineKeyboardButton("🗑️ Supprimer compte", callback_data='delete_seller')],
            [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
        ]

        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def seller_info(self, query, lang):
        await query.edit_message_text("Conditions & avantages vendeur (à implémenter)")

    async def admin_mark_all_payouts_paid(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE seller_payouts
                SET payout_status = 'completed', processed_at = CURRENT_TIMESTAMP
                WHERE payout_status = 'pending'
            ''')
            conn.commit()
            conn.close()
            await query.edit_message_text("✅ Tous les payouts en attente ont été marqués comme payés.")
        except Exception as e:
            logger.error(f"Erreur mark payouts paid: {e}")
            await query.edit_message_text("❌ Erreur lors du marquage des payouts.")

    async def admin_export_payouts(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.seller_user_id, p.total_amount_sol, p.payout_status, p.created_at, p.processed_at,
                       u.seller_name, u.seller_solana_address
                FROM seller_payouts p
                JOIN users u ON u.user_id = p.seller_user_id
                ORDER BY p.created_at DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            csv_lines = ["id,seller_user_id,total_amount_sol,payout_status,created_at,processed_at,seller_name,seller_solana_address"]
            for r in rows:
                csv_lines.append(','.join([str(x).replace(',', ' ') for x in r]))
            data = '\n'.join(csv_lines)
            await query.message.reply_document(document=bytes(data, 'utf-8'), filename='payouts.csv')
        except Exception as e:
            logger.error(f"Erreur export payouts: {e}")
            await query.edit_message_text("❌ Erreur export payouts.")

    async def admin_search_user(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        self.memory_cache[query.from_user.id] = {'admin_search_user': True}
        await query.edit_message_text("🔎 Entrez un user_id ou un partner_code à rechercher:")

    async def admin_export_users(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, first_name, is_seller, registration_date
                FROM users ORDER BY registration_date DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            csv_lines = ["user_id,username,first_name,is_seller,registration_date"]
            for r in rows:
                csv_lines.append(','.join([str(x).replace(',', ' ') for x in r]))
            data = '\n'.join(csv_lines)
            await query.message.reply_document(document=bytes(data, 'utf-8'), filename='users.csv')
        except Exception as e:
            logger.error(f"Erreur export users: {e}")
            await query.edit_message_text("❌ Erreur export utilisateurs.")

    async def admin_search_product(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        self.memory_cache[query.from_user.id] = {'admin_search_product': True}
        await query.edit_message_text("🔎 Entrez un product_id exact à rechercher:")

    async def admin_suspend_product(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        self.memory_cache[query.from_user.id] = {'admin_suspend_product': True}
        await query.edit_message_text("⛔ Entrez un product_id à suspendre:")

    async def access_account_prompt(self, query, lang):
        """Menu d'accès au compte (connexion via email + code, dashboard si connecté)."""
        user_id = query.from_user.id
        user_data = self.get_user(user_id)
        is_seller = bool(user_data and user_data.get('is_seller'))
        is_logged = self.is_seller_logged_in(user_id)

        if is_seller and is_logged:
            keyboard = [
                [InlineKeyboardButton("🏪 Mon dashboard", callback_data='seller_dashboard')],
                [InlineKeyboardButton("💰 Mon wallet", callback_data='my_wallet')],
                [InlineKeyboardButton("⚙️ Paramètres", callback_data='seller_settings')],
                [InlineKeyboardButton("🔙 Retour", callback_data='back_main')]
            ]
            await query.edit_message_text("🔑 Compte vendeur", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # Non connecté → proposer de se connecter (sans forcer la saisie)
        keyboard = [
            [InlineKeyboardButton("🔐 Se connecter", callback_data='seller_login')],
            [InlineKeyboardButton("🚀 Créer un compte vendeur", callback_data='create_seller')],
            [InlineKeyboardButton("🔙 Retour", callback_data='back_main')]
        ]
        await query.edit_message_text("🔑 **ACCÈS COMPTE VENDEUR**\n\nConnectez-vous avec votre email et votre code de récupération.", reply_markup=InlineKeyboardMarkup(keyboard))

    async def seller_logout(self, query):
        """Déconnexion: on nettoie l'état mémoire d'authentification côté bot."""
        state = self.memory_cache.get(query.from_user.id, {})
        state.pop('seller_logged_in', None)
        self.memory_cache[query.from_user.id] = state
        await query.answer("Déconnecté.")
        await self.back_to_main(query)

    async def seller_back(self, query):
        """Retour vendeur qui préserve l'état de connexion"""
        await self.seller_dashboard(query, 'fr')

    async def delete_seller_prompt(self, query):
        keyboard = [
            [InlineKeyboardButton("✅ Confirmer suppression", callback_data='delete_seller_confirm')],
            [InlineKeyboardButton("❌ Annuler", callback_data='back_main')]
        ]
        await query.edit_message_text(
            "⚠️ Confirmez la suppression du compte vendeur (produits non supprimés).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def delete_seller_confirm(self, query):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users
                    SET is_seller = FALSE, seller_name = NULL, seller_bio = NULL, seller_solana_address = NULL
                    WHERE user_id = ?
                ''', (query.from_user.id,))
                conn.commit()
                await query.edit_message_text("✅ Compte vendeur supprimé.")
        except Exception as e:
            logger.error(f"Erreur suppression vendeur: {e}")
            await query.edit_message_text("❌ Erreur suppression compte vendeur.")

async def main():
    """Fonction principale optimisée"""
    if not config.token:
        logger.error("❌ TELEGRAM_TOKEN manquant dans .env")
        return

    # Créer l'application
    bot = MarketplaceBot()
    application = Application.builder().token(config.token).build()

    # Handlers principaux
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("admin", bot.admin_command))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND,
                       bot.handle_text_message))

    # Handler pour fichiers
    application.add_handler(
        MessageHandler(filters.Document.ALL, bot.handle_document_upload))

    logger.info("🚀 Démarrage du TechBot Marketplace OPTIMISÉ...")
    logger.info(f"📱 Bot: @{config.token.split(':')[0] if config.token else 'TOKEN_MISSING'}")
    logger.info("✅ FONCTIONNALITÉS ACTIVÉES :")
    logger.info("   🏪 Marketplace multi-vendeurs")
    logger.info("   🔐 Authentification email + code")
    logger.info("   💰 Paiements crypto (8 devises)")
    logger.info("   🎁 Système parrainage")
    logger.info("   💳 Paiements NOWPayments")
    logger.info("   📁 Upload/download formations")
    logger.info("   📊 Analytics vendeurs complets")
    logger.info("   🎫 Support tickets intégré")
    logger.info("   👑 Panel admin marketplace")
    logger.info("🚀 OPTIMISATIONS PERFORMANCE :")
    logger.info("   🗄️ Pool de connexions DB")
    logger.info("   ⚡ Cache intelligent avec TTL")
    logger.info("   🌐 Client HTTP asynchrone")
    logger.info("   🛡️ Rate limiting")
    logger.info("   📊 Monitoring performances")
    logger.info("   🔄 Queue de tâches asynchrones")
    logger.info("   📦 Compression automatique")

    # Démarrer le bot
    await application.initialize()
    await application.start()
    await application.run_polling(drop_pending_updates=True)
    
    # Nettoyage à la fermeture
    await bot.task_queue.stop()
    await application.stop()
    await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
