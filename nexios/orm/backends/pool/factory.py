from typing import Any, Callable, Awaitable
from nexios.orm.backends.pool.base import BaseConnectionPool, GenericConnectionPool, GenericAsyncConnectionPool, BaseAsyncConnectionPool
from nexios.orm.backends.config import DatabaseDialect, MySQLDriver, PostgreSQLDriver
from nexios.orm.connection import SyncDatabaseConnection, AsyncDatabaseConnection


class ConnectionPoolFactory:
    @staticmethod
    def create_sync_pool(
        dialect: Any,
        driver: Any,
        connection: Callable[[], SyncDatabaseConnection],
        max_size: int = 10,
        min_size: int = 1,
        **kwargs
    ) -> BaseConnectionPool:
        if dialect == DatabaseDialect.SQLITE:
            from nexios.orm.backends.pool.sqlite.sqlite_pool import SQLitePool
            return SQLitePool(
                min_size=min_size,
                max_size=max_size,
                **kwargs
            )
        elif dialect == DatabaseDialect.POSTGRES:
            if driver == PostgreSQLDriver.PSYCOPG3:
                from nexios.orm.backends.pool.postgres.psycopg3_pool import PsycopgConnectionPool
                return PsycopgConnectionPool(
                    min_size=min_size,
                    max_size=max_size,
                    **kwargs
                )
            elif driver == PostgreSQLDriver.PG8000:
                from nexios.orm.backends.pool.postgres.pg8000_pool import Pg8000ConnectionPool
                return Pg8000ConnectionPool(
                    min_connections=min_size,
                    max_connections=max_size,
                    **kwargs
                )
            else:
                raise ValueError(f"Unsupported Postgres driver: {driver}")
        elif dialect == DatabaseDialect.MYSQL:
            if driver == MySQLDriver.MYSQL_CONNECTOR:
                from nexios.orm.backends.pool.mysql.mysql_connector_pool import MySQLConnectorPool
                return MySQLConnectorPool(
                    min_size=min_size,
                    max_size=max_size,
                    **kwargs
                )
            elif driver == MySQLDriver.PYMySQL:
                from nexios.orm.backends.pool.mysql.pymysql_pool import PyMySQLConnectionPool
                return PyMySQLConnectionPool(
                    min_size=min_size,
                    max_size=max_size,
                    **kwargs
                )
            else:
                raise ValueError(f"Unsupported MySQL driver: {driver}")
        else:
            return GenericConnectionPool(
                create_connection=connection,
                min_size=min_size,
                max_size=max_size,
            )
        
    
    @staticmethod
    def create_async_pool(
        dialect: Any,
        driver: Any,
        connection: Callable[[], Awaitable[AsyncDatabaseConnection]],
        max_size: int = 10,
        min_size: int = 1,
        **kwargs
    ) -> BaseAsyncConnectionPool:

        if dialect == DatabaseDialect.SQLITE:
            from nexios.orm.backends.pool.sqlite.aiosqlite_pool import AioSQLitePool
            return AioSQLitePool(
                min_size=min_size,
                max_size=max_size,
                **kwargs
            )
        elif dialect == DatabaseDialect.POSTGRES:
            if driver == PostgreSQLDriver.ASYNCPG:
                from nexios.orm.backends.pool.postgres.asyncgp_pool import AsyncpgConnectionPool
                return AsyncpgConnectionPool(
                    min_size=min_size,
                    max_size=max_size,
                    **kwargs
                )
            elif driver == PostgreSQLDriver.PSYCOPG3:
                from nexios.orm.backends.pool.postgres.psycopg_async_pool import PsycopgAsynConnectioncPool
                return PsycopgAsynConnectioncPool(
                    min_size=min_size,
                    max_size=max_size,
                    **kwargs
                )
            else:
                raise ValueError(
                    f"Unsupported Postgres driver: {driver}"
                )
        else:
            return GenericAsyncConnectionPool(
                create_connection=connection,
                min_size=min_size,
                max_size=max_size,
            )
            