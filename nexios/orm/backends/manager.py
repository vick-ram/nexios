from typing_extensions import Any, Optional, cast
from nexios.orm.backends.config import DatabaseDetector, DatabaseDialect, MySQLDriver, PostgreSQLDriver
from nexios.orm.backends.dialects.mysql.base import MySQLConnection_
from nexios.orm.backends.dialects.postgres.base import PostgresConnection
from nexios.orm.backends.dialects.sqlite.aiosqlite_ import AioSQLiteConnection
from nexios.orm.backends.dialects.sqlite.sqlite_ import SQLiteConnection
from nexios.orm.backends.pool.base import BaseAsyncConnectionPool, BaseConnectionPool
from nexios.orm.backends.pool.factory import ConnectionPoolFactory
from nexios.orm.connection import (
    AsyncCursor,
    AsyncDatabaseConnection,
    SyncCursor,
    SyncDatabaseConnection,
)

class DatabaseManager:
    def __init__(self, url: Optional[str] = None, **kwargs: Any):
        if url:
            self.db_type, self.driver, connection_params = DatabaseDetector.detect_from_url(url, False)
            connection_params.update(kwargs)
            self.connection_params = connection_params
        else:
            self.db_type, self.driver = DatabaseDetector.detect_from_kwargs(kwargs, False)
            self.connection_params = kwargs

        self._connection: Optional[SyncDatabaseConnection] = None
        self._connection_pool: Optional[BaseConnectionPool] = None
        self._use_pool = kwargs.get('use_pool', False)
        self._pool_min_size = kwargs.get('pool_min_size', 1)
        self._pool_max_size = kwargs.get('pool_max_size', 10)

    def connect(self) -> SyncDatabaseConnection:
        if self._use_pool:
            if self._connection_pool is None:
                self._connection_pool = ConnectionPoolFactory.create_sync_pool(
                    dialect=self.db_type,
                    driver=self.driver,
                    connection=self._create_direct_connection,
                    min_size=self._pool_min_size,
                    max_size=self._pool_max_size,
                    **self.connection_params
                )
            return self._connection_pool.get_connection()
        else:
            return self._create_direct_connection()
    
    def _create_direct_connection(self) -> SyncDatabaseConnection:
        if self.db_type == DatabaseDialect.SQLITE:
            import sqlite3
            raw_conn = sqlite3.connect(**self.connection_params)
            self._connection = SQLiteConnection(raw_conn)
        elif self.db_type == DatabaseDialect.POSTGRES:
            if self.driver == PostgreSQLDriver.PSYCOPG3:
                import psycopg
                raw_conn = psycopg.connect(**self.connection_params)
            elif self.driver == PostgreSQLDriver.PG8000:
                import pg8000
                raw_conn = pg8000.connect(**self.connection_params)
            else:
                raise ValueError(f"Unsupported Postgres driver: {self.driver}")
            
            self._connection = PostgresConnection.connect(raw_conn)

        elif self.db_type == DatabaseDialect.MYSQL:
            if self.driver == MySQLDriver.MYSQL_CONNECTOR:
                import mysql.connector
                raw_conn = mysql.connector.connect(**self.connection_params)
            elif self.driver == MySQLDriver.PYMySQL:
                import pymysql
                raw_conn = pymysql.connect(**self.connection_params)
            else:
                raise ValueError(f"Unsupported MySQL driver: {self.driver}")
            
            self._connection = MySQLConnection_.connection(raw_conn)
        
        return cast(SyncDatabaseConnection, self._connection)
    
    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        if self._use_pool and self._connection_pool:
            self._connection_pool.return_connection(conn) # type: ignore
        else:
            conn.close()


    def cursor(self) -> SyncCursor:
        if not self._connection:
            self.connect()
        return self._connection.cursor()  # type: ignore

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None


class AsyncDatabaseManager:
    def __init__(self, url: Optional[str] = None, **kwargs: Any):
        if url:
            self.db_type, self.driver, connection_params = DatabaseDetector.detect_from_url(url, True)
            connection_params.update(kwargs)
            self.connection_params = connection_params
        else:
            self.db_type, self.driver = DatabaseDetector.detect_from_kwargs(kwargs, True)
            self.connection_params = kwargs

        self._connection: Optional[AsyncDatabaseConnection] = None
        self._connection_pool: Optional['BaseAsyncConnectionPool'] = None
        self._use_pool = kwargs.get('use_pool', False)
        self._pool_min_size = kwargs.get('pool_min_size', 1)
        self._pool_max_size = kwargs.get('pool_max_size', 10)

    async def connect(self) -> AsyncDatabaseConnection:
        if self._use_pool:
            if self._connection_pool is None:
                self._connection_pool = ConnectionPoolFactory.create_async_pool(
                    dialect=self.db_type,
                    driver=self.driver,
                    connection=self._create_async_direct_connection,
                    min_size=self._pool_min_size,
                    max_size=self._pool_max_size,
                    **self.connection_params
                )
            return await self._connection_pool.get_connection()
        else:
            return await self._create_async_direct_connection()

        
    
    async def _create_async_direct_connection(self) -> AsyncDatabaseConnection:
        if self.db_type == DatabaseDialect.SQLITE:
            from aiosqlite import connect

            raw_conn = await connect(**self.connection_params)
            self._connection = AioSQLiteConnection(raw_conn)
        elif self.db_type == DatabaseDialect.POSTGRES:
            if self.driver == PostgreSQLDriver.PSYCOPG3:
                import psycopg
                raw_conn = await psycopg.AsyncConnection.connect(**self.connection_params)
            elif self.driver == PostgreSQLDriver.ASYNCPG:
                from asyncpg import connect
                raw_conn = await connect(**self.connection_params)
            else:
                raise ValueError(f"Unsupported Postgres driver: {self.driver}")
            
            self._connection = await PostgresConnection.connect_async(raw_conn)

        elif self.db_type == DatabaseDialect.MYSQL:
            if self.driver == "aiomysql":
                from aiomysql import connect

                pool = await connect(**self.connection_params)
                self._connection = await MySQLConnection_.connection_async(pool)
            else:
                raise ValueError(f"Unsupported MySQL driver: {self.driver}")
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        return cast(AsyncDatabaseConnection, self._connection)
    
    async def return_connection(self, conn: AsyncDatabaseConnection):
        if self._use_pool and self._connection_pool:
            await self._connection_pool.return_connection() # type: ignore
        else:
            await conn.close()

    async def cursor(self) -> AsyncCursor:
        if not self._connection:
            await self.connect()
        cursor = await self._connection.cursor()  # type: ignore
        return cast(AsyncCursor, cursor)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
