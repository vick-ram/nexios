from enum import StrEnum
from typing import Any, Dict, Tuple
from urllib.parse import urlparse


class DatabaseDialect(StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MYSQL = "mysql"

class PostgreSQLDriver(StrEnum):
    ASYNCPG = "asyncpg"
    PG8000 = "pg8000"
    PSYCOPG3 = "psycopg3"

class MySQLDriver(StrEnum):
    MYSQL_CONNECTOR = "mysql-connector"
    PYMySQL = "pymysql"
    AIOMYSQL = "aiomysql"

class SQLiteDriver(StrEnum):
    AIOSQLITE = "aiosqlite"
    SQLITE3 = "sqlite3"

class DatabaseDetector:
    """Automatically detects database type and driver from connection parameters."""
    
    @staticmethod
    def detect_from_url(url: str, is_async: bool = False) -> Tuple[DatabaseDialect, str, Dict[str, Any]]:
        """Detect database type from connection URL."""
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        def parse_query(q: str) -> Dict[str, Any]:
            from urllib.parse import parse_qs
            values = {}
            for k, v in parse_qs(q).items():
                item = v[0] if len(v) == 1 else v
                if isinstance(item, str):
                    if item.isdigit():
                        item = int(item)
                    elif item.replace('.', '').isdigit() and item.count('.') == 1:
                        item = float(item)
                    elif item.lower() in ('true', 'false'):
                        item = item.lower() == 'true'
                    elif item.lower() in ('none', 'null'):
                        item = None
                values[k] = item
            return values
        
        scheme = scheme.split('+')[-1]

        if scheme == 'sqlite':
            db_type = DatabaseDialect.SQLITE
            driver = DatabaseDetector._detect_sqlite_driver(is_async)
            database_path = parsed.path.lstrip('/') or ':memory:'
            kwargs = {'database': database_path}
            
        elif scheme in ['postgres', 'postgresql']:
            db_type = DatabaseDialect.POSTGRES
            driver = DatabaseDetector._detect_postgres_driver(is_async)
            kwargs = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 5432,
                'dbname': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password,
            }
                    
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
                    
        else:
            raise ValueError(f"Unsupported database URL scheme: {scheme}")
        
        if parsed.query:
            kwargs.update(parse_query(parsed.query))
        
        clean_kwargs = {k: v for k, v in kwargs.items() if v is not None}
            
        return db_type, driver, clean_kwargs
    
    @staticmethod
    def detect_from_kwargs(kwargs: Dict[str, Any], is_async: bool = False) -> Tuple[DatabaseDialect, str]:
        """Detect database type from connection kwargs."""
        # # Check for explicit database type
        # if 'database' in kwargs and isinstance(kwargs['database'], str):
        #     if kwargs['database'].startswith((':memory:', 'file:')) or '.db' in kwargs['database']:
        #         driver = DatabaseDetector._detect_sqlite_driver(is_async)
        #         return DatabaseDialect.SQLITE, driver
        
        # # Check for PostgreSQL indicators
        # if any(key in kwargs for key in ['port', 'user', 'password', 'host']):
        #     if kwargs.get('port') == 5432 or 'postgres' in str(kwargs.get('dsn', '')):
        #         driver = DatabaseDetector._detect_postgres_driver(is_async)
        #         return DatabaseDialect.POSTGRES, driver
        
        # # Check for MySQL indicators  
        # if kwargs.get('port') == 3306 or any(key in kwargs for key in ['unix_socket', 'auth_plugin']):
        #     driver = DatabaseDetector._detect_mysql_driver(is_async)
        #     return DatabaseDialect.MYSQL, driver
        
        # # Default to SQLite if no clear indicators
        # driver = DatabaseDetector._detect_sqlite_driver(is_async)
        # return DatabaseDialect.SQLITE, driver
        if 'driver' in kwargs:
            driver = kwargs['driver']
            if driver in [d.value for d in PostgreSQLDriver]:
                return DatabaseDialect.POSTGRES, driver
            elif driver in [d.value for d in MySQLDriver]:
                return DatabaseDialect.MYSQL, driver
            elif driver in [d.value for d in SQLiteDriver]:
                return DatabaseDialect.SQLITE, driver
            else:
                raise ValueError(f"Unsupported driver: {driver}")
        
        if 'dialect' in kwargs:
            dialect = kwargs['dialect']
            if dialect in DatabaseDialect:
                driver_method = getattr(DatabaseDetector, f'_detect_{dialect}_driver')
                return dialect, driver_method(is_async)
        
        database_value = kwargs.get('database', '')
        if isinstance(database_value, str):
            if (database_value == ':memory:' or
                database_value.startswith('file:') or
                database_value.endswith('.db') or
                database_value.endswith('.sqlite') or
                database_value.endswith('sqlite3')
            ):
                driver = DatabaseDetector._detect_sqlite_driver(is_async)
                return DatabaseDialect.SQLITE, driver
        pg_indicators = [
            kwargs.get('port') == 5432,
            'postgres' in str(kwargs.get('dsn', '')),
            'postgres' in str(kwargs.get('host', '')),
            'postgres' in str(kwargs.get('dbname', '')),
            any(key in kwargs for key in ['sslmode', 'application_name'])
        ]

        if any(pg_indicators):
            driver = DatabaseDetector._detect_postgres_driver(is_async)
            return DatabaseDialect.POSTGRES, driver

        mysql_indicators = [
            kwargs.get('port') == 3306,
            any(key in kwargs for key in ['unix_socket', 'auth_plugin', 'charset']),
            'mysql' in str(kwargs.get('host', '')),
            'mysql' in str(kwargs.get('database', '')),
        ]

        if any(mysql_indicators):
            driver = DatabaseDetector._detect_mysql_driver(is_async)
            return DatabaseDialect.MYSQL, driver
        
        if 'database' in kwargs and isinstance(kwargs['database'], str):
            if not any(key in kwargs for key in ['host', 'port', 'user', 'password']):
                driver = DatabaseDetector._detect_sqlite_driver(is_async)
                return DatabaseDialect.SQLITE, driver
        
        try:
            DatabaseDetector._detect_postgres_driver(is_async)
            return DatabaseDialect.POSTGRES, DatabaseDetector._detect_postgres_driver(is_async)
        except ImportError:
            pass
            
        try:
            DatabaseDetector._detect_mysql_driver(is_async)
            return DatabaseDialect.MYSQL, DatabaseDetector._detect_mysql_driver(is_async)
        except ImportError:
            pass
            
        # Ultimate fallback to SQLite
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
                import asyncpg # noqa
                return PostgreSQLDriver.ASYNCPG
            except ImportError:
                try:
                    import psycopg # noqa
                    return PostgreSQLDriver.PSYCOPG3
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