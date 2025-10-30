"""
Database connection module - PostgreSQL on Railway
"""
import psycopg2
import psycopg2.extras
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_postgresql_connection():
    """
    Get PostgreSQL connection using Railway environment variables

    Returns:
        psycopg2.connection: PostgreSQL database connection
    """
    try:
        # Railway provides these environment variables automatically
        conn = psycopg2.connect(
            host=os.getenv('PGHOST'),
            port=os.getenv('PGPORT', 5432),
            database=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD'),
            sslmode='require'  # Railway requires SSL
        )
        # Enable autocommit for better compatibility
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        raise


# DEPRECATED: Backward compatibility only
def get_sqlite_connection(database_path: Optional[str] = None):
    """
    DEPRECATED: This function is kept for backward compatibility only
    All new code should use get_postgresql_connection()

    Args:
        database_path: Ignored, kept for backward compatibility

    Raises:
        NotImplementedError: SQLite is no longer supported
    """
    logger.error("⚠️ get_sqlite_connection() called but SQLite is no longer supported!")
    logger.error("⚠️ Please migrate to PostgreSQL using get_postgresql_connection()")
    raise NotImplementedError(
        "SQLite is no longer supported. "
        "Please use get_postgresql_connection() from app.core.database_init instead."
    )
