from typing import Any, List, Optional, Tuple
import asyncpg
import asyncpg.cursor
from nexios.orm.connection import AsyncCursor, AsyncDatabaseConnection


class AsyncPgCursor(AsyncCursor):
    def __init__(self, cursor: asyncpg.cursor.Cursor, connection: asyncpg.connection.Connection):
        self._cursor = cursor
        self._conn = connection
    
    @property
    def description(self) -> Any:
        return None
    
    @property
    def rowcount(self) -> int:
        return -1  # asyncpg does not provide rowcount directly
    
    @property
    def raw_connection(self) -> asyncpg.connection.Connection:
        return self._conn

    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> Any:
        return await self._conn.execute(sql, *parameters)

    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any:
        return await self._conn.executemany(sql, seq_of_parameters)

    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = await self._cursor.fetchrow()
        return tuple(row) if row else None

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetch(100)
        return [tuple(row) for row in rows] if rows else []

    async def fetchmany(self, size: int = -1) -> List[Tuple[Any, ...]]:
        rows = await self._conn.fetch(size)
        return [tuple(row) for row in rows] if rows else []
    
class AsyncPgConnection(AsyncDatabaseConnection):
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection

    async def cursor(self) -> AsyncPgCursor:
        cursor = await self._connection.cursor("SELECT 1")
        return AsyncPgCursor(cursor, self._connection)

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        await self._connection.close()
    
    @property
    def raw_connection(self) -> asyncpg.Connection:
        return self._connection