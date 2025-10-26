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

from telegram import Update
from telegram.ext import ContextTypes
import httpx

# Configuration globale de httpx pour plus de tolérance

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
from app.core.validation import validate_email, validate_solana_address
from app.core.state_manager import StateManager
from app.core.database_init import DatabaseInitService
from app.services.seller_service import SellerService
from app.integrations.telegram.callback_router import CallbackRouter
from app.integrations.telegram.keyboards import main_menu_keyboard, buy_menu_keyboard, sell_menu_keyboard
from app.integrations.telegram.handlers.sell_handlers import SellHandlers
from app.integrations.telegram.handlers.admin_handlers import AdminHandlers
from app.integrations.telegram.handlers.auth_handlers import AuthHandlers
from app.integrations.telegram.handlers.buy_handlers import BuyHandlers
from app.integrations.telegram.handlers.support_handlers import SupportHandlers
from app.integrations.telegram.handlers.core_handlers import CoreHandlers
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
SMTP_EMAIL = core_settings.SMTP_USERNAME
SMTP_PASSWORD = core_settings.SMTP_PASSWORD

# Configuration marketplace
MAX_FILE_SIZE_MB = core_settings.MAX_FILE_SIZE_MB
SUPPORTED_FILE_TYPES = core_settings.SUPPORTED_FILE_TYPES

# Configuration crypto
MARKETPLACE_CONFIG = core_settings.MARKETPLACE_CONFIG

# Platform commission (fixed 5%)
PLATFORM_COMMISSION_RATE = core_settings.PLATFORM_COMMISSION_RATE

# Configuration logging
logger = logging.getLogger(__name__)


# SUPPRIMER ENTIÈREMENT la classe CryptoWalletManager
# REMPLACER PAR ces fonctions simples :


class MarketplaceBot:

    def __init__(self):
        logger.info("🚀 Initialisation MarketplaceBot optimisé...")

        self.db_path = core_settings.DATABASE_PATH
        # Database initialization handled by DatabaseInitService
        db_init_service = DatabaseInitService(self.db_path)
        db_init_service.init_all_tables()

        # State Manager centralisé (remplace memory_cache)
        self.state_manager = StateManager()

        # Seller sessions en mémoire
        self.seller_sessions = set()

        # Inject repositories and services directly
        from app.domain.repositories import UserRepository
        from app.domain.repositories.product_repo import ProductRepository
        from app.domain.repositories.order_repo import OrderRepository
        from app.domain.repositories.ticket_repo import SupportTicketRepository
        from app.domain.repositories.payout_repo import PayoutRepository
        from app.domain.repositories.review_repo import ReviewRepository  # V2: Added for reviews
        from app.services.payment_service import PaymentService
        from app.services.payout_service import PayoutService
        from app.services.support_service import SupportService

        self.user_repo = UserRepository(self.db_path)
        self.product_repo = ProductRepository(self.db_path)
        self.order_repo = OrderRepository(self.db_path)
        self.ticket_repo = SupportTicketRepository(self.db_path)
        self.payout_repo = PayoutRepository(self.db_path)
        self.review_repo = ReviewRepository(self.db_path)  # V2: Initialize review repository
        self.payment_service = PaymentService()
        self.payout_service = PayoutService(self.db_path)
        self.support_service = SupportService(self.ticket_repo)
        self.seller_service = SellerService(self.db_path)

        # Email service
        from app.core.email_service import EmailService
        self.email_service = EmailService()

        # Initialize handlers with dependency injection
        self.core_handlers = CoreHandlers(self.user_repo)
        self.sell_handlers = SellHandlers(self.user_repo, self.product_repo, self.payment_service)
        self.admin_handlers = AdminHandlers(self.user_repo, self.product_repo, self.order_repo, self.payout_service)
        self.auth_handlers = AuthHandlers(self.user_repo, self.email_service)
        self.buy_handlers = BuyHandlers(self.product_repo, self.order_repo, self.payment_service, self.review_repo)  # V2: Pass review_repo
        self.support_handlers = SupportHandlers(self.user_repo, self.product_repo, self.support_service)

        # Import and initialize library handlers
        from app.integrations.telegram.handlers.library_handlers import LibraryHandlers
        self.library_handlers = LibraryHandlers(self.product_repo, self.order_repo, self.user_repo)

        # Initialize analytics handlers (AI-powered)
        from app.integrations.telegram.handlers.analytics_handlers import AnalyticsHandlers
        self.analytics_handlers = AnalyticsHandlers()

        # Router centralisé pour callbacks
        self.callback_router = CallbackRouter(self)

        logger.info("✅ MarketplaceBot optimisé initialisé avec succès")

    def get_db_connection(self):
        """Retourne une connexion à la base de données"""
        return get_sqlite_connection(self.db_path)

    def escape_markdown(self, text: str) -> str:
        """Escape special markdown characters"""
        from app.core.utils import escape_markdown
        return escape_markdown(text)

    def get_product_by_id(self, product_id: str):
        """Get product by ID"""
        return self.product_repo.get_product_by_id(product_id)

    def create_ticket(self, user_id: int, subject: str, message: str):
        """Create support ticket"""
        return self.support_service.create_ticket(user_id, subject, message)

    async def save_uploaded_file(self, file_info, filename: str) -> str:
        """Save uploaded file"""
        from app.core.file_utils import save_uploaded_file
        return await save_uploaded_file(file_info, filename)

    def create_product(self, product_data: dict) -> str:
        """Create product"""
        return self.product_repo.create_product(product_data)

    def is_seller_logged_in(self, user_id: int) -> bool:
        """Vérifie si un vendeur est connecté"""
        return user_id in self.seller_sessions

    def login_seller(self, user_id: int):
        """Connecte un vendeur"""
        self.seller_sessions.add(user_id)
        logger.debug(f"Seller {user_id} logged in")

    def logout_seller(self, user_id: int):
        """Déconnecte un vendeur"""
        self.seller_sessions.discard(user_id)
        logger.debug(f"Seller {user_id} logged out")

    def update_user_mapping(self, from_user_id: int, to_user_id: int, account_name: str = None):
        """
        Update user mapping for multi-account support

        Comportement:
        - Si mapping existe déjà (telegram_id, seller_user_id) → met à jour last_login
        - Sinon → crée nouveau mapping
        - Désactive tous les autres comptes du même telegram_id
        - Active le compte mappé
        """
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()

            # 1. Désactiver tous les comptes de ce telegram_id
            cursor.execute('''
                UPDATE telegram_mappings
                SET is_active = 0
                WHERE telegram_id = ?
            ''', (from_user_id,))

            # 2. Insérer ou activer le compte
            cursor.execute('''
                INSERT INTO telegram_mappings (telegram_id, seller_user_id, is_active, account_name, last_login)
                VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_id, seller_user_id) DO UPDATE SET
                    is_active = 1,
                    account_name = COALESCE(excluded.account_name, account_name),
                    last_login = CURRENT_TIMESTAMP
            ''', (from_user_id, to_user_id, account_name))

            conn.commit()
            conn.close()

            logger.info(f"✅ Activated account: Telegram {from_user_id} → Seller {to_user_id}")
        except Exception as e:
            logger.error(f"❌ Error updating user mapping: {e}")

    def get_seller_id(self, telegram_id: int) -> int:
        """
        Get the ACTIVE seller user_id for a telegram_id (multi-account support)

        Retourne:
        - Le seller_user_id du compte actif (is_active=1) si existe
        - Le premier compte si aucun actif (backward compatibility)
        - telegram_id si aucun mapping (nouveau user)
        """
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()

            # Try to get active account first
            cursor.execute('''
                SELECT seller_user_id FROM telegram_mappings
                WHERE telegram_id = ? AND is_active = 1
                ORDER BY last_login DESC
                LIMIT 1
            ''', (telegram_id,))
            result = cursor.fetchone()

            if result:
                conn.close()
                return result[0]  # Return active account

            # No active account, get the most recent one (backward compatibility)
            cursor.execute('''
                SELECT seller_user_id FROM telegram_mappings
                WHERE telegram_id = ?
                ORDER BY last_login DESC
                LIMIT 1
            ''', (telegram_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return result[0]  # Return most recent account
            else:
                return telegram_id  # No mapping, use telegram_id directly

        except Exception as e:
            logger.error(f"❌ Error getting seller_id for telegram_id {telegram_id}: {e}")
            return telegram_id  # Fallback to telegram_id

    def get_user_accounts(self, telegram_id: int) -> list:
        """
        Liste tous les comptes vendeur associés à un telegram_id

        Retourne: List[dict] avec:
        - seller_user_id
        - is_active (1 ou 0)
        - account_name
        - seller_name (depuis users table)
        - created_at
        - last_login
        """
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT
                    tm.seller_user_id,
                    tm.is_active,
                    tm.account_name,
                    u.seller_name,
                    u.first_name,
                    tm.created_at,
                    tm.last_login
                FROM telegram_mappings tm
                JOIN users u ON tm.seller_user_id = u.user_id
                WHERE tm.telegram_id = ?
                ORDER BY tm.is_active DESC, tm.last_login DESC
            ''', (telegram_id,))

            accounts = []
            for row in cursor.fetchall():
                accounts.append({
                    'seller_user_id': row[0],
                    'is_active': bool(row[1]),
                    'account_name': row[2] or row[3] or row[4] or f"Compte {row[0]}",  # Fallback name
                    'created_at': row[5],
                    'last_login': row[6]
                })

            conn.close()
            return accounts

        except Exception as e:
            logger.error(f"❌ Error getting user accounts: {e}")
            return []

    def switch_account(self, telegram_id: int, target_seller_id: int) -> bool:
        """
        Switch active account for a telegram_id

        Returns: True si succès, False si compte n'existe pas
        """
        try:
            conn = get_sqlite_connection(self.db_path)
            cursor = conn.cursor()

            # Vérifier que le compte existe pour ce telegram_id
            cursor.execute('''
                SELECT 1 FROM telegram_mappings
                WHERE telegram_id = ? AND seller_user_id = ?
            ''', (telegram_id, target_seller_id))

            if not cursor.fetchone():
                conn.close()
                logger.warning(f"⚠️ Account {target_seller_id} not found for telegram {telegram_id}")
                return False

            # Désactiver tous les comptes
            cursor.execute('''
                UPDATE telegram_mappings
                SET is_active = 0
                WHERE telegram_id = ?
            ''', (telegram_id,))

            # Activer le compte cible
            cursor.execute('''
                UPDATE telegram_mappings
                SET is_active = 1, last_login = CURRENT_TIMESTAMP
                WHERE telegram_id = ? AND seller_user_id = ?
            ''', (telegram_id, target_seller_id))

            conn.commit()
            conn.close()

            logger.info(f"✅ Switched to account {target_seller_id} for telegram {telegram_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error switching account: {e}")
            return False

    def reset_user_state_preserve_login(self, user_id: int) -> None:
        """Nettoie l'état utilisateur tout en préservant la langue"""
        current = self.state_manager.get_state(user_id)
        lang = current.get('lang')
        keep_set = {'lang'} if lang else set()
        self.state_manager.reset_state(user_id, keep_set)


    def get_user_language(self, user_id: int) -> str:
        """Get user language from database or default to 'fr'"""
        from app.core.user_utils import get_user_language
        return get_user_language(user_id, self.user_repo, self.state_manager.get_state(user_id))


    def reset_conflicting_states(self, user_id: int, keep: set = None) -> None:
        """Remet à zéro les états conflictuels"""
        self.state_manager.reset_conflicting_states(user_id, keep)

    def get_user_state(self, user_id: int) -> dict:
        """Récupère l'état utilisateur"""
        return self.state_manager.get_state(user_id)

    def update_user_state(self, user_id: int, **kwargs) -> None:
        """Met à jour l'état utilisateur"""
        self.state_manager.update_state(user_id, **kwargs)

    def reset_user_state(self, user_id: int, keep: set = None) -> None:
        """Remet à zéro l'état utilisateur"""
        self.state_manager.reset_state(user_id, keep)





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
            payout_id = self.payout_service.create_payout(
                seller_user_id,
                [order_id],
                seller_amount_sol
            )

            conn.close()
            return payout_id is not None

        except Exception as e:
            logger.error(f"Erreur auto payout: {e}")
            return False


    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler principal des callbacks - ROUTAGE CENTRALISÉ"""
        query = update.callback_query
        await query.answer()

        try:
            # Router centralisé gère tous les callbacks
            routed = await self.callback_router.route(query)

            if not routed:
                # Fallback pour callbacks non routés
                logger.warning(f"Callback non routé: {query.data}")
                await self._handle_unknown_callback(query)

        except Exception as e:
            logger.error(f"Erreur button_handler: {e}")
            await self._handle_callback_error(query, e)

    async def _handle_unknown_callback(self, query):
        """Gère les callbacks inconnus"""
        lang = self.get_user_language(query.from_user.id)
        await query.edit_message_text(
            i18n(lang, 'err_temp'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')
            ]]))

    async def _handle_callback_error(self, query, error):
        """Gère les erreurs de callback"""
        lang = self.get_user_language(query.from_user.id)
        logger.error(f"Callback error: {error}")
        try:
            await query.edit_message_text(
                i18n(lang, 'err_temp'),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(i18n(lang, 'btn_home'), callback_data='back_main')
                ]]))
        except:
            pass


    # Toutes les autres méthodes ont été extraites vers les handlers modulaires
    async def handle_text_message(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire principal des messages texte"""
        user_id = update.effective_user.id
        message_text = update.message.text

        # S'assurer qu'un état existe pour l'utilisateur via StateManager
        # StateManager gère automatiquement les états vides

        user_state = self.state_manager.get_state(user_id)

        # === CRÉATION VENDEUR (prioritaire pour éviter la collision avec recherche) ===
        if user_state.get('creating_seller'):
            await self.sell_handlers.process_seller_creation(self, update, message_text)

        # === CONNEXION VENDEUR PAR EMAIL ===
        elif user_state.get('waiting_seller_login_email'):
            await self.sell_handlers.process_seller_login_email(self, update, message_text)

        # === RECHERCHE PRODUIT ===
        elif user_state.get('waiting_for_product_id'):
            await self.buy_handlers.process_product_search(self, update, message_text)

        # === AJOUT PRODUIT ===
        elif user_state.get('adding_product'):
            await self.sell_handlers.process_product_addition(self, update, message_text)

        # === SAISIE CODE PARRAINAGE ===
        # (Supprimé) Saisie code parrainage

        # === CRÉATION TICKET SUPPORT ===
        elif user_state.get('creating_ticket'):
            await self.process_support_ticket(update, message_text)
        elif user_state.get('waiting_reply_ticket_id'):
            await self.support_handlers.process_messaging_reply(self, update, message_text)
        elif user_state.get('waiting_admin_reply_ticket_id'):
            await self.support_handlers.process_admin_reply(self, update, message_text)

        # === RÉCUPÉRATION PAR EMAIL ===
        elif user_state.get('waiting_for_email'):
            await self.auth_handlers.process_recovery_email(self, update, message_text)

        # === RÉCUPÉRATION CODE ===
        elif user_state.get('waiting_for_recovery_code'):
            await self.auth_handlers.process_recovery_code(self, update, message_text)
        elif user_state.get('waiting_new_password'):
            await self.auth_handlers.process_set_new_password(self, update, message_text)

        # === CONNEXION (email + code fourni lors de la création) ===
        elif user_state.get('login_wait_email'):
            await self.auth_handlers.process_login_email(self, update, message_text)
        elif user_state.get('login_wait_code'):
            await self.auth_handlers.process_login_code(self, update, message_text)

        # === PARAMÈTRES VENDEUR ===
        elif user_state.get('editing_settings'):
            await self.sell_handlers.process_seller_settings(self, update, message_text)

        # === ÉCRITURE D'AVIS ===
        elif user_state.get('waiting_for_review'):
            await self.library_handlers.process_review_text(self, update, message_text)
        # === MESSAGE AU VENDEUR VIA TICKET ===
        elif user_state.get('waiting_ticket_message'):
            ticket_id = user_state.get('waiting_ticket_message')
            lang = user_state.get('lang', 'fr')
            try:
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                conn = self.get_db_connection()
                cursor = conn.cursor()

                # Add message to ticket
                cursor.execute('''
                    INSERT INTO support_messages (ticket_id, sender_user_id, sender_role, message, created_at)
                    VALUES (?, ?, 'buyer', ?, CURRENT_TIMESTAMP)
                ''', (ticket_id, user_id, message_text))

                conn.commit()
                conn.close()

                # Reset state
                self.state_manager.reset_state(user_id, keep={'lang'})

                success_text = (
                    f"✅ **Message sent!**\n\n"
                    f"Ticket: `{ticket_id}`\n\n"
                    f"The seller will be notified and can respond via the support system."
                    if lang == 'en' else
                    f"✅ **Message envoyé !**\n\n"
                    f"Ticket : `{ticket_id}`\n\n"
                    f"Le vendeur sera notifié et pourra répondre via le système de support."
                )

                await update.message.reply_text(
                    success_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📬 My Tickets" if lang == 'en' else "📬 Mes Tickets",
                            callback_data='my_tickets'
                        ),
                        InlineKeyboardButton(
                            "🏠 Home" if lang == 'en' else "🏠 Accueil",
                            callback_data='back_main'
                        )
                    ]]),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending ticket message: {e}")
                await update.message.reply_text("❌ Error" if lang == 'en' else "❌ Erreur")
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
                    state = self.state_manager.get_state(user_id)
                    for k in ['editing_product', 'product_id', 'step']:
                        state.pop(k, None)
                    # État mis à jour via StateManager (pas besoin de réassigner)
                    await update.message.reply_text("✅ Titre mis à jour.")
                except Exception as e:
                    logger.error(f"Erreur maj titre produit: {e}")
                    await update.message.reply_text("❌ Erreur mise à jour titre.")
            elif step == 'edit_price_input':
                lang = self.get_user_language(user_id)
                success = await self.sell_handlers.process_product_price_update(self, update, product_id, message_text, lang)
                if success:
                    # Nettoyer uniquement le contexte d'édition produit
                    state = self.state_manager.get_state(user_id)
                    for k in ['editing_product', 'product_id', 'step']:
                        state.pop(k, None)
                    self.state_manager.update_state(user_id, **state)
            else:
                await update.message.reply_text("💬 Choisissez l'action d'édition depuis le menu.")
        # === ADMIN RECHERCHES/SUSPENSIONS ===
        elif user_state.get('admin_search_user'):
            await self.admin_handlers.process_admin_search_user(update, message_text)
        elif user_state.get('admin_search_product'):
            await self.admin_handlers.process_admin_search_product(update, message_text)
        elif user_state.get('admin_suspend_product'):
            await self.admin_handlers.handle_product_suspend_message(self, update, user_state)
        elif user_state.get('restoring_product'):
            await self.admin_handlers.process_admin_restore_product(self, update, user_state)
        elif user_state.get('suspending_user'):
            await self.admin_handlers.process_admin_suspend_user(update, message_text)
        elif user_state.get('restoring_user'):
            await self.admin_handlers.process_admin_restore_user(update, message_text)
        # === NOUVELLE ÉDITION PRODUIT PAR CHAMP ===
        elif user_state.get('editing_product_price'):
            product_id = user_state.get('editing_product_price')
            lang = self.get_user_language(user_id)
            success = await self.sell_handlers.process_product_price_update(self, update, product_id, message_text, lang)
            if success:
                state = self.state_manager.get_state(user_id)
                state.pop('editing_product_price', None)
                self.state_manager.update_state(user_id, **state)
        elif user_state.get('editing_product_title'):
            product_id = user_state.get('editing_product_title')
            lang = self.get_user_language(user_id)
            try:
                new_title = message_text.strip()[:100]
                if len(new_title) < 3:
                    raise ValueError("Titre trop court")
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE products SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND seller_user_id = ?', (new_title, product_id, user_id))
                conn.commit()
                conn.close()
                state = self.state_manager.get_state(user_id)
                state.pop('editing_product_title', None)
                self.state_manager.update_state(user_id, **state)
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                from app.core.i18n import t as i18n
                await update.message.reply_text(
                    i18n(lang, 'success_title_updated'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_back_dashboard'), callback_data='seller_dashboard')
                    ]])
                )
            except Exception as e:
                logger.error(f"Erreur maj titre produit: {e}")
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                from app.core.i18n import t as i18n
                await update.message.reply_text(
                    i18n(lang, 'err_title_update_error'),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(i18n(lang, 'btn_back_dashboard'), callback_data='seller_dashboard')
                    ]])
                )
        elif user_state.get('editing_product_description'):
            product_id = user_state.get('editing_product_description')
            lang = self.get_user_language(user_id)
            success = await self.sell_handlers.process_product_description_update(self, update, product_id, message_text, lang)
            if success:
                state = self.state_manager.get_state(user_id)
                state.pop('editing_product_description', None)
                self.state_manager.update_state(user_id, **state)
        elif user_state.get('editing_seller_name'):
            try:
                new_name = message_text.strip()[:20]
                if len(new_name) < 2:
                    raise ValueError("Nom trop court")
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET seller_name = ? WHERE user_id = ?', (new_name, user_id))
                conn.commit()
                conn.close()
                state = self.state_manager.get_state(user_id)
                state.pop('editing_seller_name', None)
                self.state_manager.update_state(user_id, **state)
                await update.message.reply_text("✅ Nom de vendeur mis à jour avec succès !")
            except Exception as e:
                logger.error(f"Erreur maj nom vendeur: {e}")
                await update.message.reply_text("❌ Nom invalide (minimum 2 caractères) ou erreur mise à jour.")
        elif user_state.get('editing_seller_bio'):
            try:
                new_bio = message_text.strip()[:300]
                if len(new_bio) < 10:
                    raise ValueError("Bio trop courte")
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET seller_bio = ? WHERE user_id = ?', (new_bio, user_id))
                conn.commit()
                conn.close()
                state = self.state_manager.get_state(user_id)
                state.pop('editing_seller_bio', None)
                self.state_manager.update_state(user_id, **state)
                await update.message.reply_text("✅ Biographie vendeur mise à jour avec succès !")
            except Exception as e:
                logger.error(f"Erreur maj bio vendeur: {e}")
                await update.message.reply_text("❌ Biographie invalide (minimum 10 caractères) ou erreur mise à jour.")

        # === DÉFAUT : Détection automatique d'ID produit ===
        else:
            # BUYER_WORKFLOW_V2_SPEC.md : "À N'IMPORTE QUELLE étape"
            # Détecter si le message ressemble à un ID produit
            message_clean = message_text.strip().upper()

            # Pattern: TBF-{hex}-{number} ou simplement commence par TBF
            if message_clean.startswith('TBF') or 'TBF-' in message_clean:
                # L'utilisateur essaie de chercher un produit directement
                logger.info(f"🔍 Auto-detection ID produit: {message_clean}")
                await self.buy_handlers.process_product_search(self, update, message_text)
            else:
                # Message non reconnu - Essayer recherche textuelle
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                logger.info(f"🔍 Tentative recherche textuelle: {message_text}")
                await self.buy_handlers.process_product_search(self, update, message_text)





    async def process_support_ticket(self, update: Update, message_text: str):
        user_id = update.effective_user.id
        state = self.state_manager.get_state(user_id)
        step = state.get('step')

        if step == 'subject':
            state['subject'] = message_text[:100]
            state['step'] = 'message'
            # UI i18n
            user_data = self.user_repo.get_user(user_id)
            lang = user_data['language_code'] if user_data else 'fr'
            await update.message.reply_text("Enter your detailed message:" if lang == 'en' else "Entrez votre message détaillé:")
            return

        if step == 'message':
            user_data = self.user_repo.get_user(user_id)
            lang = user_data['language_code'] if user_data else 'fr'
            subject = state.get('subject', 'No subject' if lang == 'en' else 'Sans sujet')
            content = message_text[:2000]

            from app.services.support_service import SupportService
            ticket_id = SupportService(self.db_path).create_ticket(user_id, subject, content)
            if ticket_id:
                # Nettoyer uniquement le contexte de création de ticket
                state = self.state_manager.get_state(user_id)
                for k in ['creating_ticket', 'step', 'subject']:
                    state.pop(k, None)
                # État mis à jour via StateManager (pas besoin de réassigner)
                await update.message.reply_text(
                    (f"🎫 Ticket created: {ticket_id}\nOur team will get back to you soon." if lang == 'en' else f"🎫 Ticket créé: {ticket_id}\nNotre équipe vous répondra bientôt."))
            else:
                await update.message.reply_text("❌ Error while creating the ticket." if lang == 'en' else "❌ Erreur lors de la création du ticket.")

    # process_messaging_reply removed - use support_handlers.process_messaging_reply


    async def handle_document_upload(self, update, context):
        """Handle file uploads for product creation"""
        try:
            user_id = update.effective_user.id
            user_state = self.state_manager.get_state(user_id)

            # 🔍 DEBUG COMPLET
            logger.info(f"📄 DOCUMENT UPLOAD - User {user_id}")
            logger.info(f"   State: {user_state}")
            logger.info(f"   adding_product: {user_state.get('adding_product')}")
            logger.info(f"   step: {user_state.get('step')}")
            logger.info(f"   Document type: {update.message.document.mime_type if update.message.document else 'None'}")
            logger.info(f"   Full memory cache: {self.state_manager.user_states.get(user_id, 'NOT FOUND')}")

            # 🔧 FIX: Si c'est une image envoyée comme document et qu'on est à l'étape cover_image
            if user_state.get('adding_product') and user_state.get('step') == 'cover_image':
                mime_type = update.message.document.mime_type if update.message.document else ''
                if mime_type in ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']:
                    logger.info(f"🔀 ROUTING: Image sent as document, redirecting to cover_image handler")
                    # Convertir le document en format photo-like et déléguer au handler photo
                    await self.sell_handlers.process_cover_image_upload(self, update, photo_as_document=update.message.document)
                    return

            # Vérifier si l'utilisateur est dans le processus d'ajout de produit
            if not user_state.get('adding_product') or user_state.get('step') != 'file':
                # 🔍 DEBUG: Pourquoi rejeté
                logger.warning(f"❌ DOCUMENT REJECTED - adding_product={user_state.get('adding_product')}, step={user_state.get('step')} (expected 'file')")
                await update.message.reply_text(
                    f"❌ Pas d'ajout de produit en cours ou étape incorrecte.\n\n"
                    f"🔍 DEBUG:\n"
                    f"• État: {user_state.get('step')}\n"
                    f"• adding_product: {user_state.get('adding_product')}\n"
                    f"• Attendu: step='file'"
                )
                return

            # Déléguer au sell_handlers
            logger.info(f"✅ DOCUMENT ACCEPTED - Delegating to process_file_upload")
            await self.sell_handlers.process_file_upload(self, update, update.message.document)

        except Exception as e:
            logger.error(f"Error handling document upload: {e}")
            await update.message.reply_text("❌ Erreur lors du traitement du fichier.")

    async def handle_photo_upload(self, update, context):
        """Handle photo uploads for product cover images"""
        try:
            user_id = update.effective_user.id
            user_state = self.state_manager.get_state(user_id)

            # 🔍 DEBUG COMPLET
            logger.info(f"📸 PHOTO UPLOAD - User {user_id}")
            logger.info(f"   State: {user_state}")
            logger.info(f"   adding_product: {user_state.get('adding_product')}")
            logger.info(f"   step: {user_state.get('step')}")
            logger.info(f"   Photo count: {len(update.message.photo) if update.message.photo else 0}")
            logger.info(f"   Full memory cache: {self.state_manager.user_states.get(user_id, 'NOT FOUND')}")

            # Only process if in cover_image step during product creation
            if user_state.get('adding_product') and user_state.get('step') == 'cover_image':
                logger.info(f"✅ PHOTO ACCEPTED - Delegating to process_cover_image_upload")
                await self.sell_handlers.process_cover_image_upload(self, update, update.message.photo)
            else:
                # DEBUG: Show why it was rejected
                logger.warning(f"❌ PHOTO REJECTED - adding_product={user_state.get('adding_product')}, step={user_state.get('step')} (expected 'cover_image')")
                if user_state.get('adding_product'):
                    await update.message.reply_text(
                        f"⚠️ État actuel: {user_state.get('step')}\n"
                        f"Attendu: cover_image\n\n"
                        f"🔍 DEBUG:\n"
                        f"• product_data keys: {list(user_state.get('product_data', {}).keys())}\n"
                        f"• Full state keys: {list(user_state.keys())}"
                    )
                else:
                    # Ignore photos sent in other contexts (could be in chat, support, etc.)
                    logger.info(f"Photo ignored - User not in product creation mode")

        except Exception as e:
            logger.error(f"Error handling photo upload: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await update.message.reply_text("❌ Erreur lors du traitement de l'image.")

