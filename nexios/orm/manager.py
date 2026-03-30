from __future__ import annotations

import logging
from typing import Dict

import aiomysql
import pg8000.dbapi
import pg8000.dbapi
from typing_extensions import Any, Optional

from nexios.orm.config import DatabaseDetector, MySQLDriver, PostgreSQLDriver, SQLiteDialect, PostgreSQLDialect, \
    MySQLDialect, SQLiteDriver
from nexios.orm.connection import (
    AsyncCursor,
    AsyncDatabaseConnection,
    SyncCursor,
    SyncDatabaseConnection,
)
from nexios.orm.dbapi.mysql.aiomysql_ import MySQLAioMySQLConnection
from nexios.orm.dbapi.mysql.asyncmy_ import AsyncMyConnection
from nexios.orm.dbapi.mysql.mariadb_ import MariaDBConnection
from nexios.orm.dbapi.mysql.mysql_client import MySQLClientConnection
from nexios.orm.dbapi.mysql.mysql_connector_ import MySQLConnectorConnection
from nexios.orm.dbapi.mysql.pymysql_ import PyMySQLConnection
from nexios.orm.dbapi.postgres.aiopg_ import AioPgConnection
from nexios.orm.dbapi.postgres.async_psycopg_ import AsyncPsycopgConnection
from nexios.orm.dbapi.postgres.asyncpg_ import AsyncPgConnection
from nexios.orm.dbapi.postgres.pg8000_ import Pg8000Connection
from nexios.orm.dbapi.postgres.psycopg_ import PsycopgConnection
from nexios.orm.dbapi.sqlite.aiosqlite_ import AioSQLiteConnection
from nexios.orm.dbapi.sqlite.apsw_ import ApswConnection
from nexios.orm.dbapi.sqlite.sqlite_ import SQLiteConnection
from nexios.orm.pool.base import BaseAsyncConnectionPool, BaseConnectionPool
from nexios.orm.pool.factory import ConnectionPoolFactory


def _excluded_kwargs(**kwargs) -> Dict[str, Any]:
    kwargs_copy = kwargs.copy()

    kwargs_copy.pop('use_pool')
    kwargs_copy.pop('pool_min_size')
    kwargs_copy.pop('pool_max_size')
    return kwargs_copy


class DatabaseManager:
    def __init__(self, url: Optional[str] = None, logger: Optional[logging.Logger] = None, **kwargs: Any):
        self.logger = logger or logging.getLogger(__name__)

        if url:
            self.db_type, self.driver, connection_params = DatabaseDetector.detect_from_url(url, False)
            connection_params.update(kwargs)
            self.connection_params = _excluded_kwargs(**connection_params)
        else:
            self.db_type, self.driver = DatabaseDetector.detect_from_kwargs(kwargs, False)
            self.connection_params = _excluded_kwargs(**kwargs)

        self._connection: Optional[SyncDatabaseConnection] = None
        self._connection_pool: Optional[BaseConnectionPool] = None
        self._use_pool = kwargs.get('use_pool', False)
        self._pool_min_size = kwargs.get('pool_min_size', 1)
        self._pool_max_size = kwargs.get('pool_max_size', 10)

        print(f"Database driver detected: {self.db_type}, {self.driver}, {self.connection_params}")

    def connect(self) -> SyncDatabaseConnection:
        if self._use_pool:
            if self._connection_pool is None:
                self._connection_pool = ConnectionPoolFactory.create_sync_pool(
                    connection=self._create_direct_connection,
                    min_size=self._pool_min_size,
                    max_size=self._pool_max_size,
                    **self.connection_params
                )
            conn = self._connection_pool.get_connection()
            if conn is None:
                raise RuntimeError("Connection pool returned no connection.")
            return conn
        else:
            conn = self._create_direct_connection()
            if conn is None:
                raise RuntimeError("Failed to establish a DB connection.")
            return conn
    
    def _create_direct_connection(self) -> SyncDatabaseConnection:
        
        if isinstance(self.db_type, SQLiteDialect):
            if self.driver == SQLiteDriver.SQLITE3:
                import sqlite3
                raw_conn = sqlite3.connect(**self.connection_params)
                raw_conn.execute("PRAGMA foreign_keys=ON")
                self._connection = SQLiteConnection(raw_conn)
            elif self.driver == SQLiteDriver.APSW:
                import apsw
                raw_conn = apsw.Connection(**self.connection_params)
                raw_conn.execute("PRAGMA foreign_keys=ON")
                self._connection = ApswConnection(raw_conn)
            else:
                raise ValueError(f"Unsupported SQL driver: {self.driver}")
        elif isinstance(self.db_type, PostgreSQLDialect):
            if self.driver == PostgreSQLDriver.PSYCOPG3:
                import psycopg
                raw_conn = psycopg.connect(**self.connection_params)
                self._connection = PsycopgConnection(raw_conn)
            elif self.driver == PostgreSQLDriver.PG8000:
                import pg8000
                import pg8000.dbapi
                raw_conn = pg8000.dbapi.connect(**self.connection_params)
                self._connection = Pg8000Connection(raw_conn)
            else:
                raise ValueError(f"Unsupported Postgres driver: {self.driver}")

        elif isinstance(self.db_type, MySQLDialect):
            if self.driver == MySQLDriver.MYSQL_CONNECTOR:
                import mysql.connector
                mysql_conn = mysql.connector.connect(**self.connection_params)
                self._connection = MySQLConnectorConnection(mysql_conn) # type: ignore
            elif self.driver == MySQLDriver.PYMySQL:
                import pymysql
                raw_conn = pymysql.connect(**self.connection_params)
                self._connection = PyMySQLConnection(raw_conn)
            elif self.driver == MySQLDriver.MARIADB:
                import mariadb

                raw_conn = mariadb.connect(**self.connection_params)
                self._connection = MariaDBConnection(raw_conn)
            elif self.driver == MySQLDriver.MYSQL_CLIENT:
                import MySQLdb

                raw_conn = MySQLdb.connect(**self.connection_params)
                self._connection = MySQLClientConnection(raw_conn)
            else:
                raise ValueError(f"Unsupported MySQL driver: {self.driver}")
        
        return self._connection # type: ignore

    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        if self._use_pool and self._connection_pool:
            self._connection_pool.return_connection(conn)
        else:
            conn.close()


    def cursor(self) -> SyncCursor:
        if self._connection is None:
            print("WARNING: Connection is None, trying to establish connection...")
            self._connection = self.connect()
        
        if self._connection is None:
            raise RuntimeError(
                "Failed to establish a DB connection. "
                f"db_type={self.db_type!r}, driver={self.driver!r}, params={self.connection_params}"
            )
        
        return self._connection.cursor()

    def close(self) -> None:
        if self._connection:
            if not self._use_pool:
                self._connection.close()
            self._connection = None
        
        if self._connection_pool:
            self._connection_pool.close()
            self._connection_pool = None


class AsyncDatabaseManager:
    def __init__(self, url: Optional[str] = None, logger: Optional[logging.Logger] = None, **kwargs: Any):
        self.logger = logger or logging.getLogger(__name__)

        if url:
            self.db_type, self.driver, connection_params = DatabaseDetector.detect_from_url(url, True)
            connection_params.update(kwargs)
            self.connection_params = _excluded_kwargs(**connection_params)
        else:
            self.db_type, self.driver = DatabaseDetector.detect_from_kwargs(kwargs, True)
            self.connection_params = _excluded_kwargs(**kwargs)

        self._connection: Optional[AsyncDatabaseConnection] = None
        self._connection_pool: Optional['BaseAsyncConnectionPool'] = None
        self._use_pool = kwargs.get('use_pool', False)
        self._pool_min_size = kwargs.get('pool_min_size', 1)
        self._pool_max_size = kwargs.get('pool_max_size', 10)

    async def connect(self) -> AsyncDatabaseConnection:
        if self._use_pool:
            if self._connection_pool is None:
                self._connection_pool = ConnectionPoolFactory.create_async_pool(
                    connection=self._create_async_direct_connection,
                    min_size=self._pool_min_size,
                    max_size=self._pool_max_size,
                    **self.connection_params
                )
            return await self._connection_pool.get_connection()
        else:
            return await self._create_async_direct_connection()
        
    async def _create_async_direct_connection(self) -> AsyncDatabaseConnection:
        if isinstance(self.db_type, SQLiteDialect):
            import aiosqlite
            raw_conn = await aiosqlite.connect(**self.connection_params)
            await raw_conn.execute("PRAGMA foreign_keys=ON")
            self._connection = AioSQLiteConnection(raw_conn)
        elif isinstance(self.db_type, PostgreSQLDialect):
            if self.driver == PostgreSQLDriver.PSYCOPG3_ASYNC:
                import psycopg
                raw_conn = await psycopg.AsyncConnection.connect(**self.connection_params)
                self._connection = AsyncPsycopgConnection(raw_conn)
            elif self.driver == PostgreSQLDriver.ASYNCPG:
                from asyncpg import connect

                if 'dbname' in self.connection_params:
                    self.connection_params['database'] = self.connection_params.pop('dbname')
                self.connection_params.pop('sslmode', None)

                raw_conn = await connect(**self.connection_params)
                self._connection = AsyncPgConnection(raw_conn)
            elif self.driver == PostgreSQLDriver.AIOPG:
                import aiopg
                raw_conn = await aiopg.connect(**self.connection_params)
                self._connection = AioPgConnection(raw_conn)
            else:
                raise ValueError(f"Unsupported Postgres driver: {self.driver}")

        elif isinstance(self.db_type, MySQLDialect):
            if self.driver == MySQLDriver.AIOMYSQL:

                if 'database' in self.connection_params:
                    self.connection_params['db'] = self.connection_params.pop('database')

                raw_conn = await aiomysql.connect(**self.connection_params)
                self._connection = MySQLAioMySQLConnection(raw_conn)
                
            elif self.driver == MySQLDriver.ASYNCMY:
                import asyncmy

                raw_conn = await asyncmy.connect(**self.connection_params)
                self._connection = AsyncMyConnection(raw_conn)
            else:
                raise ValueError(f"Unsupported MySQL driver: {self.driver}")
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        return self._connection
    
    async def return_connection(self, conn: AsyncDatabaseConnection):
        if self._use_pool and self._connection_pool:
            await self._connection_pool.return_connection(conn)
        else:
            await conn.close()

    async def cursor(self) -> AsyncCursor:
        # if not self._connection:
        #     self._connection = await self.connect()
        # cursor = await self._connection.cursor()
        # return cursor
        if self._connection is None:
            print("WARNING: Connection is None, trying to establish connection...")
            self._connection = await self.connect()

        if self._connection is None:
            raise RuntimeError(
                "Failed to establish a DB connection. "
                f"db_type={self.db_type!r}, driver={self.driver!r}, params={self.connection_params}"
            )
        return await self._connection.cursor()


    async def close(self) -> None:
        if self._connection:
            if not self._use_pool:
                await self._connection.close()
            self._connection = None
        
        if self._connection_pool:
            await self._connection_pool.close()
            self._connection_pool = None
