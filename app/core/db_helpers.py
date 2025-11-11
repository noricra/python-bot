"""
Database Helper Functions - Connection Pool Wrappers
Simplifies database operations with automatic connection management
"""
import logging
from functools import wraps
from app.core.db_pool import get_connection, put_connection

logger = logging.getLogger(__name__)


def with_db_connection(func):
    """
    Decorator that automatically provides and manages database connection.

    Usage:
        @with_db_connection
        def my_function(conn, ...other_args):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            # ... do work ...
            conn.commit()
            return result

        # Call function normally (conn is injected automatically)
        result = my_function(arg1, arg2)

    The decorator:
    - Gets connection from pool
    - Injects it as first argument
    - Handles errors (rollback on exception)
    - Returns connection to pool (always)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = get_connection()
            # Inject connection as first argument
            return func(conn, *args, **kwargs)

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Database error in {func.__name__}: {e}")
            raise

        finally:
            if conn:
                put_connection(conn)

    return wrapper


def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
    """
    Execute a database query with automatic connection management.

    Args:
        query: SQL query string
        params: Query parameters (tuple)
        fetch_one: If True, return single row
        fetch_all: If True, return all rows
        commit: If True, commit transaction

    Returns:
        Query result (depending on fetch_one/fetch_all)

    Usage:
        # Insert with commit
        execute_query(
            "INSERT INTO users (user_id, username) VALUES (%s, %s)",
            (123, "john"),
            commit=True
        )

        # Select one
        user = execute_query(
            "SELECT * FROM users WHERE user_id = %s",
            (123,),
            fetch_one=True
        )

        # Select all
        users = execute_query(
            "SELECT * FROM users WHERE is_seller = %s",
            (True,),
            fetch_all=True
        )
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(query, params or ())

        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()

        if commit:
            conn.commit()

        cursor.close()
        return result

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Query execution error: {e}")
        logger.error(f"Query: {query}")
        raise

    finally:
        if conn:
            put_connection(conn)


def execute_dict_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
    """
    Execute a database query and return results as dictionaries (using RealDictCursor).

    Same as execute_query but returns dict instead of tuple.

    Returns:
        dict or list[dict]: Query results as dictionaries

    Usage:
        user = execute_dict_query(
            "SELECT * FROM users WHERE user_id = %s",
            (123,),
            fetch_one=True
        )
        print(user['username'])  # Access by key instead of index
    """
    import psycopg2.extras

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute(query, params or ())

        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()

        if commit:
            conn.commit()

        cursor.close()
        return result

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Query execution error: {e}")
        logger.error(f"Query: {query}")
        raise

    finally:
        if conn:
            put_connection(conn)


class TransactionContext:
    """
    Context manager for database transactions with automatic rollback on error.

    Usage:
        with TransactionContext() as (conn, cursor):
            cursor.execute("INSERT INTO users (...) VALUES (...)")
            cursor.execute("UPDATE products SET ...")
            # Automatically commits if no exception
            # Automatically rollbacks on exception
    """

    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred, rollback
            if self.conn and not self.conn.closed:
                self.conn.rollback()
                logger.error(f"❌ Transaction rolled back due to error: {exc_val}")
        else:
            # No exception, commit
            if self.conn and not self.conn.closed:
                self.conn.commit()

        # Clean up
        if self.cursor:
            self.cursor.close()

        if self.conn:
            put_connection(self.conn)

        # Don't suppress exceptions
        return False
