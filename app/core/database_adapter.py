"""
Database Adapter - Abstraction layer for multiple database backends
"""
import sqlite3
import logging
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DatabaseAdapter(ABC):
    """Abstract database adapter"""

    @abstractmethod
    def connect(self):
        """Create database connection"""
        pass

    @abstractmethod
    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute query and return result"""
        pass

    @abstractmethod
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch single row as dict"""
        pass

    @abstractmethod
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows as list of dicts"""
        pass

    @abstractmethod
    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """Execute query multiple times"""
        pass

    @abstractmethod
    def close(self):
        """Close connection"""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Create SQLite connection with row factory"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            return self.connection
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite connection error: {e}")
            raise

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute query and return cursor"""
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return cursor
        except sqlite3.Error as e:
            if self.connection:
                self.connection.rollback()
            logger.error(f"❌ SQLite execute error: {e}")
            raise

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch single row as dict"""
        try:
            cursor = self.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite fetch_one error: {e}")
            return None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows as list of dicts"""
        try:
            cursor = self.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite fetch_all error: {e}")
            return []

    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """Execute query multiple times"""
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()
            cursor.executemany(query, params_list)
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            if self.connection:
                self.connection.rollback()
            logger.error(f"❌ SQLite execute_many error: {e}")
            return False

    def close(self):
        """Close SQLite connection"""
        if self.connection:
            self.connection.close()
            self.connection = None


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter (ready for future implementation)"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None

    def connect(self):
        """Create PostgreSQL connection (requires psycopg2)"""
        # TODO: Implement when PostgreSQL is needed
        # import psycopg2
        # import psycopg2.extras
        # self.connection = psycopg2.connect(self.connection_string)
        # self.connection.cursor_factory = psycopg2.extras.RealDictCursor
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute PostgreSQL query"""
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch single row from PostgreSQL"""
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows from PostgreSQL"""
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """Execute query multiple times in PostgreSQL"""
        raise NotImplementedError("PostgreSQL adapter not yet implemented")

    def close(self):
        """Close PostgreSQL connection"""
        raise NotImplementedError("PostgreSQL adapter not yet implemented")


class DatabaseFactory:
    """Factory for creating database adapters"""

    @staticmethod
    def create_adapter(db_type: str, **kwargs) -> DatabaseAdapter:
        """Create database adapter based on type"""
        if db_type.lower() == 'sqlite':
            return SQLiteAdapter(kwargs.get('db_path', 'database.db'))
        elif db_type.lower() == 'postgresql':
            return PostgreSQLAdapter(kwargs.get('connection_string', ''))
        else:
            raise ValueError(f"Unsupported database type: {db_type}")


# Global database instance
_db_adapter: Optional[DatabaseAdapter] = None


def get_database_adapter(db_type: str = 'sqlite', **kwargs) -> DatabaseAdapter:
    """Get global database adapter instance"""
    global _db_adapter
    if _db_adapter is None:
        _db_adapter = DatabaseFactory.create_adapter(db_type, **kwargs)
    return _db_adapter


# Global database closer removed - never used (6 lines removed)