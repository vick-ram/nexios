from typing_extensions import Any, Optional, cast
from nexios.orm.backends.config import DatabaseDetector, DatabaseDialect, MySQLDriver, PostgreSQLDriver
from nexios.orm.backends.dialects.postgres.base import PostgresConnection
from nexios.orm.backends.dialects.postgres.psycopg2_ import Psycopg2Connection
from nexios.orm.backends.dialects.sqlite.sqlite_ import SQLiteConnection
from nexios.orm.connection import (
    AsyncCursor,
    AsyncDatabaseConnection,
    SyncCursor,
    SyncDatabaseConnection,
)

# if TYPE_CHECKING:
# from nexios.orm.backends.types import DatabaseDialect

class DatabaseManager:
    def __init__(self, url: Optional[str] = None, **kwargs: Any):
        if url:
            self.db_type, self.driver, connection_params = DatabaseDetector.detect_from_url(url)
            connection_params.update(kwargs)
            self.connection_params = connection_params
        else:
            self.db_type, self.driver = DatabaseDetector.detect_from_kwargs(kwargs)
            self.connection_params = kwargs

        self._connection: Optional[SyncDatabaseConnection] = None

    def connect(self) -> SyncDatabaseConnection:
        if self.db_type == DatabaseDialect.SQLITE:
            import sqlite3
            raw_conn = sqlite3.connect(**self.connection_params)
            self._connection = SQLiteConnection(raw_conn)
        elif self.db_type == DatabaseDialect.POSTGRES:
            if self.driver == PostgreSQLDriver.PSYCOPG2:
                import psycopg2
                raw_conn = psycopg2.connect(**self.connection_params)
                self._connection = Psycopg2Connection()
            elif self.driver == PostgreSQLDriver.PSYCOPG3:
                import psycopg
                raw_conn = psycopg.connect(**self.connection_params)
            elif self.driver == PostgreSQLDriver.PG8000:
                import pg8000
                raw_conn = pg8000.connect(**self.connection_params)
            else:
                raise ValueError(f"Unsupported Postgres driver: {self.driver}")
            
            self._connection = PostgresConnection(raw_conn, )

        elif self.db_type == DatabaseDialect.MYSQL:
            from mysql.connector.connection import MySQLConnection
            if self.driver == MySQLDriver.MYSQL_CONNECTOR:
                import mysql.connector
                raw_conn = mysql.connector.connect(**self.connection_params)
            elif self.driver == MySQLDriver.PYMySQL:
                import pymysql
                raw_conn = pymysql.connect(**self.connection_params)
            else:
                raise ValueError(f"Unsupported MySQL driver: {self.driver}")
            
            typed_conn = cast(MySQLConnection, raw_conn)
            self._connection = MySQLConnectionWrapper(typed_conn)


        return self._connection  # type: ignore

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
            self.db_type, self.driver, connection_params = DatabaseDetector.detect_from_url(url)
            connection_params.update(kwargs)
            self.connection_params = connection_params
        else:
            self.db_type, self.driver = DatabaseDetector.detect_from_kwargs(kwargs)
            self.connection_params = kwargs

        self._connection: Optional[AsyncDatabaseConnection] = None

    async def connect(self) -> AsyncDatabaseConnection:
        if self.db_type == DatabaseDialect.SQLITE:
            from aiosqlite import connect

            raw_conn = await connect(**self.connection_params)
            self._connection = AsyncSQLiteConnectionWrapper(raw_conn)
        elif self.db_type == DatabaseDialect.POSTGRES:
            if self.driver == PostgreSQLDriver.PSYCOPG3:
                import psycopg
                raw_conn = await psycopg.AsyncConnection.connect(**self.connection_params)
            elif self.driver == PostgreSQLDriver.ASYNCPG:
                from asyncpg import connect
                raw_conn = await connect(**self.connection_params)
            else:
                raise ValueError(f"Unsupported Postgres driver: {self.driver}")
            self._connection = AsyncPostgreSQLConnectionWrapper(raw_conn)
        elif self.db_type == DatabaseDialect.MYSQL:
            if self.driver == "aiomysql":
                from aiomysql import create_pool

                pool = await create_pool(**self.connection_params)
                self._connection = AsyncMySQLConnectionWrapper(pool)
            else:
                raise ValueError(f"Unsupported MySQL driver: {self.driver}")
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        return self._connection  # type: ignore

    async def cursor(self) -> AsyncCursor:
        if not self._connection:
            await self.connect()
        cursor = await self._connection.cursor()  # type: ignore
        return cast(AsyncCursor, cursor)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
