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
    PSYCOPG2 = "psycopg2"
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
    def detect_from_url(url: str) -> Tuple[DatabaseDialect, str, Dict[str, Any]]:
        """Detect database type from connection URL."""
        parsed = urlparse(url)
        
        # Extract scheme (database type)
        scheme = parsed.scheme
        if scheme == 'sqlite':
            db_type = DatabaseDialect.SQLITE
            driver = 'sqlite3'
            kwargs = {'database': parsed.path.lstrip('/') or ':memory:'}
            
        elif scheme in ['postgres', 'postgresql']:
            db_type = DatabaseDialect.POSTGRES
            driver = DatabaseDetector._detect_postgres_driver()
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
            driver = DatabaseDetector._detect_mysql_driver()
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
    def detect_from_kwargs(kwargs: Dict[str, Any]) -> Tuple[DatabaseDialect, str]:
        """Detect database type from connection kwargs."""
        # Check for explicit database type
        if 'database' in kwargs and isinstance(kwargs['database'], str):
            if kwargs['database'].startswith((':memory:', 'file:')) or '.db' in kwargs['database']:
                return DatabaseDialect.SQLITE, 'sqlite3'
        
        # Check for PostgreSQL indicators
        if any(key in kwargs for key in ['port', 'user', 'password', 'host']):
            if kwargs.get('port') == 5432 or 'postgres' in str(kwargs.get('database', '')):
                return DatabaseDialect.POSTGRES, DatabaseDetector._detect_postgres_driver()
        
        # Check for MySQL indicators  
        if kwargs.get('port') == 3306 or any(key in kwargs for key in ['unix_socket', 'auth_plugin']):
            return DatabaseDialect.MYSQL, DatabaseDetector._detect_mysql_driver()
        
        # Default to SQLite if no clear indicators
        return DatabaseDialect.SQLITE, 'sqlite3'
    
    @staticmethod
    def _detect_sqlite_driver() -> str:
        """Detect which SQLite driver is available."""
        try:
            import aiosqlite # noqa
            return SQLiteDriver.AIOSQLITE
        except ImportError:
            return SQLiteDriver.SQLITE3
    
    @staticmethod
    def _detect_postgres_driver() -> str:
        """Detect which PostgreSQL driver is available."""
        try:
            import psycopg2 # noqa
            return PostgreSQLDriver.PSYCOPG2
        except ImportError:
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
                        "psycopg2, psycopg3, or pg8000"
                    )
    
    @staticmethod
    def _detect_mysql_driver() -> str:
        """Detect which MySQL driver is available."""
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
    
    @staticmethod
    def _detect_async_postgres_driver() -> str:
        """Detect which async PostgreSQL driver is available."""
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
    
    @staticmethod
    def _detect_async_mysql_driver() -> str:
        """Detect which async MySQL driver is available."""
        try:
            import aiomysql # noqa
            return MySQLDriver.AIOMYSQL
        except ImportError:
            raise ImportError(
                "No async MySQL driver found. Please install aiomysql"
            )