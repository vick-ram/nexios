from typing import Any, List, Optional, Tuple, cast

import aiosqlite

from nexios.orm.connection import AsyncCursor, AsyncDatabaseConnection

class AioSQLiteCursor(AsyncCursor):
    def __init__(self, cursor: aiosqlite.Cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> Any:
        return await self._cursor.execute(sql, parameters)
    
    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any:
        return await self._cursor.executemany(sql, seq_of_parameters)
    
    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = await self._cursor.fetchone()
        if row is None:
            return None
        return tuple(row)
    
    async def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchall()
        return [tuple(row) for row in rows]
    
    async def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchmany(size)
        return [tuple(row) for row in rows]
    

class AioSQLiteConnection(AsyncDatabaseConnection):
    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._connection = connection

    async def cursor(self) -> AsyncCursor:
        cursor = await self._connection.cursor()
        return AioSQLiteCursor(cursor)

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()

    async def close(self) -> None:
        await self._connection.close()