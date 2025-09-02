#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechBot Marketplace - Formations & Crypto Wallet Intégré
Version 2.0 - Marketplace décentralisée avec wallets
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
import threading
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
import base58 # Import manquant
from app.core import settings as core_settings, configure_logging, get_sqlite_connection
from app.core.i18n import t as i18n
from app.integrations.telegram.keyboards import main_menu_keyboard, buy_menu_keyboard, sell_menu_keyboard
import qrcode
from io import BytesIO

# Charger les variables d'environnement
load_dotenv()
configure_logging(core_settings)

# Configuration
TOKEN = core_settings.TELEGRAM_TOKEN
NOWPAYMENTS_API_KEY = core_settings.NOWPAYMENTS_API_KEY
NOWPAYMENTS_IPN_SECRET = core_settings.NOWPAYMENTS_IPN_SECRET
ADMIN_USER_ID = core_settings.ADMIN_USER_ID
ADMIN_EMAIL = core_settings.ADMIN_EMAIL
SMTP_SERVER = core_settings.SMTP_SERVER
SMTP_PORT = core_settings.SMTP_PORT
SMTP_EMAIL = core_settings.SMTP_EMAIL
SMTP_PASSWORD = core_settings.SMTP_PASSWORD

# Configuration marketplace
PLATFORM_COMMISSION_RATE = core_settings.PLATFORM_COMMISSION_RATE  # 5%
PARTNER_COMMISSION_RATE = core_settings.PARTNER_COMMISSION_RATE  # 10%
MAX_FILE_SIZE_MB = core_settings.MAX_FILE_SIZE_MB
SUPPORTED_FILE_TYPES = core_settings.SUPPORTED_FILE_TYPES

# Configuration crypto
MARKETPLACE_CONFIG = core_settings.MARKETPLACE_CONFIG

# Variables commission
# (Définies une seule fois pour éviter les doublons)
PLATFORM_COMMISSION_RATE = core_settings.PLATFORM_COMMISSION_RATE  # 5% pour la plateforme
PARTNER_COMMISSION_RATE = core_settings.PARTNER_COMMISSION_RATE   # 10% pour parrainage (si gardé)

# Configuration logging
logger = logging.getLogger(__name__)


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

def get_solana_balance_display(address: str) -> float:
    """Récupère solde Solana pour affichage (optionnel)"""
    try:
        # API publique Solana
        response = requests.post(
            "https://api.mainnet-beta.solana.com",
            json={
                "jsonrpc": "2.0",
                "id": 1, 
                "method": "getBalance",
                "params": [address]
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            balance_lamports = data.get('result', {}).get('value', 0)
            return balance_lamports / 1_000_000_000  # Lamports to SOL
        return 0.0
    except:
        return 0.0  # En cas d'erreur, afficher 0

def validate_email(email: str) -> bool:
    """Valide un email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email or '') is not None


def generate_salt(length: int = 16) -> str:
    import os
    return os.urandom(length).hex()


def hash_password(password: str, salt: str) -> str:
    try:
        base = f"{salt}:{password}".encode()
        return hashlib.sha256(base).hexdigest()
    except Exception:
        return ''


def infer_network_from_address(address: str) -> str:
    """Infère le réseau à partir du format d'adresse (approximation).
    - 0x... -> Réseau EVM (ERC20/BEP20/etc.)
    - T... (34 chars) -> TRC20 (TRON)
    - Adresse base58 valide 32-44 -> Solana (SPL)
    - Sinon -> Inconnu
    """
    try:
        if not address:
            return "inconnu"
        addr = address.strip()
        if addr.startswith('0x') and len(addr) == 42:
            return "EVM (ex: ERC20)"
        if addr.startswith('T') and len(addr) in (34, 35):
            return "TRC20 (TRON)"
        if validate_solana_address(addr):
            return "Solana (SPL)"
    except Exception:
        pass
    return "inconnu"


class MarketplaceBot:

    def __init__(self):
        self.db_path = core_settings.DATABASE_PATH
        self.init_database()
        self.memory_cache = {}

    def is_seller_logged_in(self, user_id: int) -> bool:
        state = self.get_user_state(user_id)
        return bool(state.get('seller_logged_in'))

    def set_seller_logged_in(self, user_id: int, logged_in: bool) -> None:
        state = self.memory_cache.setdefault(user_id, {})
        state['seller_logged_in'] = logged_in

    def reset_user_state_preserve_login(self, user_id: int) -> None:
        """Nettoie l'état utilisateur tout en préservant le flag de connexion vendeur."""
        current = self.memory_cache.get(user_id, {})
        logged = bool(current.get('seller_logged_in'))
        lang = current.get('lang')
        # Conserver aussi la langue si présente
        self.memory_cache[user_id] = {'seller_logged_in': logged, **({'lang': lang} if lang else {})}

    def get_user_state(self, user_id: int) -> dict:
        return self.memory_cache.setdefault(user_id, {})

    def update_user_state(self, user_id: int, **kwargs) -> None:
        state = self.memory_cache.setdefault(user_id, {})
        state.update(kwargs)
        self.memory_cache[user_id] = state

    def reset_conflicting_states(self, user_id: int, keep: set = None) -> None:
        """Nettoie les états de flux concurrents pour éviter les collisions de prompts.
        Conserve uniquement les clés présentes dans keep.
        """
        keep = keep or set()
        keys_to_clear = [
            'login_wait_email', 'login_wait_code', 'waiting_for_recovery_email',
            'waiting_for_recovery_code', 'waiting_new_password', 'creating_ticket',
            'waiting_for_product_id', 'adding_product', 'editing_product',
            'editing_settings', 'admin_search_user', 'admin_search_product',
            'admin_suspend_product'
        ]
        state = self.memory_cache.setdefault(user_id, {})
        for k in keys_to_clear:
            if k not in keep:
                state.pop(k, None)
        self.memory_cache[user_id] = state

    def get_db_connection(self) -> sqlite3.Connection:
        return get_sqlite_connection(self.db_path)

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

    def init_database(self):
        """Base de données simplifiée"""
        conn = self.get_db_connection()
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

                    -- Système d'authentification vendeur
                    recovery_email TEXT,
                    recovery_code_hash TEXT,
                    password_salt TEXT,
                    password_hash TEXT,

                    -- Parrainage (gardé de l'original)
                    is_partner BOOLEAN DEFAULT FALSE,
                    partner_code TEXT UNIQUE,
                    referred_by TEXT,
                    total_commission REAL DEFAULT 0.0,

                    email TEXT
                )
            ''')
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur création table users: {e}")
            conn.rollback()

        # Migration légère: ajouter colonnes manquantes si la table existe déjà
        try:
            cursor.execute("PRAGMA table_info(users)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            altered = False
            if 'password_salt' not in existing_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN password_salt TEXT")
                altered = True
            if 'password_hash' not in existing_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
                altered = True
            if 'recovery_code_hash' not in existing_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN recovery_code_hash TEXT")
                altered = True
            if 'email' not in existing_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
                altered = True
            if altered:
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur migration colonnes users: {e}")
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
                    partner_commission REAL DEFAULT 0.0,
                    crypto_currency TEXT,
                    crypto_amount REAL,
                    payment_status TEXT DEFAULT 'pending',
                    nowpayments_id TEXT,
                    payment_address TEXT,
                    partner_code TEXT,
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
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur création table support_tickets: {e}")
            conn.rollback()

        # Migration légère: colonnes supplémentaires pour le routage des tickets
        try:
            cursor.execute("PRAGMA table_info(support_tickets)")
            cols = {row[1] for row in cursor.fetchall()}
            altered = False
            if 'order_id' not in cols:
                cursor.execute("ALTER TABLE support_tickets ADD COLUMN order_id TEXT")
                altered = True
            if 'seller_user_id' not in cols:
                cursor.execute("ALTER TABLE support_tickets ADD COLUMN seller_user_id INTEGER")
                altered = True
            if 'assigned_to_user_id' not in cols:
                cursor.execute("ALTER TABLE support_tickets ADD COLUMN assigned_to_user_id INTEGER")
                altered = True
            if 'updated_at' not in cols:
                cursor.execute("ALTER TABLE support_tickets ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                altered = True
            if altered:
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur migration support_tickets: {e}")
            conn.rollback()

        # Nouvelle table: messages de support (thread par ticket)
        try:
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
        except sqlite3.Error as e:
            logger.error(f"Erreur création table support_messages: {e}")
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
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur création table categories: {e}")
            conn.rollback()

        # (Supprimé) Table codes de parrainage par défaut

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

        # (Supprimé) Insertion des codes de parrainage par défaut

        conn.close()

    def generate_product_id(self) -> str:
        """Génère un ID produit vraiment unique"""
        import secrets

        # Format aligné avec la recherche: TBF-YYMM-XXXXXX
        yymm = datetime.utcnow().strftime('%y%m')

        def random_code(length: int = 6) -> str:
            alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # éviter confusions O/0/I/1
            return ''.join(random.choice(alphabet) for _ in range(length))

        # Double vérification d'unicité
        conn = self.get_db_connection()
        cursor = conn.cursor()

        max_attempts = 100
        for attempt in range(max_attempts):
            product_id = f"TBF-{yymm}-{random_code()}"

            try:
                cursor.execute('SELECT COUNT(*) FROM products WHERE product_id = ?', (product_id,))
                if cursor.fetchone()[0] == 0:
                    conn.close()
                    return product_id
            except sqlite3.Error as e:
                logger.error(f"Erreur vérification ID produit: {e}")
                conn.close()
                raise e

            # Si collision, générer nouveau random
            yymm = datetime.utcnow().strftime('%y%m')

        conn.close()
        raise Exception("Impossible de générer un ID unique après 100 tentatives")

    def add_user(self,
                 user_id: int,
                 username: str,
                 first_name: str,
                 language_code: str = 'fr') -> bool:
        """Ajoute un utilisateur (via UserRepository)"""
        from app.domain.repositories import UserRepository
        return UserRepository(self.db_path).add_user(user_id, username, first_name, language_code)

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Récupère un utilisateur (via UserRepository)"""
        from app.domain.repositories import UserRepository
        return UserRepository(self.db_path).get_user(user_id)

    def create_seller_account_with_recovery(self, user_id: int, seller_name: str, 
                                      seller_bio: str, recovery_email: str, 
                                      solana_address: str) -> dict:
        """Crée un compte vendeur avec email + mot de passe (remplace le code 6 chiffres)"""
        try:
            # Valider adresse Solana
            if not validate_solana_address(solana_address):
                return {'success': False, 'error': 'Adresse Solana invalide'}

            # Générer un salt et le hash du mot de passe fourni en mémoire
            state = self.get_user_state(user_id)
            raw_password = state.get('password')
            if not raw_password:
                return {'success': False, 'error': 'Mot de passe manquant'}
            salt = generate_salt()
            pwd_hash = hash_password(raw_password, salt)

            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Vérifier que l'adresse n'est pas déjà utilisée
            try:
                cursor.execute(
                    'SELECT COUNT(*) FROM users WHERE seller_solana_address = ?',
                    (solana_address,)
                )
                if cursor.fetchone()[0] > 0:
                    conn.close()
                    return {'success': False, 'error': 'Adresse déjà utilisée'}
            except sqlite3.Error as e:
                logger.error(f"Erreur vérification adresse: {e}")
                conn.close()
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
                        recovery_code_hash = NULL,
                        password_salt = ?,
                        password_hash = ?
                    WHERE user_id = ?
                ''', (seller_name, seller_bio, solana_address, recovery_email, salt, pwd_hash, user_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    conn.close()

                    # Ne plus retourner de code, seulement succès
                    # Nettoyer le mot de passe en mémoire
                    state.pop('password', None)
                    return {'success': True}
                else:
                    conn.close()
                    return {'success': False, 'error': 'Échec mise à jour'}
            except sqlite3.Error as e:
                logger.error(f"Erreur création vendeur: {e}")
                conn.close()
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
                SELECT p.*, u.seller_name, u.seller_rating, u.seller_bio
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

    # (Supprimé) Fonctions de parrainage

        conn.close()
        return None

    def create_payment(self, amount_usd: float, currency: str,
                       order_id: str) -> Optional[Dict]:
        """Crée un paiement NOWPayments (via PaymentService)"""
        try:
            from app.services.payment_service import PaymentService
            return PaymentService().create_payment(amount_usd, currency, order_id)
        except Exception as e:
            logger.error(f"Erreur PaymentService.create_payment: {e}")
            return None

    def check_payment_status(self, payment_id: str) -> Optional[Dict]:
        """Vérifie le statut d'un paiement (via PaymentService)"""
        try:
            from app.services.payment_service import PaymentService
            return PaymentService().check_payment_status(payment_id)
        except Exception as e:
            logger.error(f"Erreur PaymentService.check_payment_status: {e}")
            return None

    def get_exchange_rate(self) -> float:
        """Récupère le taux EUR/USD (via PaymentService)"""
        try:
            from app.services.payment_service import PaymentService
            return PaymentService().get_exchange_rate()
        except Exception:
            return 1.10

    def get_available_currencies(self) -> List[str]:
        """Récupère les cryptos disponibles (via PaymentService)"""
        try:
            from app.services.payment_service import PaymentService
            return PaymentService().get_available_currencies()
        except Exception:
            return ['btc', 'eth', 'usdt', 'usdc']

    def create_seller_payout(self, seller_user_id: int, order_ids: list, 
                        total_amount_sol: float) -> Optional[int]:
        """Crée un payout vendeur en attente"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO seller_payouts 
                (seller_user_id, order_ids, total_amount_sol, payout_status)
                VALUES (?, ?, ?, 'pending')
            ''', (seller_user_id, json.dumps(order_ids), total_amount_sol))

            payout_id = cursor.lastrowid
            conn.commit()
            conn.close()

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

    async def start_command(self, update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
        """Nouveau menu d'accueil marketplace"""
        user = update.effective_user
        # Conserver l'état (ne pas déconnecter). Simplement assurer l'inscription DB.
        self.add_user(user.id, user.username, user.first_name, user.language_code or 'fr')

        # Déterminer la langue depuis la base si disponible (persistance)
        user_data = self.get_user(user.id)
        lang = user_data['language_code'] if user_data and user_data.get('language_code') else (user.language_code or 'fr')

        welcome_text = self.get_text('welcome', lang)
        # Construire dynamiquement le menu principal pour éviter les doublons
        is_seller = user_data and user_data.get('is_seller')
        keyboard = [
            [InlineKeyboardButton(self.get_text('buy_menu', lang), callback_data='buy_menu')]
        ]
        if is_seller:
            keyboard.append([InlineKeyboardButton(self.get_text('seller_dashboard', lang), callback_data='seller_dashboard')])
        else:
            keyboard.append([InlineKeyboardButton(self.get_text('sell_menu', lang), callback_data='sell_menu')])
        keyboard.append([
            InlineKeyboardButton(self.get_text('support', lang), callback_data='support_menu')
        ])
        keyboard.append([
            InlineKeyboardButton("🇫🇷 FR", callback_data='lang_fr'), InlineKeyboardButton("🇺🇸 EN", callback_data='lang_en')
        ])

        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire principal des boutons - COMPLET"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        user_data = self.get_user(user_id)
        lang = user_data['language_code'] if user_data else 'fr'

        try:
            # Navigation principale
            if query.data == 'buy_menu':
                await self.buy_menu(query, lang)
            elif query.data == 'sell_menu':
                await self.sell_menu(query, lang)
            elif query.data == 'seller_dashboard':
                await self.seller_dashboard(query, lang)
            # marketplace_stats déplacé dans l'admin uniquement
            elif query.data == 'support_menu':
                await self.show_support_menu(query, lang)
            elif query.data == 'account_recovery':
                await self.account_recovery_menu(query, lang)
            elif query.data == 'retry_password':
                # Rester sur l'étape mot de passe et redemander
                self.reset_conflicting_states(user_id, keep={'login_wait_code'})
                self.update_user_state(user_id, login_wait_code=True)
                await query.edit_message_text(
                    "✏️ Entrez votre mot de passe vendeur:")
            elif query.data == 'back_main':
                await self.back_to_main(query)
            elif query.data.startswith('lang_'):
                await self.change_language(query, query.data[5:])

            # Accès compte (unifié)
            # 'Accéder à mon compte' retiré pour simplifier l'UX (doublon du dashboard)
            elif query.data == 'seller_login':
                # Démarrer explicitement le flux de connexion (email puis code)
                # Respecter la langue persistée
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                self.reset_conflicting_states(user_id, keep={'login_wait_email'})
                self.update_user_state(user_id, login_wait_email=True, login_wait_code=False, lang=lang)
                from app.core.i18n import t as i18n
                await query.edit_message_text(i18n(lang, 'prompt_enter_recovery_email'))
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
            elif query.data.startswith('preview_product_'):
                product_id = query.data.split('preview_product_')[-1]
                await self.preview_product(query, product_id, lang)

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
                self.reset_conflicting_states(user_id, keep={'waiting_for_recovery_email'})
                await self.recovery_by_email_prompt(query, lang)

            # Programme de parrainage retiré

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
            elif query.data.startswith('contact_seller_'):
                from app.integrations.telegram.handlers import support_handlers as sh
                product_id = query.data.split('contact_seller_')[-1]
                await sh.contact_seller_start(self, query, product_id, lang)
            elif query.data.startswith('view_ticket_'):
                from app.integrations.telegram.handlers import support_handlers as sh
                ticket_id = query.data.split('view_ticket_')[-1]
                await sh.view_ticket(self, query, ticket_id)
            elif query.data.startswith('reply_ticket_'):
                from app.integrations.telegram.handlers import support_handlers as sh
                ticket_id = query.data.split('reply_ticket_')[-1]
                await sh.reply_ticket_prepare(self, query, ticket_id)
            elif query.data.startswith('escalate_ticket_'):
                from app.integrations.telegram.handlers import support_handlers as sh
                ticket_id = query.data.split('escalate_ticket_')[-1]
                await sh.escalate_ticket(self, query, ticket_id)
            elif query.data == 'admin_tickets':
                from app.integrations.telegram.handlers import support_handlers as sh
                await sh.admin_tickets(self, query)
            elif query.data.startswith('admin_reply_ticket_'):
                from app.integrations.telegram.handlers import support_handlers as sh
                ticket_id = query.data.split('admin_reply_ticket_')[-1]
                await sh.admin_reply_prepare(self, query, ticket_id)
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
                self.update_user_state(user_id, editing_settings=True, step='edit_name')
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                from app.core.i18n import t as i18n
                await query.edit_message_text(i18n(lang, 'prompt_new_seller_name'))
            elif query.data == 'edit_seller_bio':
                self.update_user_state(user_id, editing_settings=True, step='edit_bio')
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                from app.core.i18n import t as i18n
                await query.edit_message_text(i18n(lang, 'prompt_new_seller_bio'))
            elif query.data.startswith('edit_product_'):
                product_id = query.data.split('edit_product_')[-1]
                self.update_user_state(user_id, editing_product=True, product_id=product_id, step='choose_field')
                keyboard = [
                    [InlineKeyboardButton("✏️ Modifier titre", callback_data=f'edit_field_title_{product_id}')],
                    [InlineKeyboardButton("💰 Modifier prix", callback_data=f'edit_field_price_{product_id}')],
                    [InlineKeyboardButton("⏸️ Activer/Désactiver", callback_data=f'edit_field_toggle_{product_id}')],
                    [InlineKeyboardButton("🔙 Retour", callback_data='my_products')],
                    [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
                ]
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                await query.edit_message_text(self.tr(lang, f"Édition produit `{product_id}`:", f"Editing product `{product_id}`:"), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            elif query.data.startswith('edit_field_title_'):
                product_id = query.data.split('edit_field_title_')[-1]
                self.update_user_state(user_id, editing_product=True, product_id=product_id, step='edit_title_input')
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                from app.core.i18n import t as i18n
                await query.edit_message_text(i18n(lang, 'prompt_new_title'))
            elif query.data.startswith('edit_field_price_'):
                product_id = query.data.split('edit_field_price_')[-1]
                self.update_user_state(user_id, editing_product=True, product_id=product_id, step='edit_price_input')
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                from app.core.i18n import t as i18n
                await query.edit_message_text(i18n(lang, 'prompt_new_price'))
            elif query.data.startswith('edit_field_toggle_'):
                product_id = query.data.split('edit_field_toggle_')[-1]
                try:
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT status FROM products WHERE product_id = ? AND seller_user_id = ?', (product_id, user_id))
                    row = cursor.fetchone()
                    if not row:
                        conn.close()
                        lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                        await query.edit_message_text(self.tr(lang, "❌ Produit introuvable.", "❌ Product not found."), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self.tr(lang, "🔙 Retour", "🔙 Back"), callback_data='my_products')]]))
                    else:
                        new_status = 'inactive' if row[0] == 'active' else 'active'
                        cursor.execute('UPDATE products SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (new_status, product_id, user_id))
                        conn.commit()
                        conn.close()
                        await self.show_my_products(query, 'fr')
                except Exception as e:
                    logger.error(f"Erreur toggle statut produit: {e}")
                    lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                    await query.edit_message_text(self.tr(lang, "❌ Erreur mise à jour statut.", "❌ Error updating status."), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self.tr(lang, "🔙 Retour", "🔙 Back"), callback_data='my_products')]]))
            elif query.data.startswith('delete_product_'):
                product_id = query.data.split('delete_product_')[-1]
                self.update_user_state(user_id, confirm_delete_product=product_id)
                keyboard = [
                    [InlineKeyboardButton("✅ Confirmer suppression", callback_data=f'confirm_delete_{product_id}')],
                    [InlineKeyboardButton("❌ Annuler", callback_data='my_products')],
                    [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
                ]
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                await query.edit_message_text(self.tr(lang, f"Confirmer la suppression du produit `{product_id}` ?", f"Confirm deletion of product `{product_id}`?"), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            elif query.data.startswith('confirm_delete_'):
                product_id = query.data.split('confirm_delete_')[-1]
                try:
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM products WHERE product_id = ? AND seller_user_id = ?', (product_id, user_id))
                    conn.commit()
                    conn.close()
                    await self.show_my_products(query, lang)
                except Exception as e:
                    logger.error(f"Erreur suppression produit: {e}")
                    lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                    await query.edit_message_text(self.tr(lang, "❌ Erreur lors de la suppression.", "❌ Error during deletion."), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self.tr(lang, "🔙 Retour", "🔙 Back"), callback_data='my_products')]]))
            elif query.data == 'seller_info':
                await self.seller_info(query, lang)

            else:
                lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
                await query.edit_message_text(
                    self.tr(lang, "🚧 Fonction en cours de développement...", "🚧 Feature under development..."),
                    reply_markup=InlineKeyboardMarkup([[ 
                        InlineKeyboardButton(self.tr(lang, "🏠 Accueil", "🏠 Home"), callback_data='back_main')
                    ]]))

        except Exception as e:
            logger.error(f"Erreur button_handler: {e}")
            lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
            await query.edit_message_text(
                self.tr(lang, "❌ Erreur temporaire. Retour au menu principal.", "❌ Temporary error. Back to main menu."),
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton(self.tr(lang, "🏠 Accueil", "🏠 Home"), callback_data='back_main')
                ]]))

    async def buy_menu(self, query, lang):
        """Menu d'achat"""
        keyboard = buy_menu_keyboard(lang)

        from app.core.i18n import t as i18n
        buy_text = i18n(lang, 'buy_menu_text')

        await query.edit_message_text(
            buy_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def search_product_prompt(self, query, lang):
        """Demande de saisir un ID produit"""
        # Clear other states to avoid collisions
        self.reset_conflicting_states(query.from_user.id, keep={'waiting_for_product_id'})
        self.update_user_state(query.from_user.id, waiting_for_product_id=True, lang=lang)

        prompt_text = i18n(lang, 'search_prompt')

        try:
            await query.edit_message_text(
                prompt_text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour",
                                           callback_data='buy_menu')]]),
                parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(
                prompt_text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour",
                                           callback_data='buy_menu')]]),
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
            [InlineKeyboardButton("🏠 Home" if lang == 'en' else "🏠 Accueil", callback_data='back_main')])

        categories_text = i18n(lang, 'categories_title')

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
                SELECT p.product_id,
                       p.title,
                       p.price_eur,
                       COALESCE(COUNT(o.order_id), 0) AS sales,
                       0 AS rating,
                       u.seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
                WHERE p.status = 'active'
                GROUP BY p.product_id
                ORDER BY sales DESC
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
                SELECT p.product_id,
                       p.title,
                       p.price_eur,
                       COALESCE(COUNT(o.order_id), 0) AS sales,
                       0 AS rating,
                       u.seller_name
                FROM products p
                JOIN users u ON p.seller_user_id = u.user_id
                LEFT JOIN orders o ON o.product_id = p.product_id AND o.payment_status = 'completed'
                WHERE p.status = 'active' AND p.category = ?
                GROUP BY p.product_id
                ORDER BY sales DESC
            '''
            query_params = (category_name,)

        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Exécuter la requête appropriée
        try:
            cursor.execute(f"{base_query} LIMIT 10", query_params)
            products = cursor.fetchall()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération produits catégorie: {e}")
            conn.close()
            return

        # Reste du code identique pour l'affichage...

        if not products:
            safe_name = self.escape_markdown(category_name.upper())
            products_text = f"📂 **{safe_name}**\n\n" + i18n(lang, 'no_products_category')

            keyboard = [[
                InlineKeyboardButton("🚀 Créer une formation",
                                     callback_data='sell_menu')
            ],
                        [
                            InlineKeyboardButton(
                                "📂 Autres catégories",
                                callback_data='browse_categories')
                        ]]
        else:
            safe_name = self.escape_markdown(category_name.upper())
            products_text = f"📂 **{safe_name}** ({len(products)} formations)\n\n"

            keyboard = []
            for product in products:
                product_id, title, price, sales, rating, seller = product
                safe_title = self.escape_markdown(title)
                safe_seller = self.escape_markdown(seller)
                products_text += f"📦 **{safe_title}**\n"
                products_text += f"💰 {price}€ • 👤 {safe_seller} • 🛒 {sales} ventes\n\n"

                keyboard.append([
                    InlineKeyboardButton(f"📖 {title[:40]}...",
                                         callback_data=f'product_{product_id}')
                ])

            keyboard.extend([[
                InlineKeyboardButton("📂 Autres catégories",
                                     callback_data='browse_categories')
            ], [
                InlineKeyboardButton("🔙 Menu achat", callback_data='buy_menu')
            ]])

        try:
            await query.edit_message_text(
                products_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"Markdown render failed in category list, falling back: {e}")
            await query.edit_message_text(
                products_text.replace('*', ''),
                reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_product_details(self, query, product_id, lang):
        """Affiche les détails d'un produit"""
        product = self.get_product_by_id(product_id)

        if not product:
            from app.core.i18n import t as i18n
            await query.edit_message_text(
                (f"❌ **Product not found:** `{product_id}`\n\nCheck the ID or browse categories." if lang=='en' else f"❌ **Produit introuvable :** `{product_id}`\n\nVérifiez l'ID ou cherchez dans les catégories."),
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton(i18n(lang, 'btn_search'),
                                         callback_data='search_product'),
                    InlineKeyboardButton(i18n(lang, 'btn_categories'),
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

        from app.core.i18n import t as i18n
        safe_title = self.escape_markdown(str(product.get('title') or ''))
        safe_seller = self.escape_markdown(str(product.get('seller_name') or ''))
        safe_category = self.escape_markdown(str(product.get('category') or ''))
        desc_raw = product.get('description') or ("No description" if lang=='en' else "Aucune description disponible")
        safe_desc = self.escape_markdown(str(desc_raw))
        bio_raw = product.get('seller_bio') or ("Not provided" if lang=='en' else "Non renseignée")
        safe_bio = self.escape_markdown(str(bio_raw))
        product_text = (
            f"📦 **{safe_title}**\n\n"
            f"{i18n(lang, 'label_seller')} {safe_seller}\n"
            f"{i18n(lang, 'label_category')} {safe_category}\n"
            f"{i18n(lang, 'label_price')} {product['price_eur']}€\n\n"
            f"{i18n(lang, 'label_description')}\n{safe_desc}\n\n"
            f"{i18n(lang, 'label_seller_bio')}\n{safe_bio}\n\n"
            f"{i18n(lang, 'stats_title')}\n"
            f"• {i18n(lang, 'label_views')} {product['views_count']} {'views' if lang=='en' else 'vues'}\n"
            f"• {i18n(lang, 'label_sales')} {product['sales_count']} {'sales' if lang=='en' else 'ventes'}\n\n"
            f"📁 **Fichier :** {product['file_size_mb']:.1f} MB"
        )

        keyboard = [[
            InlineKeyboardButton(i18n(lang, 'btn_buy'),
                                 callback_data=f'buy_product_{product_id}')
        ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_preview'),
                                             callback_data=f'preview_product_{product_id}')
                    ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_other_products'),
                                             callback_data='browse_categories')
                    ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_back'),
                                             callback_data='buy_menu')
                    ]]

        try:
            await query.edit_message_text(
                product_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"Markdown render failed in product details, falling back: {e}")
            await query.edit_message_text(
                product_text.replace('*', ''),
                reply_markup=InlineKeyboardMarkup(keyboard))

    async def preview_product(self, query, product_id: str, lang: str):
        product = self.get_product_by_id(product_id)
        if not product:
            from app.core.i18n import t as i18n
            await query.edit_message_text(i18n(lang, 'err_product_not_found'))
            return
        # Extrait de description (200-300 chars)
        desc = (product['description'] or '')
        snippet_raw = (desc[:300] + '…') if len(desc) > 300 else desc or ("No preview available" if lang=='en' else "Aucun aperçu disponible")
        safe_title = self.escape_markdown(str(product.get('title') or ''))
        snippet = self.escape_markdown(snippet_raw)
        text = (
            f"👀 **PREVIEW**\n\n📦 {safe_title}\n\n{snippet}" if lang=='en'
            else f"👀 **APERÇU**\n\n📦 {safe_title}\n\n{snippet}"
        )
        from app.core.i18n import t as i18n
        keyboard = [
            [InlineKeyboardButton(i18n(lang, 'btn_buy'), callback_data=f'buy_product_{product_id}')],
            [InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data=f'product_{product_id}')]
        ]
        # Afficher d'abord le texte
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.warning(f"Fallback to reply_text for preview: {e}")
            await query.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        # Si un PDF est disponible, tenter un aperçu visuel de la première page
        try:
            import os
            main_path = product.get('main_file_path') or ''
            if isinstance(main_path, str) and main_path.lower().endswith('.pdf') and os.path.exists(main_path):
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(main_path)
                    if doc.page_count > 0:
                        page = doc.load_page(0)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        bio = BytesIO(pix.tobytes('png'))
                        bio.seek(0)
                        caption = ("Preview — page 1" if lang=='en' else "Aperçu — page 1")
                        await query.message.reply_photo(photo=bio, caption=caption)
                        doc.close()
                except Exception as e:
                    # Si PyMuPDF n'est pas dispo ou erreur lecture, ignorer proprement
                    pass
        except Exception:
            pass

    async def buy_product_prompt(self, query, product_id, lang):
        """Démarrer l'achat sans parrainage (parrainage retiré)"""
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
                from app.core.i18n import t as i18n
                await query.edit_message_text(
                    i18n(lang, 'already_owned'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_library'),
                                             callback_data='my_library'),
                        InlineKeyboardButton(i18n(lang, 'btn_back'),
                                             callback_data=f'product_{product_id}')
                    ]]))
                return
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur vérification achat produit: {e}")
            conn.close()
            return

        # Stocker le produit à acheter et passer directement au choix crypto
        self.update_user_state(user_id, buying_product_id=product_id, lang=lang)

        await self.show_crypto_options(query, lang)

    async def enter_referral_manual(self, query, lang):
        """Demander la saisie manuelle du code"""
        self.update_user_state(query.from_user.id, waiting_for_referral=True, lang=lang)

        await query.edit_message_text(
            "✍️ **Veuillez saisir votre code de parrainage :**\n\nTapez le code exactement comme vous l'avez reçu.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Retour",
                                       callback_data='buy_menu')]]))

    

    async def choose_random_referral(self, query, lang):
        """Choisir un code de parrainage aléatoire"""
        from app.services.referral_service import ReferralService
        available_codes = ReferralService(self.db_path).list_all_codes()

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
        ], [InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')]])

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
        self.update_user_state(query.from_user.id, validated_referral=referral_code, lang=lang)

        await query.edit_message_text(
            f"✅ **Code validé :** `{referral_code}`\n\nProcédons au paiement !",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💳 Continuer vers le paiement",
                                     callback_data='proceed_to_payment'),
                InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
            ]]),
            parse_mode='Markdown')

    async def become_partner(self, query, lang):
        """Inscription partenaire"""
        user_id = query.from_user.id
        user_data = self.get_user(user_id)

        if user_data and user_data['is_partner']:
            await query.edit_message_text(
                ("✅ You are already a partner!" if lang == 'en' else "✅ Vous êtes déjà partenaire !"),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 My dashboard" if lang == 'en' else "📊 Mon dashboard",
                                         callback_data='seller_dashboard')
                ]]))
            return

        partner_code = self.create_partner_code(user_id)

        if partner_code:
            # Valider automatiquement son propre code
            self.update_user_state(user_id, validated_referral=partner_code, lang=lang, self_referral=True)

            welcome_text = (
                f"""🎊 **WELCOME TO THE TEAM!**

✅ Your partner account is activated!

🎯 **YOUR UNIQUE CODE:** `{partner_code}`

💰 **Partner benefits:**
• Earn 10% on each sale
• Use YOUR code for your own purchases
• Full seller dashboard
• Priority support""" if lang == 'en' else f"""🎊 **BIENVENUE DANS L'ÉQUIPE !**

✅ Votre compte partenaire est activé !

🎯 **VOTRE CODE UNIQUE :** `{partner_code}`

💰 **Avantages partenaire :**
• Gagnez 10% sur chaque vente
• Utilisez VOTRE code pour vos achats
• Dashboard vendeur complet
• Support prioritaire""")

            keyboard = [[
                InlineKeyboardButton("💳 Continue purchase" if lang == 'en' else "💳 Continuer l'achat",
                                     callback_data='proceed_to_payment')
            ],
                        [
                            InlineKeyboardButton(
                                "📊 My dashboard" if lang == 'en' else "📊 Mon dashboard",
                                callback_data='seller_dashboard')
                        ]]

            await query.edit_message_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        else:
            await query.edit_message_text(
                ("❌ Error while creating the partner account." if lang == 'en' else "❌ Erreur lors de la création du compte partenaire."),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour", callback_data='buy_menu')
                ]]))

    async def show_crypto_options(self, query, lang):
        """Affiche les options de crypto pour le paiement (sans parrainage)"""
        user_id = query.from_user.id
        user_cache = self.get_user_state(user_id)

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
            'usdc': ('🟢 USD Coin', '⚡ 5-10 min'),
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

        if lang == 'en':
            crypto_text = f"""💳 **CHOOSE YOUR CRYPTO**

📦 **Product:** {product['title']}
💰 **Price:** {product['price_eur']}€
🔐 **Select your preferred crypto:**

✅ **Benefits:**
• 100% secure and private payment
• Automatic confirmation
• Instant delivery after payment
• Priority support 24/7"""
        else:
            crypto_text = f"""💳 **CHOISIR VOTRE CRYPTO**

📦 **Produit :** {product['title']}
💰 **Prix :** {product['price_eur']}€
🔐 **Sélectionnez votre crypto préférée :**

✅ **Avantages :**
• Paiement 100% sécurisé et anonyme
• Confirmation automatique
• Livraison instantanée après paiement
• Support prioritaire 24/7"""

        await query.edit_message_text(
            crypto_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def process_payment(self, query, crypto_currency, lang):
        """Traite le paiement (parrainage retiré)"""
        user_id = query.from_user.id
        user_cache = self.get_user_state(user_id)

        # Vérifier les données nécessaires
        if 'buying_product_id' not in user_cache:
            await query.edit_message_text("❌ Données de commande manquantes !",
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton(
                                                  "🔙 Recommencer",
                                                  callback_data='buy_menu')
                                          ]]))
            return

        product_id = user_cache['buying_product_id']

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
        partner_commission = 0.0  # Parrainage désactivé
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
                     product_price_eur, platform_commission, seller_revenue, partner_commission,
                     crypto_currency, crypto_amount, nowpayments_id, payment_address, partner_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_id, user_id, product_id, product['seller_user_id'],
                      product_price_eur, platform_commission, seller_revenue,
                      partner_commission, crypto_currency,
                      payment_data.get('pay_amount',
                                       0), payment_data.get('payment_id'),
                      payment_data.get('pay_address', ''), None))
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                logger.error(f"Erreur création commande: {e}")
                conn.close()
                return

            # Nettoyer le cache de l'achat uniquement (conserver l'état global/login)
            # Nettoyer uniquement les clés liées à l'achat, conserver le reste (dont lang/login)
            if user_id in self.memory_cache:
                user_cache = self.get_user_state(user_id)
                for k in ['buying_product_id', 'validated_referral', 'self_referral']:
                    user_cache.pop(k, None)
                self.memory_cache[user_id] = user_cache

            crypto_amount = payment_data.get('pay_amount', 0)
            payment_address = payment_data.get('pay_address', '')
            network_hint = infer_network_from_address(payment_address)

            if lang == 'en':
                payment_text = f"""💳 **PAYMENT IN PROGRESS**

📋 **Order:** `{order_id}`
📦 **Product:** {product['title']}
💰 **Exact amount:** `{crypto_amount}` {crypto_currency.upper()}

📍 **Payment address:**
`{payment_address}`
🧭 **Detected network:** {network_hint}

⏰ **Validity:** 30 minutes
🔄 **Confirmations:** 1-3 depending on network

⚠️ **IMPORTANT:**
• Send **exactly** the indicated amount
• Use only {crypto_currency.upper()}
• Detection is automatic"""
            else:
                payment_text = f"""💳 **PAIEMENT EN COURS**

📋 **Commande :** `{order_id}`
📦 **Produit :** {product['title']}
💰 **Montant exact :** `{crypto_amount}` {crypto_currency.upper()}

📍 **Adresse de paiement :**
`{payment_address}`
🧭 **Réseau détecté :** {network_hint}

⏰ **Validité :** 30 minutes
🔄 **Confirmations :** 1-3 selon réseau

⚠️ **IMPORTANT :**
• Envoyez **exactement** le montant indiqué
• Utilisez uniquement du {crypto_currency.upper()}
• La détection est automatique"""

            keyboard = [[
                InlineKeyboardButton("🔄 Check payment" if lang == 'en' else "🔄 Vérifier paiement",
                                     callback_data=f'check_payment_{order_id}')
            ], [
                InlineKeyboardButton("💬 Support", callback_data='support_menu')
            ], [
                InlineKeyboardButton("🏠 Home" if lang == 'en' else "🏠 Accueil", callback_data='back_main')
            ]]

            # Envoyer le texte avec le clavier, puis le QR séparément (évite les échecs d'edit sur media)
            try:
                await query.edit_message_text(
                    payment_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown')
            except Exception as e:
                logger.warning(f"edit_message_text failed, sending new message: {e}")
                await query.message.reply_text(
                    payment_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown')

            try:
                qr_img = qrcode.make(payment_address)
                bio = BytesIO()
                qr_img.save(bio, format='PNG')
                bio.seek(0)
                await query.message.reply_photo(photo=bio, caption="QR de paiement")
            except Exception as e:
                logger.warning(f"QR code generation failed: {e}")
        else:
            logger.error(f"create_payment returned None order_id={order_id} crypto={crypto_currency} amount_usd={product_price_usd}")
            from app.core.i18n import t as i18n
            await query.edit_message_text(
                i18n(lang, 'err_nowpayments'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_retry'),
                                         callback_data='proceed_to_payment')
                ], [
                    InlineKeyboardButton("💱 Change crypto" if lang=='en' else "💱 Changer de crypto",
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

        # Index corrects: nowpayments_id = 12, partner_code = 14
        payment_id = order[12]
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
                    ''', (order[7], order[4]))

                    partner_code = order[14]
                    if partner_code:
                        cursor.execute(
                            '''
                            UPDATE users 
                            SET total_commission = total_commission + ?
                            WHERE partner_code = ?
                        ''', (order[8], partner_code))

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
{"✅ Payout vendeur créé automatiquement" if payout_created else "⚠️ Payout vendeur en attente"}

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
                try:
                    await query.edit_message_text(
                        (f"⏳ **PAYMENT IN PROGRESS**\n\n🔍 **Status:** {status}\n\n💡 Confirmations can take 5-30 min" if lang == 'en' else f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Les confirmations peuvent prendre 5-30 min"),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                            "🔄 Refresh" if lang == 'en' else "🔄 Rafraîchir", callback_data=f'check_payment_{order_id}')]]))
                except Exception:
                    await query.message.reply_text(
                        (f"⏳ **PAYMENT IN PROGRESS**\n\n🔍 **Status:** {status}\n\n💡 Confirmations can take 5-30 min" if lang == 'en' else f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Les confirmations peuvent prendre 5-30 min"),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                            "🔄 Refresh" if lang == 'en' else "🔄 Rafraîchir", callback_data=f'check_payment_{order_id}')]]),
                        parse_mode='Markdown')
        else:
            conn.close()
            try:
                from app.core.i18n import t as i18n
                await query.edit_message_text(
                    i18n(lang, 'err_verify'),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                        i18n(lang, 'btn_retry'), callback_data=f'check_payment_{order_id}')]]))
            except Exception:
                from app.core.i18n import t as i18n
                await query.message.reply_text(
                    i18n(lang, 'err_verify'),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                        i18n(lang, 'btn_retry'), callback_data=f'check_payment_{order_id}')]]))

    async def sell_menu(self, query, lang):
        """Menu vendeur"""
        user_data = self.get_user(query.from_user.id)

        if user_data and user_data['is_seller']:
            await self.seller_dashboard(query, lang)
            return

        keyboard = sell_menu_keyboard(lang)

        sell_text = i18n(lang, 'sell_menu_text')

        try:
            await query.edit_message_text(
                sell_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(
                sell_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')

    async def create_seller_prompt(self, query, lang):
        """Demande les informations pour créer un compte vendeur"""
        # Clear other flows to avoid ID validator collision
        self.reset_conflicting_states(query.from_user.id, keep={'creating_seller'})
        self.update_user_state(query.from_user.id, creating_seller=True, step='name', lang=lang)
        from app.core.i18n import t as i18n
        await query.edit_message_text(
            f"{i18n(lang, 'seller_create_title')}\n\n{i18n(lang, 'seller_create_intro')}\n\n{i18n(lang, 'seller_step1_title')}\n\n{i18n(lang, 'seller_step1_prompt')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_cancel'), callback_data='sell_menu')]]),
            parse_mode='Markdown')

    async def seller_login_menu(self, query, lang):
        """Menu de connexion vendeur"""
        from app.core.i18n import t as i18n
        await query.edit_message_text(
            i18n(lang, 'login_title'),
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton(i18n(lang, 'btn_email'), callback_data='seller_login'),
                InlineKeyboardButton(i18n(lang, 'btn_create_seller'), callback_data='create_seller')
            ], [
                InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='back_main')
            ]]),
            parse_mode='Markdown')

    async def seller_dashboard(self, query, lang):
        """Dashboard vendeur complet"""
        user_data = self.get_user(query.from_user.id)
        # Si on arrive via un bouton et que le flag login est set, on autorise;
        # sinon on redirige vers la connexion
        if not user_data or not user_data['is_seller']:
            await query.edit_message_text(
                "❌ Accès non autorisé.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
            )
            return
        if not self.is_seller_logged_in(query.from_user.id):
            from app.core.i18n import t as i18n
            lang = (self.get_user(query.from_user.id) or {}).get('language_code', 'fr')
            keyboard = [
                [InlineKeyboardButton(i18n(lang, 'btn_email'), callback_data='seller_login')],
                [InlineKeyboardButton(i18n(lang, 'btn_create_seller'), callback_data='create_seller')],
                [InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]
            ]
            await query.edit_message_text(i18n(lang, 'login_subtitle_simple'), reply_markup=InlineKeyboardMarkup(keyboard))
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

        from app.core.i18n import t as i18n
        dashboard_text = (
            f"{i18n(lang, 'dashboard_title')}\n\n"
            f"{i18n(lang, 'welcome_user').format(name=self.escape_markdown(user_data['seller_name']))}\n\n"
            f"📊 **Statistiques :**\n"
            f"{i18n(lang, 'seller_stats_products_active').format(count=active_products)}\n"
            f"{i18n(lang, 'seller_stats_month_sales').format(count=month_sales)}\n"
            f"{i18n(lang, 'seller_stats_month_revenue').format(amount=f"{month_revenue:.2f}")}\n"
            f"{i18n(lang, 'seller_stats_rating').format(rating=f"{user_data['seller_rating']:.1f}")}\n\n"
            f"💸 **Payouts / Adresse :** {i18n(lang, 'wallet_configured') if user_data['seller_solana_address'] else i18n(lang, 'wallet_to_configure')}"
        )

        keyboard = [[
            InlineKeyboardButton(i18n(lang, 'btn_add_product'), callback_data='add_product')
        ], [
            InlineKeyboardButton(i18n(lang, 'btn_my_products'), callback_data='my_products')
        ], [InlineKeyboardButton(i18n(lang, 'btn_my_wallet'), callback_data='my_wallet')],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_seller_analytics'), callback_data='seller_analytics')
                    ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_seller_settings'), callback_data='seller_settings')
                    ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')
                    ]]

        try:
            await query.edit_message_text(
                dashboard_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception:
            await query.edit_message_text(
                dashboard_text.replace('*', ''),
                reply_markup=InlineKeyboardMarkup(keyboard))

    async def add_product_prompt(self, query, lang):
        """Demande les informations pour ajouter un produit"""
        user_data = self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            from app.core.i18n import t as i18n
            await query.edit_message_text(
                i18n(lang, 'err_login_required'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]])
            )
            return

        # Clear conflicting states to avoid search validator catching this step
        self.reset_conflicting_states(query.from_user.id, keep={'adding_product'})
        self.update_user_state(query.from_user.id, adding_product=True, step='title', product_data={}, lang=lang)

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
        user_data = self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            from app.core.i18n import t as i18n
            await query.edit_message_text(
                i18n(lang, 'err_login_required'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]])
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

            keyboard = [[
                InlineKeyboardButton("➕ Créer mon premier produit",
                                     callback_data='add_product')
            ],
                        [
                            InlineKeyboardButton(
                                "🔙 Dashboard",
                                callback_data='seller_dashboard')
                        ]]
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
                        f"✏️ Modifier",
                        callback_data=f'edit_product_{product[0]}'),
                    InlineKeyboardButton(
                        "🗑️ Supprimer",
                        callback_data=f'delete_product_{product[0]}')
                ])

            keyboard.extend([[InlineKeyboardButton("➕ Nouveau produit", callback_data='add_product')],
                             [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')],
                             [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])

        await query.edit_message_text(
            products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def show_wallet(self, query, lang):
        """Affiche les payouts et l'adresse de retrait (Solana)."""
        user_data = self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            from app.core.i18n import t as i18n
            await query.edit_message_text(
                i18n(lang, 'err_login_required'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]])
            )
            return

        if not user_data['seller_solana_address']:
            await query.edit_message_text(
                """💳 **WALLET NON CONFIGURÉ**

    Pour avoir un wallet, vous devez d'abord devenir vendeur.

    Votre adresse Solana sera configurée lors de l'inscription.""",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Devenir vendeur", callback_data='create_seller')],
                    [InlineKeyboardButton("🔙 Retour", callback_data='back_main')]
                ])
            )
            return

        solana_address = user_data['seller_solana_address']

        # Récupérer solde (optionnel)
        try:
            balance = get_solana_balance_display(solana_address)
        except Exception:
            balance = 0.0

        # Calculer payouts en attente
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT COALESCE(SUM(total_amount_sol), 0) 
                FROM seller_payouts 
                WHERE seller_user_id = ? AND payout_status = 'pending'
            ''', (query.from_user.id,))
            pending_amount = cursor.fetchone()[0]
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération payouts en attente: {e}")
            conn.close()
            pending_amount = 0

        wallet_text = f"""💸 **PAYOUTS / ADRESSE DE RETRAIT**

    📍 **Adresse :** `{solana_address}`

    💎 **Solde actuel :** {balance:.6f} SOL
    ⏳ **Payout en attente :** {pending_amount:.6f} SOL

    💡 **Infos payouts :**
    - Traités quotidiennement
    - 95% de vos ventes
    - Commission plateforme : 5%"""

        keyboard = [
            [InlineKeyboardButton("📊 Historique payouts", callback_data='payout_history')],
            [InlineKeyboardButton("📋 Copier adresse", callback_data='copy_address')],
            [InlineKeyboardButton("🔙 Dashboard", callback_data='seller_dashboard')]
        ]

        await query.edit_message_text(
            wallet_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def marketplace_stats(self, query, lang):
        """Statistiques globales de la marketplace"""
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

            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération stats marketplace: {e}")
            conn.close()
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

        keyboard = [[
            InlineKeyboardButton("🔥 Meilleures ventes",
                                 callback_data='category_bestsellers')
        ], [
            InlineKeyboardButton("🆕 Nouveautés", callback_data='category_new')
        ],
                    [
                        InlineKeyboardButton("🏪 Devenir vendeur",
                                             callback_data='sell_menu')
                    ],
                    [
                        InlineKeyboardButton("🏠 Accueil",
                                             callback_data='back_main')
                    ]]

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def handle_text_message(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire principal des messages texte"""
        user_id = update.effective_user.id
        message_text = update.message.text

        # S'assurer qu'un état existe pour l'utilisateur, il peut être vide mais persistant
        self.memory_cache.setdefault(user_id, {})

        user_state = self.get_user_state(user_id)

        # === CRÉATION VENDEUR (prioritaire pour éviter la collision avec recherche) ===
        if user_state.get('creating_seller'):
            await self.process_seller_creation(update, message_text)

        # === CONNEXION VENDEUR ===
        elif user_state.get('seller_login'):
            await self.process_seller_login(update, message_text)

        # === RECHERCHE PRODUIT ===
        elif user_state.get('waiting_for_product_id'):
            await self.process_product_search(update, message_text)

        # === AJOUT PRODUIT ===
        elif user_state.get('adding_product'):
            await self.process_product_addition(update, message_text)

        # === SAISIE CODE PARRAINAGE ===
        # (Supprimé) Saisie code parrainage

        # === CRÉATION TICKET SUPPORT ===
        elif user_state.get('creating_ticket'):
            await self.process_support_ticket(update, message_text)
        elif user_state.get('waiting_reply_ticket_id'):
            from app.integrations.telegram.handlers import support_handlers as sh
            await sh.process_messaging_reply(self, update, message_text)
        elif user_state.get('waiting_admin_reply_ticket_id'):
            from app.integrations.telegram.handlers import support_handlers as sh
            await sh.process_admin_reply(self, update, message_text)

        # === RÉCUPÉRATION PAR EMAIL ===
        elif user_state.get('waiting_for_recovery_email'):
            await self.process_recovery_email(update, message_text)

        # === RÉCUPÉRATION CODE ===
        elif user_state.get('waiting_for_recovery_code'):
            await self.process_recovery_code(update, message_text)
        elif user_state.get('waiting_new_password'):
            await self.process_set_new_password(update, message_text)

        # === CONNEXION (email + code fourni lors de la création) ===
        elif user_state.get('login_wait_email'):
            await self.process_login_email(update, message_text)
        elif user_state.get('login_wait_code'):
            await self.process_login_code(update, message_text)

        # === PARAMÈTRES VENDEUR ===
        elif user_state.get('editing_settings'):
            await self.process_seller_settings(update, message_text)
        # === ÉDITION PRODUIT ===
        elif user_state.get('editing_product'):
            step = user_state.get('step')
            product_id = user_state.get('product_id')
            if step == 'edit_title_input':
                new_title = message_text.strip()[:100]
                try:
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE products SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (new_title, product_id, user_id))
                    conn.commit()
                    conn.close()
                    # Nettoyer uniquement le contexte d'édition produit
                    state = self.get_user_state(user_id)
                    for k in ['editing_product', 'product_id', 'step']:
                        state.pop(k, None)
                    self.memory_cache[user_id] = state
                    await update.message.reply_text("✅ Titre mis à jour.")
                except Exception as e:
                    logger.error(f"Erreur maj titre produit: {e}")
                    await update.message.reply_text("❌ Erreur mise à jour titre.")
            elif step == 'edit_price_input':
                try:
                    price = float(message_text.replace(',', '.'))
                    if price < 1 or price > 5000:
                        raise ValueError("Prix hors limites")
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE products SET price_eur = ?, price_usd = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (price, price * self.get_exchange_rate(), product_id, user_id))
                    conn.commit()
                    conn.close()
                    # Nettoyer uniquement le contexte d'édition produit
                    state = self.get_user_state(user_id)
                    for k in ['editing_product', 'product_id', 'step']:
                        state.pop(k, None)
                    self.memory_cache[user_id] = state
                    await update.message.reply_text("✅ Prix mis à jour.")
                except Exception as e:
                    logger.error(f"Erreur maj prix produit: {e}")
                    await update.message.reply_text("❌ Prix invalide ou erreur mise à jour.")
            else:
                await update.message.reply_text("💬 Choisissez l'action d'édition depuis le menu.")
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
            from app.core.i18n import t as i18n
            lang = user_state.get('lang','fr')
            await update.message.reply_text(
                f"❌ **Format ID invalide :** `{self.escape_markdown(product_id)}`\n\n💡 **Format attendu :** `TBF-2501-ABC123`",
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='buy_menu')
                ]]),
                parse_mode='Markdown')
            return

        # Chercher le produit
        product = self.get_product_by_id(product_id)

        # Nettoyer uniquement l'état de recherche
        if user_id in self.memory_cache:
            state = self.memory_cache.get(user_id, {})
            for k in ['waiting_for_product_id']:
                state.pop(k, None)
            self.memory_cache[user_id] = state

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
        from app.core.i18n import t as i18n
        # Secure dynamic fields for Markdown
        safe_title = self.escape_markdown(str(product.get('title') or ''))
        safe_seller = self.escape_markdown(str(product.get('seller_name') or ''))
        safe_category = self.escape_markdown(str(product.get('category') or ''))
        desc_raw = product.get('description') or 'Aucune description disponible'
        safe_desc = self.escape_markdown(str(desc_raw))

        product_text = (
            f"📦 **{safe_title}**\n\n"
            f"👤 **Vendeur :** {safe_seller} ({product['seller_rating']:.1f}/5)\n"
            f"📂 **Catégorie :** {safe_category}\n"
            f"💰 **Prix :** {product['price_eur']}€\n\n"
            f"📖 **Description :**\n{safe_desc}\n\n"
            f"📊 **Statistiques :**\n"
            f"• 👁️ {product['views_count']} vues\n"
            f"• 🛒 {product['sales_count']} ventes\n\n"
            f"📁 **Fichier :** {product['file_size_mb']:.1f} MB"
        )

        lang = (self.get_user(update.effective_user.id) or {}).get('language_code', 'fr')
        keyboard = [[
            InlineKeyboardButton(i18n(lang, 'btn_buy'), callback_data=f'buy_product_{product["product_id"]}')
        ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_other_products'), callback_data='browse_categories')
                    ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_back'), callback_data='buy_menu')
                    ]]

        try:
            await update.message.reply_text(
                product_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(
                product_text.replace('*',''),
                reply_markup=InlineKeyboardMarkup(keyboard))

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

            from app.core.i18n import t as i18n
            safe_name = self.escape_markdown(message_text)
            await update.message.reply_text(
                f"✅ **Nom :** {safe_name}\n\n{i18n(user_state.get('lang','fr'), 'seller_step2_title')}\n\n{i18n(user_state.get('lang','fr'), 'seller_step2_prompt')}",
                parse_mode='Markdown')

        elif step == 'bio':
            # Étape 2 : Bio
            user_state['seller_bio'] = message_text[:500]
            user_state['step'] = 'email'

            from app.core.i18n import t as i18n
            lang = user_state.get('lang','fr')
            await update.message.reply_text(
                f"✅ **Bio sauvegardée**\n\n{i18n(lang, 'seller_step3_title')}\n\n{i18n(lang, 'seller_step3_prompt')}\n\n⚠️ **Important :** " + ("This email will be used to recover your seller account" if lang=='en' else "Cet email servira à récupérer votre compte vendeur"),
                parse_mode='Markdown')

        elif step == 'email':
            # Étape 3 : Email
            email = message_text.strip().lower()

            from app.core.i18n import t as i18n
            lang = user_state.get('lang','fr')
            if not validate_email(email):
                await update.message.reply_text(i18n(lang, 'err_invalid_email'))
                return

            user_state['recovery_email'] = email
            user_state['step'] = 'password'

            from app.core.i18n import t as i18n
            await update.message.reply_text(i18n(user_state.get('lang','fr'), 'seller_password_prompt'), parse_mode='Markdown')

        elif step == 'password':
            # Étape 4 : Mot de passe
            password = message_text.strip()
            if len(password) < 8:
                await update.message.reply_text("❌ Mot de passe trop court (8 caractères minimum).")
                return
            user_state['password'] = password
            user_state['step'] = 'solana_address'

            from app.core.i18n import t as i18n
            lang = user_state.get('lang','fr')
            prompt = ("""📍 **Solana address**

Enter your Solana address to receive your payouts:

💡 **How to find your address:**
- Open Phantom, Solflare, or your Solana wallet
- Click \"Receive\"
- Copy the address (format: `5Fxk...abc`)""" if lang=='en' else f"{i18n(lang, 'seller_step4_title')}\n\n{i18n(lang, 'seller_step4_prompt')}\n\n💡 **Comment trouver votre adresse :**\n- Ouvrez Phantom, Solflare ou votre wallet Solana\n- Cliquez \"Receive\" ou \"Recevoir\"\n- Copiez l'adresse (format : `5Fxk...abc`)")
            await update.message.reply_text(prompt, parse_mode='Markdown')

        elif step == 'solana_address':
            # Étape 4 : Adresse Solana
            solana_address = message_text.strip()

            from app.core.i18n import t as i18n
            lang = user_state.get('lang','fr')
            if not validate_solana_address(solana_address):
                await update.message.reply_text(i18n(lang, 'err_invalid_solana'))
                return

            # Créer le compte vendeur
            user_cache = self.get_user_state(user_id)
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
                from app.core.i18n import t as i18n
                msg = i18n(user_state.get('lang','fr'), 'seller_created_msg').format(
                    name=self.escape_markdown(user_cache['seller_name']),
                    email=self.escape_markdown(user_cache['recovery_email']),
                    address=self.escape_markdown(solana_address)
                )
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(i18n(user_state.get('lang','fr'), 'btn_dashboard'), callback_data='seller_dashboard')]]),
                    parse_mode='Markdown')
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

            from app.core.i18n import t as i18n
            lang = user_state.get('lang','fr')
            await update.message.reply_text(
                f"✅ **Titre :** {self.escape_markdown(message_text)}\n\n📝 **Étape 2/5 : Description**\n\n" + ("Describe your course (content, goals, prerequisites...) :" if lang=='en' else "Decrivez votre formation (contenu, objectifs, prérequis...) :"),
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
                ("✅ **Description saved**\n\n📂 **Step 3/5: Category**\n\nChoose a category:" if user_state.get('lang','fr')=='en' else "✅ **Description sauvegardée**\n\n📂 **Étape 3/5 : Catégorie**\n\nChoisissez la catégorie :"),
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
        state = self.get_user_state(user_id)
        step = state.get('step')

        if step == 'subject':
            state['subject'] = message_text[:100]
            state['step'] = 'message'
            # UI i18n
            user_data = self.get_user(user_id)
            lang = user_data['language_code'] if user_data else 'fr'
            await update.message.reply_text("Enter your detailed message:" if lang == 'en' else "Entrez votre message détaillé:")
            return

        if step == 'message':
            user_data = self.get_user(user_id)
            lang = user_data['language_code'] if user_data else 'fr'
            subject = state.get('subject', 'No subject' if lang == 'en' else 'Sans sujet')
            content = message_text[:2000]

            from app.services.support_service import SupportService
            ticket_id = SupportService(self.db_path).create_ticket(user_id, subject, content)
            if ticket_id:
                # Nettoyer uniquement le contexte de création de ticket
                state = self.get_user_state(user_id)
                for k in ['creating_ticket', 'step', 'subject']:
                    state.pop(k, None)
                self.memory_cache[user_id] = state
                await update.message.reply_text(
                    (f"🎫 Ticket created: {ticket_id}\nOur team will get back to you soon." if lang == 'en' else f"🎫 Ticket créé: {ticket_id}\nNotre équipe vous répondra bientôt."))
            else:
                await update.message.reply_text("❌ Error while creating the ticket." if lang == 'en' else "❌ Erreur lors de la création du ticket.")

    async def process_messaging_reply(self, update: Update, message_text: str):
        """Ajoute un message dans le thread Acheteur↔Vendeur et notifie le vendeur (plus tard admin)."""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        ticket_id = state.get('waiting_reply_ticket_id')
        if not ticket_id:
            await update.message.reply_text("❌ Session expirée. Relancez le contact vendeur depuis votre bibliothèque.")
            return
        msg = message_text.strip()
        if not msg:
            await update.message.reply_text("❌ Message vide.")
            return
        try:
            from app.services.messaging_service import MessagingService
            ok = MessagingService(self.db_path).post_user_message(ticket_id, user_id, msg)
            if not ok:
                await update.message.reply_text("❌ Erreur lors de l'envoi du message.")
                return
            # Nettoyer l'état de saisie
            state.pop('waiting_reply_ticket_id', None)
            self.memory_cache[user_id] = state

            # Afficher le récapitulatif des derniers messages
            messages = MessagingService(self.db_path).list_recent_messages(ticket_id, 5)
            thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
            keyboard = [[
                InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
                InlineKeyboardButton("🚀 Escalader", callback_data=f'escalate_ticket_{ticket_id}')
            ]]
            await update.message.reply_text(f"✅ Message envoyé.\n\n🧵 Derniers messages:\n{thread}", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Erreur reply ticket: {e}")
            await update.message.reply_text("❌ Erreur interne.")

    async def view_ticket(self, query, ticket_id: str):
        try:
            from app.services.messaging_service import MessagingService
            messages = MessagingService(self.db_path).list_recent_messages(ticket_id, 10)
            if not messages:
                await query.edit_message_text("🎫 Aucun message dans ce ticket.")
                return
            thread = "\n".join([f"[{m['created_at']}] {m['sender_role']}: {m['message']}" for m in reversed(messages)])
            keyboard = [[
                InlineKeyboardButton("↩️ Répondre", callback_data=f'reply_ticket_{ticket_id}'),
                InlineKeyboardButton("🚀 Escalader", callback_data=f'escalate_ticket_{ticket_id}')
            ]]
            await query.edit_message_text(f"🧵 Thread ticket `{ticket_id}`:\n\n{thread}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Erreur view ticket: {e}")
            await query.edit_message_text("❌ Erreur interne.")

    async def reply_ticket_prepare(self, query, ticket_id: str):
        self.reset_conflicting_states(query.from_user.id, keep={'waiting_reply_ticket_id'})
        self.update_user_state(query.from_user.id, waiting_reply_ticket_id=ticket_id)
        await query.edit_message_text("✍️ Écrivez votre réponse:")

    async def escalate_ticket(self, query, ticket_id: str):
        try:
            from app.services.messaging_service import MessagingService
            ok = MessagingService(self.db_path).escalate(ticket_id, ADMIN_USER_ID or query.from_user.id)
            if not ok:
                await query.edit_message_text("❌ Impossible d'escalader ce ticket.")
                return
            await query.edit_message_text("🚀 Ticket escaladé au support.")
        except Exception as e:
            logger.error(f"Erreur escalade: {e}")
            await query.edit_message_text("❌ Erreur interne.")

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
                # Nettoyer uniquement le contexte d'édition paramètres
                state = self.get_user_state(user_id)
                for k in ['editing_settings', 'step']:
                    state.pop(k, None)
                self.memory_cache[user_id] = state
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
                # Nettoyer uniquement le contexte d'édition paramètres
                state = self.get_user_state(user_id)
                for k in ['editing_settings', 'step']:
                    state.pop(k, None)
                self.memory_cache[user_id] = state
                await update.message.reply_text("✅ Biographie mise à jour.")
            except Exception as e:
                logger.error(f"Erreur maj bio vendeur: {e}")
                await update.message.reply_text("❌ Erreur mise à jour bio.")

    async def process_admin_search_user(self, update: Update, message_text: str):
        admin_id = update.effective_user.id
        self.memory_cache.pop(admin_id, None)
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            # Essayer par user_id
            if message_text.isdigit():
                cursor.execute('SELECT user_id, username, first_name, is_seller, is_partner, partner_code FROM users WHERE user_id = ?', (int(message_text),))
            else:
                cursor.execute('SELECT user_id, username, first_name, is_seller, is_partner, partner_code FROM users WHERE partner_code = ?', (message_text.strip(),))
            row = cursor.fetchone()
            conn.close()
            if not row:
                await update.message.reply_text("❌ Utilisateur non trouvé.")
                return
            await update.message.reply_text(f"ID: {row[0]}\nUser: {row[1]}\nNom: {row[2]}\nVendeur: {bool(row[3])}\nPartenaire: {bool(row[4])}\nCode: {row[5]}")
        except Exception as e:
            logger.error(f"Erreur admin search user: {e}")
            await update.message.reply_text("❌ Erreur recherche utilisateur.")

    async def process_admin_search_product(self, update: Update, message_text: str):
        admin_id = update.effective_user.id
        self.memory_cache.pop(admin_id, None)
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT product_id, title, price_eur, status FROM products WHERE product_id = ?', (message_text.strip(),))
            row = cursor.fetchone()
            conn.close()
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
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET status='inactive' WHERE product_id = ?", (message_text.strip(),))
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ Produit suspendu si trouvé.")
        except Exception as e:
            logger.error(f"Erreur suspend product: {e}")
            await update.message.reply_text("❌ Erreur suspension produit.")

    # (Supprimé) process_referral_input

    async def change_language(self, query, lang):
        """Change la langue - CORRIGÉ"""
        user_id = query.from_user.id

        # Valider la langue
        supported_languages = ['fr', 'en']
        if lang not in supported_languages:
            await query.answer("❌ Langue non supportée")
            return

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET language_code = ? WHERE user_id = ?', (lang, user_id))
            conn.commit()
            conn.close()

            # Mettre à jour aussi l'état mémoire pour utilisation immédiate
            self.update_user_state(user_id, lang=lang)

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
                'support': '🆘 Support & aide',
                'seller_dashboard': '🏪 Mon espace vendeur',
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
                'support': '🆘 Support & help',
                'seller_dashboard': '🏪 Seller dashboard',
                'back': '🔙 Back',
                'error_occurred': '❌ An error occurred. Please try again later.',
            }
        }
        return texts.get(lang, texts['fr']).get(key, key)

    def tr(self, lang: str, fr_text: str, en_text: str) -> str:
        """Retourne le texte dans la langue demandée, FR par défaut."""
        return en_text if lang == 'en' else fr_text

    async def back_to_main(self, query):
        """Menu principal avec récupération"""
        user_id = query.from_user.id
        user_data = self.get_user(user_id)
        lang = user_data['language_code'] if user_data else 'fr'
        is_seller = user_data and user_data['is_seller']

        keyboard = [[InlineKeyboardButton(self.get_text('buy_menu', lang), callback_data='buy_menu')]]
        if is_seller:
            keyboard.append([InlineKeyboardButton(self.get_text('seller_dashboard', lang), callback_data='seller_dashboard')])
        else:
            keyboard.append([InlineKeyboardButton(self.get_text('sell_menu', lang), callback_data='sell_menu')])

        keyboard.extend([
            [InlineKeyboardButton(self.get_text('support', lang), callback_data='support_menu')],
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data='lang_fr'),
                InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')
            ]
        ])

        welcome_text = self.get_text('welcome', lang)
        try:
            await query.edit_message_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Redirige vers la FAQ en respectant la langue de l'utilisateur."""
        user = update.effective_user
        user_data = self.get_user(user.id)
        lang = user_data['language_code'] if user_data else (user.language_code or 'fr')
        # Utiliser le même écran que le bouton FAQ
        class DummyQuery:
            def __init__(self, uid):
                self.from_user = type('u', (), {'id': uid})
            async def edit_message_text(self, *args, **kwargs):
                await update.message.reply_text(*args, **kwargs)
        await self.show_faq(DummyQuery(user.id), lang)

    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Redirige vers la création de ticket de support directement."""
        user = update.effective_user
        user_data = self.get_user(user.id)
        lang = user_data['language_code'] if user_data else (user.language_code or 'fr')
        # Ouvre directement la création de ticket
        class DummyQuery:
            def __init__(self, uid):
                self.from_user = type('u', (), {'id': uid})
            async def edit_message_text(self, *args, **kwargs):
                await update.message.reply_text(*args, **kwargs)
        await self.create_ticket(DummyQuery(user.id), lang)

    async def account_recovery_menu(self, query, lang):
        """Menu de récupération de compte"""
        await query.edit_message_text((
            """🔐 **ACCOUNT RECOVERY**

If you've lost access to your seller account:

📧 **Reset by email:**
- Enter your recovery email
- You receive a one-time code
- Enter the code
- Set a new password

🎫 **Manual support:**
- Contact our team with proof""" if lang == 'en' else
            """🔐 **RÉCUPÉRATION COMPTE VENDEUR**

Si vous avez perdu l'accès à votre compte vendeur :

📧 **Réinitialisation par email :**
- Entrez votre email de récupération
- Vous recevez un code unique
- Entrez le code
- Choisissez un nouveau mot de passe

🎫 **Support manuel :**
- Contactez notre équipe avec preuves"""
        ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📧 Récupération par email", callback_data='recovery_by_email')],
                [InlineKeyboardButton("🎫 Contacter support", callback_data='create_ticket')],
                [InlineKeyboardButton("🔙 Retour", callback_data='back_main')]
            ]),
            parse_mode='Markdown'
        )

    async def recovery_by_email_prompt(self, query, lang):
        """Demande l'email pour récupération"""
        self.update_user_state(query.from_user.id, waiting_for_recovery_email=True, lang=lang)

        await query.edit_message_text((
            """📧 **EMAIL RECOVERY**

Enter the email of your seller account:

✍️ **Type your email:**""" if lang == 'en' else
            """📧 **RÉCUPÉRATION PAR EMAIL**

Saisissez l'email de votre compte vendeur :

✍️ **Tapez votre email :**"""
        ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Retour", callback_data='account_recovery')]
            ]))

    async def process_recovery_email(self, update: Update, message_text: str):
        """Traite l'entrée d'email et envoie un code si l'email existe."""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        if not validate_email(email):
            from app.core.i18n import t as i18n
            lang = (self.get_user(user_id) or {}).get('language_code', 'fr')
            await update.message.reply_text(i18n(lang, 'err_invalid_email'))
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT user_id FROM users WHERE recovery_email = ?', (email,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                await update.message.reply_text("❌ Email non trouvé.")
                # Nettoyer uniquement le contexte de récupération
                state = self.get_user_state(user_id)
                for k in ['waiting_for_recovery_email', 'email']:
                    state.pop(k, None)
                self.memory_cache[user_id] = state
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
                    msg['Subject'] = "Seller password reset code"
                    body = (f"Your reset code: {recovery_code}\nValid for 15 minutes" if (self.get_user(user_id) or {}).get('language_code') == 'en' else f"Votre code de réinitialisation: {recovery_code}\nValide 15 minutes")
                    msg.attach(MIMEText(body, 'plain'))

                    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                    server.starttls()
                    server.login(SMTP_EMAIL, SMTP_PASSWORD)
                    server.sendmail(SMTP_EMAIL, email, msg.as_string())
                    server.quit()
                except Exception as e:
                    logger.error(f"Erreur envoi email: {e}")

            # Poursuivre le flow: demander le code puis le nouveau mot de passe
            # Désactiver l'attente d'email pour éviter la confusion "Email invalide"
            self.update_user_state(
                user_id,
                waiting_for_recovery_email=False,
                login_wait_email=False,
                login_wait_code=False,
                waiting_for_recovery_code=True,
                email=email
            )
            await update.message.reply_text(
                "📧 Code envoyé. Entrez votre code à 6 chiffres:")
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération par email: {e}")
            conn.close()
            await update.message.reply_text("❌ Erreur interne.")

    async def process_recovery_code(self, update: Update, message_text: str):
        """Valide le code de récupération et passe à la saisie d'un nouveau mot de passe."""
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

            # Passer à l'étape de nouveau mot de passe
            conn.close()
            self.update_user_state(user_id, waiting_for_recovery_code=False, waiting_new_password=True)
            await update.message.reply_text("🔒 Entrez votre nouveau mot de passe (8+ caractères):")
        except Exception as e:
            logger.error(f"Erreur vérification code: {e}")
            await update.message.reply_text("❌ Erreur interne.")

    async def process_set_new_password(self, update: Update, message_text: str):
        """Définit un nouveau mot de passe après validation du code."""
        user_id = update.effective_user.id
        new_password = message_text.strip()
        if len(new_password) < 8:
            await update.message.reply_text("❌ Mot de passe trop court (8+ caractères).")
            return

        # Récupérer l'email stocké lors de l'étape précédente
        state = self.get_user_state(user_id)
        email = state.get('email')
        if not email:
            await update.message.reply_text("❌ Session expirée. Recommencez la récupération.")
            state.pop('waiting_new_password', None)
            self.memory_cache[user_id] = state
            return

        try:
            salt = generate_salt()
            pwd_hash = hash_password(new_password, salt)
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET password_salt = ?, password_hash = ?, recovery_code_hash = NULL WHERE recovery_email = ?', (salt, pwd_hash, email))
            conn.commit()
            conn.close()

            # Nettoyer l'état de récupération
            for k in ['waiting_new_password', 'email']:
                state.pop(k, None)
            self.memory_cache[user_id] = state

            await update.message.reply_text("✅ Mot de passe mis à jour. Connectez-vous avec email + mot de passe.")
        except Exception as e:
            logger.error(f"Erreur reset mot de passe: {e}")
            await update.message.reply_text("❌ Erreur interne.")

    async def process_login_email(self, update: Update, message_text: str):
        """Étape 1 du login: saisir l'email enregistré lors de la création vendeur."""
        user_id = update.effective_user.id
        email = message_text.strip().lower()
        if not validate_email(email):
            await update.message.reply_text("❌ Email invalide. Recommencez.")
            return
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            # Accept login by email regardless of Telegram account binding
            cursor.execute('SELECT user_id FROM users WHERE recovery_email = ?', (email,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                from app.core.i18n import t as i18n
                await update.message.reply_text(i18n(lang, 'err_invalid_email'))
                return
            # Passer proprement à l'étape mot de passe et désactiver la saisie email
            self.update_user_state(user_id, login_wait_email=False, login_wait_code=True, login_email=email)
            await update.message.reply_text(i18n(lang, 'prompt_enter_password'))
        except Exception as e:
            logger.error(f"Erreur login email: {e}")
            await update.message.reply_text("❌ Erreur interne.")

    async def process_login_code(self, update: Update, message_text: str):
        """Étape 2 du login: vérifier email + mot de passe (hash en DB)."""
        user_id = update.effective_user.id
        state = self.memory_cache.get(user_id, {})
        email = state.get('login_email')
        password = message_text.strip()
        if len(password) < 1:
            await update.message.reply_text(
                "❌ Mot de passe invalide.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Réessayer", callback_data='retry_password')], [InlineKeyboardButton("📧 Réinitialiser mot de passe", callback_data='account_recovery')]])
            )
            return
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            if email:
                cursor.execute('SELECT password_salt, password_hash FROM users WHERE user_id = ? AND recovery_email = ?', (user_id, email))
                row = cursor.fetchone()
            else:
                cursor.execute('SELECT password_salt, password_hash FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
            conn.close()
            if not row or not row[0] or not row[1]:
                await update.message.reply_text(
                    "❌ Identifiants incorrects.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Réessayer", callback_data='retry_password')], [InlineKeyboardButton("📧 Réinitialiser mot de passe", callback_data='account_recovery')]])
                )
                return
            salt, stored_hash = row
            if hash_password(password, salt) != stored_hash:
                await update.message.reply_text(
                    "❌ Identifiants incorrects.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Réessayer", callback_data='retry_password')], [InlineKeyboardButton("📧 Réinitialiser mot de passe", callback_data='account_recovery')]])
                )
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
        from app.core.i18n import t as i18n
        lang = (self.get_user(update.effective_user.id) or {}).get('language_code', 'fr')
        keyboard = [[
                        InlineKeyboardButton(
                            "📊 Stats marketplace",
                            callback_data='admin_marketplace_stats')
                    ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_admin_payouts'),
                                             callback_data='admin_payouts')
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

        from app.core.i18n import t as i18n
        lang = (self.get_user(query.from_user.id) or {}).get('language_code', 'fr')
        keyboard = [[
                        InlineKeyboardButton(
                            "📊 Stats marketplace",
                            callback_data='admin_marketplace_stats')
                    ],
                    [
                        InlineKeyboardButton(i18n(lang, 'btn_admin_payouts'),
                                             callback_data='admin_payouts')
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
        """Affiche les commissions à payer"""
        if query.from_user.id != ADMIN_USER_ID:
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        # Commissions non payées
        try:
            cursor.execute('''
                SELECT o.order_id, o.partner_code, o.partner_commission, o.created_at,
                       u.first_name, p.title
                FROM orders o
                LEFT JOIN users u ON u.partner_code = o.partner_code
                LEFT JOIN products p ON p.product_id = o.product_id
                WHERE o.payment_status = 'completed' 
                AND o.commission_paid = FALSE
                AND o.partner_commission > 0
                ORDER BY o.created_at DESC
            ''')

            unpaid = cursor.fetchall()

            # Total à payer
            cursor.execute('''
                SELECT SUM(partner_commission) 
                FROM orders 
                WHERE payment_status = 'completed' 
                AND commission_paid = FALSE
            ''')
            total_due = cursor.fetchone()[0] or 0

            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Erreur récupération commissions (admin): {e}")
            conn.close()
            return

        if not unpaid:
            text = "💰 **COMMISSIONS**\n\n✅ Aucune commission en attente !"
        else:
            text = f"💰 **COMMISSIONS À PAYER**\n\n💸 **Total à payer : {total_due:.2f}€**\n\n"

            for comm in unpaid:
                text += f"📋 **Commande :** `{comm[0]}`\n"
                text += f"👤 **Partenaire :** {comm[4] or 'Anonyme'} (`{comm[1]}`)\n"
                text += f"📦 **Produit :** {comm[5]}\n"
                text += f"💰 **Commission :** {comm[2]:.2f}€\n"
                text += f"📅 **Date :** {comm[3][:10]}\n"
                text += "---\n"

        keyboard = [[
            InlineKeyboardButton("✅ Marquer comme payées",
                                 callback_data='admin_mark_paid')
        ], [
            InlineKeyboardButton("🔙 Retour admin", callback_data='admin_menu')
        ]]

        await query.edit_message_text(
            text[:4000],  # Limite Telegram
            reply_markup=InlineKeyboardMarkup(keyboard),
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

            # Commissions en attente
            cursor.execute(
                'SELECT COALESCE(SUM(partner_commission), 0) FROM orders WHERE payment_status = "completed" AND commission_paid = FALSE'
            )
            pending_commissions = cursor.fetchone()[0]

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
• Commissions en attente : {pending_commissions:.2f}€

📈 **Taux plateforme :** {PLATFORM_COMMISSION_RATE*100}%
💸 **Moyenne par vente :** {total_volume/max(total_sales,1):.2f}€"""

        keyboard = [[
            InlineKeyboardButton("💰 Traiter commissions",
                                 callback_data='admin_commissions')
        ],
                    [
                        InlineKeyboardButton("📦 Gérer produits",
                                             callback_data='admin_products')
                    ],
                    [
                        InlineKeyboardButton("🔙 Panel admin",
                                             callback_data='admin_menu')
                    ]]

        await query.edit_message_text(
            stats_text,
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
            if document.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                await update.message.reply_text(
                    f"❌ **Fichier trop volumineux**\n\nTaille max : {MAX_FILE_SIZE_MB}MB\nVotre fichier : {file_size_mb:.1f}MB",
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
            await update.message.reply_text(i18n(user_state.get('lang','fr'), 'upload_in_progress'), parse_mode='Markdown')

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
                # Nettoyer uniquement le contexte d'ajout de produit et conserver la session/login
                state = self.get_user_state(user_id)
                for k in ['adding_product', 'step', 'product_data']:
                    state.pop(k, None)
                self.memory_cache[user_id] = state

                # Échapper Markdown via utilitaire
                safe_filename = self.escape_markdown(filename)
                safe_title = self.escape_markdown(product_data['title'])
                safe_category = self.escape_markdown(product_data['category'])

                lang = user_state.get('lang','fr')
                success_text = (
                    f"{i18n(lang, 'product_created_title')}\n\n"
                    f"{i18n(lang, 'product_created_id').format(id=product_id)}\n"
                    f"{i18n(lang, 'product_created_name').format(title=safe_title)}\n"
                    f"{i18n(lang, 'product_created_price').format(price=product_data['price_eur'])}\n"
                    f"{i18n(lang, 'product_created_category').format(category=safe_category)}\n"
                    f"{i18n(lang, 'product_created_file').format(filename=safe_filename)}\n\n"
                    f"{i18n(lang, 'product_created_ready')}\n\n"
                    f"{i18n(lang, 'product_created_hint').format(id=product_id)}"
                )

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
        from app.core.i18n import t as i18n
        keyboard = [
            [InlineKeyboardButton(i18n(lang, 'btn_faq'), callback_data='faq')],
            [InlineKeyboardButton(i18n(lang, 'btn_create_ticket'), callback_data='create_ticket')],
            [InlineKeyboardButton(i18n(lang, 'btn_my_tickets'), callback_data='my_tickets')],
            [InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')]
        ]
        support_text = f"{i18n(lang, 'support_title')}\n\n{i18n(lang, 'support_sub')}"

        await query.edit_message_text(
            support_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def show_faq(self, query, lang):
        """Affiche la FAQ"""
        if lang == 'en':
            faq_text = """**FAQ**

Q: How to buy a course?
A: Browse categories or search by ID.

Q: How to sell a course?
A: Become a seller and add your products.

Q: How to recover my account?
A: Use the recovery email."""
            keyboard = [[InlineKeyboardButton("Back", callback_data='support_menu')]]
        else:
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
        self.update_user_state(query.from_user.id, creating_ticket=True, step='subject', lang=lang)
        if lang == 'en':
            await query.edit_message_text(
                "🆘 New ticket\n\nEnter a subject for your request:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='support_menu')]])
            )
        else:
            await query.edit_message_text(
                "🆘 Nouveau ticket\n\nEntrez un sujet pour votre demande:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='support_menu')]])
            )

    async def show_my_tickets(self, query, lang):
        """Affiche les tickets de support de l'utilisateur"""
        try:
            from app.services.support_service import SupportService
            rows = SupportService(self.db_path).list_user_tickets(query.from_user.id, 10)
        except Exception as e:
            logger.error(f"Erreur tickets: {e}")
            await query.edit_message_text("❌ Erreur récupération tickets.")
            return

        if not rows:
            await query.edit_message_text("🎫 Aucun ticket.")
            return

        text = "🎫 Vos tickets:\n\n"
        for t in rows:
            text += f"• {t['ticket_id']} — {t['subject']} — {t['status']}\n"
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
            keyboard.append([
                InlineKeyboardButton("📥 Télécharger", callback_data=f'download_product_{product_id}'),
                InlineKeyboardButton("📨 Contacter le vendeur", callback_data=f'contact_seller_{product_id}')
            ])

        keyboard.append([InlineKeyboardButton("🏠 Accueil", callback_data='back_main')])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def contact_seller_start(self, query, product_id: str, lang: str):
        """Démarre un thread Acheteur↔Vendeur uniquement si la commande est payée."""
        buyer_id = query.from_user.id
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.order_id, p.seller_user_id, p.title
                FROM orders o
                JOIN products p ON p.product_id = o.product_id
                WHERE o.buyer_user_id = ? AND o.product_id = ? AND o.payment_status = 'completed'
                ORDER BY o.completed_at DESC LIMIT 1
            ''', (buyer_id, product_id))
            row = cursor.fetchone()
            conn.close()
            if not row:
                await query.edit_message_text("❌ Vous devez avoir acheté ce produit pour contacter le vendeur.")
                return
            order_id, seller_user_id, title = row
        except Exception as e:
            logger.error(f"Erreur recherche commande pour contact vendeur: {e}")
            await query.edit_message_text("❌ Erreur lors de l'initiation du contact.")
            return

        try:
            from app.services.messaging_service import MessagingService
            ticket_id = MessagingService(self.db_path).start_or_get_ticket(buyer_id, order_id, seller_user_id, f"Contact vendeur: {title}")
            if not ticket_id:
                await query.edit_message_text("❌ Impossible de créer le ticket.")
                return
            # Armer l'état de réponse utilisateur
            self.reset_conflicting_states(buyer_id, keep={'waiting_reply_ticket_id'})
            self.update_user_state(buyer_id, waiting_reply_ticket_id=ticket_id)
            await query.edit_message_text(
                f"📨 Contact vendeur pour `{title}`\n\n✍️ Écrivez votre message:",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Erreur init ticket: {e}")
            await query.edit_message_text("❌ Erreur lors de la création du ticket.")

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
        await query.answer()
        user_data = self.get_user(query.from_user.id)
        addr = (user_data or {}).get('seller_solana_address')
        if not addr:
            await query.edit_message_text("❌ Aucune adresse configurée.")
            return
        try:
            await query.message.reply_text(f"📋 Adresse de retrait:\n`{addr}`\n\nCopiez-collez cette adresse dans votre wallet.", parse_mode='Markdown')
        except Exception:
            await query.edit_message_text(f"📋 Adresse de retrait:\n`{addr}`\n\nCopiez-collez cette adresse dans votre wallet.", parse_mode='Markdown')

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
        self.update_user_state(query.from_user.id, editing_settings=True, step='menu')
        from app.core.i18n import t as i18n
        keyboard = [
            [InlineKeyboardButton("✏️ " + ("Edit name" if lang=='en' else "Modifier nom"), callback_data='edit_seller_name')],
            [InlineKeyboardButton("📝 " + ("Edit bio" if lang=='en' else "Modifier bio"), callback_data='edit_seller_bio')],
            [InlineKeyboardButton(i18n(lang, 'btn_my_wallet'), callback_data='my_wallet')],
            [InlineKeyboardButton(i18n(lang, 'btn_logout'), callback_data='seller_logout')],
            [InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')],
        ]
        await query.edit_message_text(("Seller settings:" if lang=='en' else "Paramètres vendeur :"), reply_markup=InlineKeyboardMarkup(keyboard))

    async def seller_info(self, query, lang):
        await query.edit_message_text("Conditions & avantages vendeur (à implémenter)")

    async def admin_mark_all_payouts_paid(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        try:
            from app.services.payout_service import PayoutService
            ok = PayoutService(self.db_path).mark_all_pending_as_completed()
            if ok:
                await query.edit_message_text("✅ Tous les payouts en attente ont été marqués comme payés.")
            else:
                await query.edit_message_text("❌ Erreur lors du marquage des payouts.")
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
        self.update_user_state(query.from_user.id, admin_search_user=True)
        await query.edit_message_text("🔎 Entrez un user_id ou un partner_code à rechercher:")

    async def admin_export_users(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, first_name, is_seller, is_partner, partner_code, registration_date
                FROM users ORDER BY registration_date DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            csv_lines = ["user_id,username,first_name,is_seller,is_partner,partner_code,registration_date"]
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
        self.update_user_state(query.from_user.id, admin_search_product=True)
        await query.edit_message_text("🔎 Entrez un product_id exact à rechercher:")

    async def admin_suspend_product(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        self.update_user_state(query.from_user.id, admin_suspend_product=True)
        await query.edit_message_text("⛔ Entrez un product_id à suspendre:")

    # access_account_prompt supprimé pour simplifier l'UX (remplacé par seller_dashboard/seller_login)

    async def seller_logout(self, query):
        """Déconnexion: on nettoie l'état mémoire d'authentification côté bot."""
        state = self.memory_cache.get(query.from_user.id, {})
        state.pop('seller_logged_in', None)
        self.memory_cache[query.from_user.id] = state
        await query.answer("Déconnecté.")
        await self.back_to_main(query)

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
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users
                SET is_seller = FALSE, seller_name = NULL, seller_bio = NULL, seller_solana_address = NULL
                WHERE user_id = ?
            ''', (query.from_user.id,))
            conn.commit()
            conn.close()
            await query.edit_message_text("✅ Compte vendeur supprimé.")
        except Exception as e:
            logger.error(f"Erreur suppression vendeur: {e}")
            await query.edit_message_text("❌ Erreur suppression compte vendeur.")

def main():
    """Fonction principale"""
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN manquant dans .env")
        return

    # Démarrer le serveur IPN FastAPI en arrière-plan pour la détection auto
    def run_ipn_server():
        try:
            import uvicorn
            from app.integrations import ipn_server
            uvicorn.run(
                app=ipn_server.app,
                host=core_settings.IPN_HOST,
                port=core_settings.IPN_PORT,
                log_level="info",
            )
        except Exception as e:
            logger.error(f"IPN server failed to start: {e}")

    threading.Thread(target=run_ipn_server, daemon=True).start()

    # Créer l'application via app builder
    from app.integrations.telegram.app_builder import build_application
    bot = MarketplaceBot()
    application = build_application(bot)

    logger.info("🚀 Démarrage du TechBot Marketplace COMPLET...")
    logger.info(f"📱 Bot: @{TOKEN.split(':')[0] if TOKEN else 'TOKEN_MISSING'}")
    logger.info("✅ FONCTIONNALITÉS ACTIVÉES :")
    logger.info("   🏪 Marketplace multi-vendeurs")
    logger.info("   🔐 Authentification BIP-39 seed phrase")
    logger.info("   💰 Wallets crypto intégrés (8 devises)")
    logger.info("   🎁 Système parrainage restructuré")
    logger.info("   💳 Paiements NOWPayments + wallet")
    logger.info("   📁 Upload/download formations")
    logger.info("   📊 Analytics vendeurs complets")
    logger.info("   🎫 Support tickets intégré")
    logger.info("   👑 Panel admin marketplace")

    # Démarrer le bot
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
