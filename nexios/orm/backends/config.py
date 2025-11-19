from enum import Enum
from typing import Any, Dict, Tuple
from urllib.parse import urlparse


class DatabaseDialect(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MYSQL = "mysql"

class PostgreSQLDriver(str, Enum):
    ASYNCPG = "asyncpg"
    PG8000 = "pg8000"
    PSYCOPG3 = "psycopg3"

class MySQLDriver(str, Enum):
    MYSQL_CONNECTOR = "mysql-connector"
    PYMySQL = "pymysql"
    AIOMYSQL = "aiomysql"

class SQLiteDriver(str, Enum):
    AIOSQLITE = "aiosqlite"
    SQLITE3 = "sqlite3"

class DatabaseDetector:
    """Automatically detects database type and driver from connection parameters."""
    
    @staticmethod
    def detect_from_url(url: str, is_async: bool = False) -> Tuple[DatabaseDialect, str, Dict[str, Any]]:
        """Detect database type from connection URL."""
        parsed = urlparse(url)
        
        # Extract scheme (database type)
        scheme = parsed.scheme
        if scheme == 'sqlite':
            db_type = DatabaseDialect.SQLITE
            driver = DatabaseDetector._detect_sqlite_driver(is_async)
            kwargs = {'database': parsed.path.lstrip('/') or ':memory:'}
            
        elif scheme in ['postgres', 'postgresql']:
            db_type = DatabaseDialect.POSTGRES
            driver = DatabaseDetector._detect_postgres_driver(is_async)
            kwargs = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password,
            }
            # Add query parameters as additional kwargs
            if parsed.query:
                import urllib.parse
                query_params = urllib.parse.parse_qs(parsed.query)
                for key, value in query_params.items():
                    kwargs[key] = value[0] if len(value) == 1 else value
                    
        elif scheme in ['mysql', 'mariadb']:
            db_type = DatabaseDialect.MYSQL
            driver = DatabaseDetector._detect_mysql_driver(is_async)
            kwargs = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 3306,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password,
            }
            if parsed.query:
                import urllib.parse
                query_params = urllib.parse.parse_qs(parsed.query)
                for key, value in query_params.items():
                    kwargs[key] = value[0] if len(value) == 1 else value
                    
        else:
            raise ValueError(f"Unsupported database URL scheme: {scheme}")
            
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return db_type, driver, kwargs
    
    @staticmethod
    def detect_from_kwargs(kwargs: Dict[str, Any], is_async: bool = False) -> Tuple[DatabaseDialect, str]:
        """Detect database type from connection kwargs."""
        # Check for explicit database type
        if 'database' in kwargs and isinstance(kwargs['database'], str):
            if kwargs['database'].startswith((':memory:', 'file:')) or '.db' in kwargs['database']:
                driver = DatabaseDetector._detect_sqlite_driver(is_async)
                return DatabaseDialect.SQLITE, driver
        
        # Check for PostgreSQL indicators
        if any(key in kwargs for key in ['port', 'user', 'password', 'host']):
            if kwargs.get('port') == 5432 or 'postgres' in str(kwargs.get('dbname', '')):
                driver = DatabaseDetector._detect_postgres_driver(is_async)
                return DatabaseDialect.POSTGRES, driver
        
        # Check for MySQL indicators  
        if kwargs.get('port') == 3306 or any(key in kwargs for key in ['unix_socket', 'auth_plugin']):
            driver = DatabaseDetector._detect_mysql_driver(is_async)
            return DatabaseDialect.MYSQL, driver
        
        # Default to SQLite if no clear indicators
        driver = DatabaseDetector._detect_sqlite_driver(is_async)
        return DatabaseDialect.SQLITE, driver
    
    @staticmethod
    def _detect_sqlite_driver(is_async: bool = False):
        """Detect which SQLite driver is available."""
        if is_async:
            try:
                import aiosqlite # noqa
                return SQLiteDriver.AIOSQLITE
            except ImportError:
                raise ImportError("aiosqlite is required for async SQLite operations")
        else:
            try:
                import sqlite3 # noqa
                return SQLiteDriver.SQLITE3
            except ImportError:
                raise ImportError("sqlite3 is required for sync SQLite operations")
    
    @staticmethod
    def _detect_postgres_driver(is_async: bool = False):
        """Detect which PostgreSQL driver is available."""
        if is_async:
            try:
                import psycopg # noqa
                return PostgreSQLDriver.PSYCOPG3
            except ImportError:
                try:
                    import asyncpg # noqa
                    return PostgreSQLDriver.ASYNCPG
                except ImportError:
                    raise ImportError(
                        "No async PostgreSQL driver found. Please install one of: "
                        "psycopg3 or asyncpg"
                    )
        else:
            try:
                import psycopg # noqa
                return PostgreSQLDriver.PSYCOPG3
            except ImportError:
                try:
                    import pg8000 # noqa
                    return PostgreSQLDriver.PG8000
                except ImportError:
                    raise ImportError(
                            "No PostgreSQL driver found. Please install one of: "
                            "psycopg3, or pg8000"
                        )
    
    @staticmethod
    def _detect_mysql_driver(is_async: bool = False):
        """Detect which MySQL driver is available."""
        if is_async:
            try:
                import aiomysql # noqa
                return MySQLDriver.AIOMYSQL
            except ImportError:
                raise ImportError("aiomysql is required for async MySQL operations")
        else:
            try:
                import mysql.connector # noqa
                return MySQLDriver.MYSQL_CONNECTOR
            except ImportError:
                try:
                    import pymysql # noqa
                    return MySQLDriver.PYMySQL
                except ImportError:
                    raise ImportError(
                        "No MySQL driver found. Please install one of: "
                        "mysql-connector-python or pymysql"
                    )