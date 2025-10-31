"""
Core Utilities - Helper functions extracted from bot_mlt.py
"""
import os
import time
import random
import psycopg2
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


# sanitize_filename supprimé - version unique conservée dans file_utils.py
# (version file_utils plus robuste: limite 100 chars, settings.ALLOWED_FILENAME_CHARS)


def generate_product_id() -> str:
    """Generate unique product ID using counter-based system"""
    from app.core.database_init import get_postgresql_connection
    import psycopg2.extras

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
            INSERT INTO id_counters (counter_type, current_value)
            VALUES ('product', 0)
            ON CONFLICT (counter_type) DO NOTHING
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

        counter = cursor.fetchone()['current_value']

        # Format: TBF-{hex_timestamp}-{counter:06d}
        timestamp_hex = hex(int(time.time()))[2:].upper()  # Remove '0x' prefix
        product_id = f"TBF-{timestamp_hex}-{counter:06d}"

        conn.commit()
        conn.close()

        logger.info(f"Generated product ID: {product_id}")
        return product_id

    except psycopg2.Error as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error generating product ID: {e}")
        raise e


def generate_ticket_id() -> str:
    """Generate unique ticket ID using counter-based system"""
    from app.core.database_init import get_postgresql_connection
    import psycopg2.extras

    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
            INSERT INTO id_counters (counter_type, current_value)
            VALUES ('ticket', 0)
            ON CONFLICT (counter_type) DO NOTHING
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

        counter = cursor.fetchone()['current_value']

        # Format: TKT-{hex_timestamp}-{counter:06d}
        timestamp_hex = hex(int(time.time()))[2:].upper()  # Remove '0x' prefix
        ticket_id = f"TKT-{timestamp_hex}-{counter:06d}"

        conn.commit()
        conn.close()

        logger.info(f"Generated ticket ID: {ticket_id}")
        return ticket_id

    except psycopg2.Error as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error generating ticket ID: {e}")
        raise e


# Fonctions mortes supprimées: columnize, get_text, tr
# Remplacées par i18n.py centralisé - aucune occurrence trouvée