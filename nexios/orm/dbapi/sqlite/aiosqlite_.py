from typing import Any, List, Optional, Tuple

import aiosqlite

from nexios.orm.connection import AsyncCursor, AsyncDatabaseConnection, AsyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class AioSQLiteCursor(AsyncCursor):
    def __init__(self, cursor: aiosqlite.Cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> AsyncQueryResult:
        await self._cursor.execute(sql, parameters)
        return AsyncQueryResult(self)
    
    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> AsyncQueryResult:
        await self._cursor.executemany(sql, seq_of_parameters)
        return AsyncQueryResult(self)
    
    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = await self._cursor.fetchone()
        return convert_row(row)
    
    async def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchall()
        return convert_rows(rows)
    
    async def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchmany(size)
        return convert_rows(rows)
    

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
    
    @property
    def raw_connection(self) -> aiosqlite.Connection:
        return self._connection
    
    @property
    async def is_connection_open(self) -> bool:
        try:
            stmt = "SELECT 1"
            await self._connection.execute(stmt)
            return True
        except aiosqlite.ProgrammingError:
            return False