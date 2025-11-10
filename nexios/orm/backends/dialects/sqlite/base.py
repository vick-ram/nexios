import sqlite3
from typing import Any, Optional

import aiosqlite

from nexios.orm.connection import SyncDatabaseConnection, AsyncDatabaseConnection

class BaseSQLiteConnection:

    @staticmethod
    def connection(conn: Any) -> Optional["SyncDatabaseConnection"]:
        from nexios.orm.backends.dialects.sqlite.sqlite_ import SQLiteConnection
        if isinstance(conn, sqlite3.Connection):
            return SQLiteConnection(conn)
        return None
    
    @staticmethod
    async def connect_async(conn: Any) -> Optional["AsyncDatabaseConnection"]:
        from nexios.orm.backends.dialects.sqlite.aiosqlite_ import AioSQLiteConnection
        if isinstance(conn, aiosqlite.Connection):
            return AioSQLiteConnection(conn)
        return None