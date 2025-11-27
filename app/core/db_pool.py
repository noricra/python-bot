"""
PostgreSQL Connection Pool - Production-Ready Implementation
Manages database connections efficiently to avoid 'too many connections' errors
"""
import psycopg2
from psycopg2 import pool
import logging
import os
from typing import Optional
import atexit
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Global connection pool (singleton)
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def init_connection_pool(
    min_connections: int = 2,
    max_connections: int = 10
):
    """
    Initialize the PostgreSQL connection pool.
    Must be called once at application startup.

    Args:
        min_connections: Minimum number of connections in pool
        max_connections: Maximum number of connections in pool

    Railway connection limits:
        - Hobby plan: 20 connections max
        - Pro plan: 100 connections max

    Recommended settings:
        - Development: min=2, max=5
        - Production (Hobby): min=2, max=10
        - Production (Pro): min=5, max=20
    """
    global _connection_pool

    if _connection_pool is not None:
        logger.warning("⚠️ Connection pool already initialized. Skipping...")
        return

    try:
        # Priority 1: Try DATABASE_URL (Railway, Heroku, etc.)
        database_url = os.getenv('DATABASE_URL')

        if database_url:
            logger.info("🔌 Using DATABASE_URL for connection...")
            parsed = urlparse(database_url)

            pghost = parsed.hostname
            pgport = parsed.port or 5432
            pgdatabase = parsed.path[1:]  # Remove leading '/'
            pguser = parsed.username
            pgpassword = parsed.password or ''

            logger.info(f"🔌 Initializing PostgreSQL connection pool ({min_connections}-{max_connections} connections) - Host: {pghost}...")
        else:
            # Priority 2: Fall back to individual environment variables
            logger.info("🔌 Using individual PG* environment variables...")
            pghost = os.getenv('PGHOST', 'localhost')
            pgport = int(os.getenv('PGPORT', 5432))
            pgdatabase = os.getenv('PGDATABASE')
            pguser = os.getenv('PGUSER')
            pgpassword = os.getenv('PGPASSWORD', '')

            logger.info(f"🔌 Initializing PostgreSQL connection pool ({min_connections}-{max_connections} connections) - Host: {pghost}...")

        # SSL mode: require for remote, prefer for local
        sslmode = 'prefer' if pghost in ['localhost', '127.0.0.1'] else 'require'

        _connection_pool = pool.ThreadedConnectionPool(
            minconn=min_connections,
            maxconn=max_connections,
            host=pghost,
            port=pgport,
            database=pgdatabase,
            user=pguser,
            password=pgpassword,
            sslmode=sslmode
        )

        logger.info(f"✅ PostgreSQL connection pool initialized successfully")

        # Register cleanup on exit
        atexit.register(close_all_connections)

    except Exception as e:
        logger.error(f"❌ Failed to initialize connection pool: {e}")
        raise


def get_connection():
    """
    Get a connection from the pool.

    Returns:
        psycopg2.connection: Database connection from pool

    Raises:
        RuntimeError: If pool not initialized
        pool.PoolError: If no connection available

    Usage:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            # ... do work ...
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            put_connection(conn)  # IMPORTANT: Always return connection to pool
    """
    global _connection_pool

    if _connection_pool is None:
        raise RuntimeError(
            "Connection pool not initialized. "
            "Call init_connection_pool() at application startup."
        )

    try:
        conn = _connection_pool.getconn()

        if conn is None:
            raise pool.PoolError("No connection available from pool")

        return conn

    except pool.PoolError as e:
        logger.error(f"❌ Pool exhausted: {e}")
        logger.error(
            "⚠️ Possible causes:\n"
            "1. Too many concurrent requests\n"
            "2. Connections not being returned to pool (missing put_connection())\n"
            "3. max_connections too low"
        )
        raise


def put_connection(conn):
    """
    Return a connection to the pool.
    MUST be called after using a connection (use finally block).

    Args:
        conn: Connection to return to pool

    Usage:
        conn = get_connection()
        try:
            # ... use connection ...
        finally:
            put_connection(conn)  # Always return to pool
    """
    global _connection_pool

    if _connection_pool is None:
        logger.warning("⚠️ Connection pool not initialized. Cannot return connection.")
        return

    if conn is not None:
        try:
            # Rollback any uncommitted changes before returning to pool
            if not conn.closed:
                conn.rollback()

            _connection_pool.putconn(conn)

        except Exception as e:
            logger.error(f"❌ Error returning connection to pool: {e}")


def close_all_connections():
    """
    Close all connections in the pool.
    Called automatically at application shutdown (via atexit).
    """
    global _connection_pool

    if _connection_pool is not None:
        logger.info("🔌 Closing all PostgreSQL connections...")
        try:
            _connection_pool.closeall()
            _connection_pool = None
            logger.info("✅ All connections closed successfully")
        except Exception as e:
            logger.error(f"❌ Error closing connections: {e}")


def get_pool_status() -> dict:
    """
    Get current status of the connection pool.
    Useful for monitoring and debugging.

    Returns:
        dict: Pool statistics
            - initialized: bool
            - min_connections: int
            - max_connections: int
            - Note: psycopg2 pool doesn't expose active connections count
    """
    global _connection_pool

    if _connection_pool is None:
        return {
            'initialized': False,
            'min_connections': 0,
            'max_connections': 0
        }

    return {
        'initialized': True,
        'min_connections': _connection_pool.minconn,
        'max_connections': _connection_pool.maxconn
    }


# Context manager for automatic connection handling
class PooledConnection:
    """
    Context manager for database connections.
    Automatically returns connection to pool.

    Usage:
        with PooledConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            # ... do work ...
            conn.commit()
        # Connection automatically returned to pool
    """

    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred, rollback
            if self.conn and not self.conn.closed:
                self.conn.rollback()

        # Always return connection to pool
        put_connection(self.conn)

        # Don't suppress exceptions
        return False
