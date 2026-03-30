from __future__ import annotations

import asyncmy
from typing import List, Tuple, Any

import asyncmy.cursors
from nexios.orm.connection import AsyncDatabaseConnection, AsyncCursor, AsyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class AsyncMyConnection(AsyncDatabaseConnection):
    def __init__(self, connection: asyncmy.Connection):
        self.connection = connection

    async def cursor(self) -> AsyncCursor:
        return AsyncMyCursor(self.connection.cursor())

    async def commit(self) -> None:
        await self.connection.commit()

    async def rollback(self) -> None:
        await self.connection.rollback()

    async def close(self) -> None:
        await self.connection.close()

    @property
    def raw_connection(self) -> Any:
        return self.connection

    @property
    def is_connection_open(self) -> bool:
        return self.connection

class AsyncMyCursor(AsyncCursor):
    def __init__(self, cursor: asyncmy.cursors.Cursor) -> None:
        self._cursor = cursor
    
    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> AsyncQueryResult:
        await self._cursor.execute(sql, parameters)
        return AsyncQueryResult(self)
    
    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> AsyncQueryResult:
        await self._cursor.executemany(sql, seq_of_parameters)
        return AsyncQueryResult(self)
    
    async def fetchone(self) -> Tuple[Any] | None:
        row = await self._cursor.fetchone()
        return convert_row(row)
    
    async def fetchall(self) -> List[Tuple[Any]]:
        rows = await self._cursor.fetchall()
        return convert_rows(rows)
    
    async def fetchmany(self, size: int = 1) -> List[Tuple[Any]]:
        rows = await self._cursor.fetchmany(size)
        return convert_rows(rows)
    
    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount
