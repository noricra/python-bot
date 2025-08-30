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

    def get_user_state(self, user_id: int) -> dict:
        return self.memory_cache.setdefault(user_id, {})

    def update_user_state(self, user_id: int, **kwargs) -> None:
        state = self.memory_cache.setdefault(user_id, {})
        state.update(kwargs)
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

                    -- Système de récupération
                    recovery_email TEXT,
                    recovery_code_hash TEXT,

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

        # Table codes de parrainage par défaut
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS default_referral_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    usage_count INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur création table default_referral_codes: {e}")
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

        # Créer quelques codes par défaut si la table est vide
        cursor.execute('SELECT COUNT(*) FROM default_referral_codes')
        if cursor.fetchone()[0] == 0:
            default_codes = [
                'BRF2025', 'CRYPTO57', 'BITREF', 'PROFIT42', 'MONEY57',
                'GAIN420'
            ]
            for code in default_codes:
                try:
                    cursor.execute(
                        'INSERT INTO default_referral_codes (code) VALUES (?)',
                        (code, ))
                    conn.commit()
                except sqlite3.Error as e:
                    logger.error(f"Erreur insertion code {code}: {e}")
                    conn.rollback()

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
        """Crée un compte vendeur avec email + code de récupération"""
        try:
            # Valider adresse Solana
            if not validate_solana_address(solana_address):
                return {'success': False, 'error': 'Adresse Solana invalide'}

            # Générer code de récupération 6 chiffres
            recovery_code = f"{random.randint(100000, 999999)}"

            # Hash du code (ne jamais stocker en clair)
            code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()

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
                        recovery_code_hash = ?
                    WHERE user_id = ?
                ''', (seller_name, seller_bio, solana_address, recovery_email, code_hash, user_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    conn.close()

                    return {
                        'success': True,
                        'recovery_code': recovery_code
                    }
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
        """Récupère les codes de parrainage disponibles (via ReferralService)"""
        from app.services.referral_service import ReferralService
        return ReferralService(self.db_path).list_all_codes()

    def validate_referral_code(self, code: str) -> bool:
        """Valide un code de parrainage"""
        available_codes = self.get_available_referral_codes()
        return code in available_codes

    def create_partner_code(self, user_id: int) -> Optional[str]:
        """Crée un code partenaire unique (via ReferralService)"""
        from app.services.referral_service import ReferralService
        for _ in range(10):
            partner_code = f"REF{user_id % 1000}{random.randint(100, 999)}"
            if ReferralService(self.db_path).set_partner_code_for_user(user_id, partner_code):
                return partner_code
        return None

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

        welcome_text = """🏪 **TECHBOT MARKETPLACE**
*La première marketplace crypto pour formations*

🎯 **Découvrez des formations premium**
📚 **Vendez vos connaissances**  
💰 **Wallet crypto intégré**

Choisissez une option pour commencer :"""

        keyboard = main_menu_keyboard()

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
            elif query.data == 'marketplace_stats':
                await self.marketplace_stats(query, lang)
            elif query.data == 'support_menu':
                await self.show_support_menu(query, lang)
            elif query.data == 'back_main':
                await self.back_to_main(query)
            elif query.data.startswith('lang_'):
                await self.change_language(query, query.data[5:])

            # Accès compte (unifié)
            # 'Accéder à mon compte' retiré pour simplifier l'UX (doublon du dashboard)
            elif query.data == 'seller_login':
                # Démarrer explicitement le flux de connexion (email puis code)
                self.update_user_state(user_id, login_wait_email=True)
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
            elif query.data == 'become_partner':
                await self.become_partner(query, lang)

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
                self.update_user_state(user_id, editing_settings=True, step='edit_name')
                await query.edit_message_text("Entrez le nouveau nom vendeur:")
            elif query.data == 'edit_seller_bio':
                self.update_user_state(user_id, editing_settings=True, step='edit_bio')
                await query.edit_message_text("Entrez la nouvelle biographie:")
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
                await query.edit_message_text(f"Édition produit `{product_id}`:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            elif query.data.startswith('edit_field_title_'):
                product_id = query.data.split('edit_field_title_')[-1]
                self.update_user_state(user_id, editing_product=True, product_id=product_id, step='edit_title_input')
                await query.edit_message_text("Entrez le nouveau titre:")
            elif query.data.startswith('edit_field_price_'):
                product_id = query.data.split('edit_field_price_')[-1]
                self.update_user_state(user_id, editing_product=True, product_id=product_id, step='edit_price_input')
                await query.edit_message_text("Entrez le nouveau prix (EUR):")
            elif query.data.startswith('edit_field_toggle_'):
                product_id = query.data.split('edit_field_toggle_')[-1]
                try:
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT status FROM products WHERE product_id = ? AND seller_user_id = ?', (product_id, user_id))
                    row = cursor.fetchone()
                    if not row:
                        conn.close()
                        await query.edit_message_text("❌ Produit introuvable.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='my_products')]]))
                    else:
                        new_status = 'inactive' if row[0] == 'active' else 'active'
                        cursor.execute('UPDATE products SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (new_status, product_id, user_id))
                        conn.commit()
                        conn.close()
                        await self.show_my_products(query, 'fr')
                except Exception as e:
                    logger.error(f"Erreur toggle statut produit: {e}")
                    await query.edit_message_text("❌ Erreur mise à jour statut.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='my_products')]]))
            elif query.data.startswith('delete_product_'):
                product_id = query.data.split('delete_product_')[-1]
                self.update_user_state(user_id, confirm_delete_product=product_id)
                keyboard = [
                    [InlineKeyboardButton("✅ Confirmer suppression", callback_data=f'confirm_delete_{product_id}')],
                    [InlineKeyboardButton("❌ Annuler", callback_data='my_products')],
                    [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
                ]
                await query.edit_message_text(f"Confirmer la suppression du produit `{product_id}` ?", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
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
                    await query.edit_message_text("❌ Erreur lors de la suppression.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Retour", callback_data='my_products')]]))
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
        keyboard = buy_menu_keyboard()

        buy_text = """🛒 **ACHETER UNE FORMATION**

Plusieurs façons de découvrir nos formations :

🔍 **Recherche directe** - Si vous avez un ID produit
📂 **Par catégories** - Explorez par domaine
🔥 **Tendances** - Les plus populaires
🆕 **Nouveautés** - Dernières publications

💰 **Paiement crypto sécurisé** avec votre wallet intégré"""

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
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Retour",
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
            products_text = f"""📂 **{category_name.upper()}**

Aucune formation disponible dans cette catégorie pour le moment.

Soyez le premier à publier dans ce domaine !"""

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

        keyboard = [[
            InlineKeyboardButton("🛒 Acheter maintenant",
                                 callback_data=f'buy_product_{product_id}')
        ],
                    [
                        InlineKeyboardButton("📂 Autres produits",
                                             callback_data='browse_categories')
                    ],
                    [
                        InlineKeyboardButton("🔙 Retour",
                                             callback_data='buy_menu')
                    ]]

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
                InlineKeyboardButton("🚀 Devenir partenaire (10% commission!)",
                                     callback_data='become_partner')
            ],
            [
                InlineKeyboardButton("🔙 Retour",
                                     callback_data=f'product_{product_id}')
            ]
        ]

        referral_text = """🎯 **CODE DE PARRAINAGE OBLIGATOIRE**

⚠️ **IMPORTANT :** Un code de parrainage est requis pour acheter.

💡 **3 OPTIONS DISPONIBLES :**

1️⃣ **Vous avez un code ?** Saisissez-le !

2️⃣ **Pas de code ?** Choisissez-en un gratuitement !

3️⃣ **MEILLEURE OPTION :** Devenez partenaire !
   • ✅ Gagnez 10% sur chaque vente
   • ✅ Votre propre code de parrainage
   • ✅ Dashboard vendeur complet"""

        await query.edit_message_text(
            referral_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def enter_referral_manual(self, query, lang):
        """Demander la saisie manuelle du code"""
        self.memory_cache[query.from_user.id]['waiting_for_referral'] = True

        await query.edit_message_text(
            "✍️ **Veuillez saisir votre code de parrainage :**\n\nTapez le code exactement comme vous l'avez reçu.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Retour",
                                       callback_data='buy_menu')]]))

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

                keyboard = [[
                    InlineKeyboardButton("📥 Télécharger maintenant", 
                                    callback_data=f'download_product_{order[3]}')
                ], [
                    InlineKeyboardButton("🏠 Menu principal", callback_data='back_main')
                ]]

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
                (f"❌ **Invalid code:** `{referral_code}`\n\nPlease try again with a valid code." if lang == 'en' else f"❌ **Code invalide :** `{referral_code}`\n\nVeuillez réessayer avec un code valide."),
                reply_markup=InlineKeyboardMarkup([[ 
                    InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour", callback_data='buy_menu')
                ]]),
                parse_mode='Markdown')
            return

        # Stocker le code validé
        user_cache = self.memory_cache.get(query.from_user.id, {})
        user_cache['validated_referral'] = referral_code
        user_cache['lang'] = lang
        self.memory_cache[query.from_user.id] = user_cache

        await query.edit_message_text(
            (f"✅ **Code validated:** `{referral_code}`\n\nLet's proceed to payment!" if lang == 'en' else f"✅ **Code validé :** `{referral_code}`\n\nProcédons au paiement !"),
            reply_markup=InlineKeyboardMarkup([[ 
                InlineKeyboardButton("💳 Continue to payment" if lang == 'en' else "💳 Continuer vers le paiement",
                                     callback_data='proceed_to_payment'),
                InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour", callback_data='buy_menu')
            ]]),
            parse_mode='Markdown')

    async def become_partner(self, query, lang):
        """Inscription partenaire"""
        user_id = query.from_user.id
        user_data = self.get_user(user_id)

        if user_data and user_data['is_partner']:
            await query.edit_message_text(
                "✅ Vous êtes déjà partenaire !",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 Mon dashboard",
                                         callback_data='seller_dashboard')
                ]]))
            return

        partner_code = self.create_partner_code(user_id)

        if partner_code:
            # Valider automatiquement son propre code
            user_cache = self.memory_cache.get(user_id, {})
            user_cache['validated_referral'] = partner_code
            user_cache['lang'] = lang
            user_cache['self_referral'] = True
            self.memory_cache[user_id] = user_cache

            welcome_text = f"""🎊 **BIENVENUE DANS L'ÉQUIPE !**

✅ Votre compte partenaire est activé !

🎯 **VOTRE CODE UNIQUE :** `{partner_code}`

💰 **Avantages partenaire :**
• Gagnez 10% sur chaque vente
• Utilisez VOTRE code pour vos achats
• Dashboard vendeur complet
• Support prioritaire"""

            keyboard = [[
                InlineKeyboardButton("💳 Continuer l'achat",
                                     callback_data='proceed_to_payment')
            ],
                        [
                            InlineKeyboardButton(
                                "📊 Mon dashboard",
                                callback_data='seller_dashboard')
                        ]]

            await query.edit_message_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        else:
            await query.edit_message_text(
                "❌ Erreur lors de la création du compte partenaire.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
                ]]))

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

        crypto_text = f"""💳 **CHOISIR VOTRE CRYPTO**

📦 **Produit :** {product['title']}
💰 **Prix :** {product['price_eur']}€
🎯 **Code parrainage :** `{user_cache['validated_referral']}`

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
        partner_commission = product_price_eur * PARTNER_COMMISSION_RATE
        seller_revenue = product_price_eur - platform_commission - partner_commission

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
                      payment_data.get('pay_address', ''), referral_code))
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                logger.error(f"Erreur création commande: {e}")
                conn.close()
                return

            # Nettoyer le cache de l'achat uniquement (conserver l'état global/login)
            if user_id in self.memory_cache:
                user_cache = self.memory_cache.get(user_id, {})
                for k in ['buying_product_id', 'validated_referral', 'self_referral']:
                    if k in user_cache:
                        user_cache.pop(k, None)
                self.memory_cache[user_id] = user_cache

            crypto_amount = payment_data.get('pay_amount', 0)
            payment_address = payment_data.get('pay_address', '')
            network_hint = infer_network_from_address(payment_address)

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
                InlineKeyboardButton("🔄 Vérifier paiement",
                                     callback_data=f'check_payment_{order_id}')
            ], [
                InlineKeyboardButton("💬 Support", callback_data='support_menu')
            ], [
                InlineKeyboardButton("🏠 Accueil", callback_data='back_main')
            ]]

            # Générer et envoyer un QR code pour l'adresse de paiement
            try:
                qr_img = qrcode.make(payment_address)
                bio = BytesIO()
                qr_img.save(bio, format='PNG')
                bio.seek(0)
                caption = payment_text
                await query.message.reply_photo(photo=bio, caption=caption, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception as e:
                logger.warning(f"QR code generation failed: {e}")
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
                await query.edit_message_text(
                    f"⏳ **PAIEMENT EN COURS**\n\n🔍 **Statut :** {status}\n\n💡 Les confirmations peuvent prendre 5-30 min",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                        "🔄 Rafraîchir", callback_data=f'check_payment_{order_id}')]]))
        else:
            conn.close()
            await query.edit_message_text(
                "❌ Erreur de vérification. Réessayez.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    "🔄 Réessayer", callback_data=f'check_payment_{order_id}')]]))

    async def sell_menu(self, query, lang):
        """Menu vendeur"""
        user_data = self.get_user(query.from_user.id)

        if user_data and user_data['is_seller']:
            await self.seller_dashboard(query, lang)
            return

        keyboard = sell_menu_keyboard()

        sell_text = """📚 **VENDRE VOS FORMATIONS**

🎯 **Valorisez votre expertise**

💰 **Avantages vendeur :**
• 95% des revenus pour vous (5% commission plateforme)
• Paiements automatiques en crypto
• Wallet intégré sécurisé
• Gestion complète de vos produits
• Support marketing inclus

🔐 **Sécurité**
• Récupération via email + code
• Adresse Solana de paiement à votre nom
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

Pour créer votre compte vendeur sécurisé, nous avons besoin de quelques informations.

👤 **Étape 1/2 : Nom public**

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
            # Proposer directement la connexion simple (email + code)
            keyboard = [
                [InlineKeyboardButton("🔐 Se connecter", callback_data='seller_login')],
                [InlineKeyboardButton("🚀 Créer un compte vendeur", callback_data='create_seller')],
                [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]
            ]
            await query.edit_message_text("🔑 Connexion vendeur\n\nConnectez-vous avec votre email et votre code de récupération.", reply_markup=InlineKeyboardMarkup(keyboard))
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

💸 **Payouts / Adresse :** {'✅ Configurée' if user_data['seller_solana_address'] else '❌ À configurer'}"""

        keyboard = [[
            InlineKeyboardButton("➕ Ajouter un produit",
                                 callback_data='add_product')
        ], [
            InlineKeyboardButton("📦 Mes produits", callback_data='my_products')
        ], [InlineKeyboardButton("💸 Payouts / Adresse", callback_data='my_wallet')],
                    [
                        InlineKeyboardButton("📊 Analytics détaillées",
                                             callback_data='seller_analytics')
                    ],
                    [
                        InlineKeyboardButton("⚙️ Paramètres",
                                             callback_data='seller_settings')
                    ],
                    [
                        InlineKeyboardButton("🏠 Accueil",
                                             callback_data='back_main')
                    ]]

        await query.edit_message_text(
            dashboard_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def add_product_prompt(self, query, lang):
        """Demande les informations pour ajouter un produit"""
        user_data = self.get_user(query.from_user.id)

        if not user_data or not user_data['is_seller'] or not self.is_seller_logged_in(query.from_user.id):
            await query.edit_message_text(
                "❌ Connectez-vous d'abord (email + code)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
            )
            return

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
            await query.edit_message_text(
                "❌ Connectez-vous d'abord (email + code)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
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
            await query.edit_message_text(
                "❌ Connectez-vous d'abord (email + code)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Accueil", callback_data='back_main')]])
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
                    self.memory_cache.pop(user_id, None)
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
                    self.memory_cache.pop(user_id, None)
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
            await update.message.reply_text(
                f"❌ **Format ID invalide :** `{product_id}`\n\n💡 **Format attendu :** `TBF-2501-ABC123`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data='buy_menu')
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

            from app.services.support_service import SupportService
            ticket_id = SupportService(self.db_path).create_ticket(user_id, subject, content)
            if ticket_id:
                self.memory_cache.pop(user_id, None)
                await update.message.reply_text(
                    f"🎫 Ticket créé: {ticket_id}\nNotre équipe vous répondra bientôt.")
            else:
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
            # Si la langue est déjà la même, éviter l'erreur 'Message is not modified'
            current = self.get_user(user_id)
            current_lang = (current and current.get('language_code')) or 'fr'
            if current_lang == lang:
                await query.answer("✅ Language already set" if lang == 'en' else "✅ Langue déjà définie")
                await self.back_to_main(query, force_new_message=True)
                return

            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET language_code = ? WHERE user_id = ?', (lang, user_id))
            conn.commit()
            conn.close()

            await query.answer(f"✅ Language changed to {lang}")
            # Toujours renvoyer un nouveau message pour éviter l'erreur 'Message is not modified'
            await self.back_to_main(query, force_new_message=True)

        except Exception as e:
            logger.error(f"Erreur changement langue: {e}")
            # Gestion spécifique du cas "Message is not modified"
            if 'Message is not modified' in str(e):
                try:
                    await self.back_to_main(query, force_new_message=True)
                    return
                except Exception:
                    pass
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

    async def back_to_main(self, query, force_new_message: bool = False):
        """Menu principal avec récupération"""
        user_id = query.from_user.id
        user_data = self.get_user(user_id)
        lang = user_data['language_code'] if user_data else 'fr'
        is_seller = user_data and user_data['is_seller']

        keyboard = [
            [InlineKeyboardButton("🛒 Acheter une formation", callback_data='buy_menu')],
            [InlineKeyboardButton("📚 Vendre vos formations", callback_data='sell_menu')]
        ]

        # Accès rapide espace vendeur si déjà vendeur
        if is_seller:
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

        welcome_text = self.get_text('welcome', lang)
        if force_new_message:
            await query.message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
            return
        try:
            await query.edit_message_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown')
        except Exception as e:
            if 'Message is not modified' in str(e):
                await query.message.reply_text(
                    welcome_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown')
            else:
                await query.message.reply_text(
                    welcome_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown')

    async def account_recovery_menu(self, query, lang):
        """Menu de récupération de compte"""
        await query.edit_message_text("""🔐 **RÉCUPÉRATION COMPTE VENDEUR**

    Si vous avez perdu l'accès à votre compte Telegram :

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
            [InlineKeyboardButton("Create a ticket" if lang == 'en' else "Créer un ticket", callback_data='create_ticket')],
            [InlineKeyboardButton("My tickets" if lang == 'en' else "Mes tickets", callback_data='my_tickets')],
            [InlineKeyboardButton("🏠 Home" if lang == 'en' else "🏠 Accueil", callback_data='back_main')]
        ]

        support_text = ("Support & assistance\n\nHow can we help you?" if lang == 'en' else """Assistance et support

Comment pouvons-nous vous aider ?""")

        await query.edit_message_text(
            support_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown')

    async def show_faq(self, query, lang):
        """Affiche la FAQ"""
        faq_text = ("""**FAQ**

Q: How to buy a course?
A: Browse categories or search by ID.

Q: How to sell a course?
A: Become a seller and add your products.

Q: How to recover my account?
A: Use the recovery email.""" if lang == 'en' else """**FAQ**

Q: Comment acheter une formation ?
R: Parcourez les catégories ou recherchez par ID.

Q: Comment vendre une formation ?
R: Devenez vendeur et ajoutez vos produits.

Q: Comment récupérer mon compte ?
R: Utilisez l'email de récupération.""")

        keyboard = [[InlineKeyboardButton("Back" if lang == 'en' else "Retour", callback_data='support_menu')]]

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
            ("🆘 New ticket\n\nEnter a subject for your request:" if lang == 'en' else "🆘 Nouveau ticket\n\nEntrez un sujet pour votre demande:"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 Retour", callback_data='support_menu')]])
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
            await query.edit_message_text("🎫 No tickets." if lang == 'en' else "🎫 Aucun ticket.")
            return

        text = ("🎫 Your tickets:\n\n" if lang == 'en' else "🎫 Vos tickets:\n\n")
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
                await query.edit_message_text("❌ Access denied. Please buy this product first." if lang == 'en' else "❌ Accès refusé. Achetez d'abord ce produit.")
                return
            cursor.execute('SELECT main_file_path FROM products WHERE product_id = ?', (product_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                await query.edit_message_text("❌ File not found." if lang == 'en' else "❌ Fichier introuvable.")
                return
            file_path = row[0]
            conn.close()

            if not os.path.exists(file_path):
                await query.edit_message_text("❌ Missing file on server." if lang == 'en' else "❌ Fichier manquant sur le serveur.")
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
            await query.edit_message_text("❌ Download error." if lang == 'en' else "❌ Erreur lors du téléchargement.")

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
            await query.edit_message_text("❌ Error fetching your library." if lang == 'en' else "❌ Erreur lors de la récupération de votre bibliothèque.")
            return

        if not rows:
            await query.edit_message_text("📚 Your library is empty." if lang == 'en' else "📚 Votre bibliothèque est vide.")
            return

        text = ("📚 Your purchases:\n\n" if lang == 'en' else "📚 Vos achats:\n\n")
        keyboard = []
        # Optional: display USD if lang == 'en'
        usd_rate = None
        if lang == 'en':
            usd_rate = await asyncio.to_thread(self.get_exchange_rate)
        for product_id, title, price in rows[:10]:
            if lang == 'en' and usd_rate:
                text += f"• {title} — {price * usd_rate:.2f}$\n"
            else:
                text += f"• {title} — {price}€\n"
            keyboard.append([InlineKeyboardButton("📥 Download" if lang == 'en' else "📥 Télécharger", callback_data=f'download_product_{product_id}')])

        keyboard.append([InlineKeyboardButton("🏠 Home" if lang == 'en' else "🏠 Accueil", callback_data='back_main')])
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
        self.update_user_state(query.from_user.id, editing_settings=True, step='menu')
        keyboard = [
            [InlineKeyboardButton("✏️ Modifier nom", callback_data='edit_seller_name')],
            [InlineKeyboardButton("📝 Modifier bio", callback_data='edit_seller_bio')],
            [InlineKeyboardButton("💸 Payouts / Adresse", callback_data='my_wallet')],
            [InlineKeyboardButton("🚪 Se déconnecter", callback_data='seller_logout')],
            [InlineKeyboardButton("🗑️ Supprimer le compte vendeur", callback_data='delete_seller')],
            [InlineKeyboardButton("🏠 Accueil", callback_data='back_main')],
        ]
        await query.edit_message_text("Paramètres vendeur:", reply_markup=InlineKeyboardMarkup(keyboard))

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
        self.memory_cache[query.from_user.id] = {'admin_search_user': True}
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
        self.memory_cache[query.from_user.id] = {'admin_search_product': True}
        await query.edit_message_text("🔎 Entrez un product_id exact à rechercher:")

    async def admin_suspend_product(self, query):
        if query.from_user.id != ADMIN_USER_ID:
            return
        self.memory_cache[query.from_user.id] = {'admin_suspend_product': True}
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
