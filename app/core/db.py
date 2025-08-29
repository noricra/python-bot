import sqlite3
import logging
from typing import Optional


logger = logging.getLogger(__name__)


def get_sqlite_connection(database_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path, timeout=30, check_same_thread=False)
    try:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        conn.execute('PRAGMA foreign_keys=ON;')
        conn.execute('PRAGMA busy_timeout=5000;')
    except Exception as e:
        logger.warning(f"PRAGMA init error: {e}")
    return conn

