"""
Core Utilities - Helper functions extracted from bot_mlt.py
"""
import os
import time
import random
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """Escape special markdown characters"""
    special_chars = "_*[]()~`>#+-=|{}.!"
    escaped = ""
    for char in str(text):
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped


def sanitize_filename(name: str) -> str:
    """Sanitize filename for security"""
    safe_name = os.path.basename(name or '')
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    sanitized = ''.join(ch if ch in allowed else '_' for ch in safe_name)
    return sanitized or f"file_{int(time.time())}"


def generate_product_id(db_path: str) -> str:
    """Generate unique product ID using counter-based system"""
    from app.core import get_sqlite_connection

    conn = get_sqlite_connection(db_path)
    cursor = conn.cursor()

    try:
        # Ensure counters table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS id_counters (
                counter_type TEXT PRIMARY KEY,
                current_value INTEGER DEFAULT 0
            )
        ''')

        # Get and increment product counter
        cursor.execute('''
            INSERT OR IGNORE INTO id_counters (counter_type, current_value)
            VALUES ('product', 0)
        ''')

        cursor.execute('''
            UPDATE id_counters
            SET current_value = current_value + 1
            WHERE counter_type = 'product'
        ''')

        cursor.execute('''
            SELECT current_value FROM id_counters
            WHERE counter_type = 'product'
        ''')

        counter = cursor.fetchone()[0]

        # Format: TBF-{hex_timestamp}-{counter:06d}
        timestamp_hex = hex(int(time.time()))[2:].upper()  # Remove '0x' prefix
        product_id = f"TBF-{timestamp_hex}-{counter:06d}"

        conn.commit()
        conn.close()

        logger.info(f"Generated product ID: {product_id}")
        return product_id

    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error generating product ID: {e}")
        raise e


def generate_ticket_id(db_path: str) -> str:
    """Generate unique ticket ID using counter-based system"""
    from app.core import get_sqlite_connection

    conn = get_sqlite_connection(db_path)
    cursor = conn.cursor()

    try:
        # Ensure counters table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS id_counters (
                counter_type TEXT PRIMARY KEY,
                current_value INTEGER DEFAULT 0
            )
        ''')

        # Get and increment ticket counter
        cursor.execute('''
            INSERT OR IGNORE INTO id_counters (counter_type, current_value)
            VALUES ('ticket', 0)
        ''')

        cursor.execute('''
            UPDATE id_counters
            SET current_value = current_value + 1
            WHERE counter_type = 'ticket'
        ''')

        cursor.execute('''
            SELECT current_value FROM id_counters
            WHERE counter_type = 'ticket'
        ''')

        counter = cursor.fetchone()[0]

        # Format: TKT-{hex_timestamp}-{counter:06d}
        timestamp_hex = hex(int(time.time()))[2:].upper()  # Remove '0x' prefix
        ticket_id = f"TKT-{timestamp_hex}-{counter:06d}"

        conn.commit()
        conn.close()

        logger.info(f"Generated ticket ID: {ticket_id}")
        return ticket_id

    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error generating ticket ID: {e}")
        raise e


def columnize(keyboard):
    """Convert keyboard to single column format"""
    return [[button] for row in keyboard for button in row]


def get_text(key: str, lang: str = 'fr') -> str:
    """Textes multilingues - version simplifiée"""
    translations = {
        'welcome': {
            'fr': '🎉 **BIENVENUE SUR THEBESTFORMATIONS**',
            'en': '🎉 **WELCOME TO THEBESTFORMATIONS**'
        },
        'main_menu': {
            'fr': '🏠 Menu principal',
            'en': '🏠 Main menu'
        },
        'err_temp': {
            'fr': '❌ Erreur temporaire. Veuillez réessayer.',
            'en': '❌ Temporary error. Please try again.'
        }
    }
    return translations.get(key, {}).get(lang, key)


def tr(lang: str, fr_text: str, en_text: str) -> str:
    """Quick translation helper"""
    return fr_text if lang == 'fr' else en_text