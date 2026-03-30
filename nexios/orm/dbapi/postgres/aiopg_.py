from __future__ import annotations

from typing import Any, List, Tuple, Optional

import aiopg

from nexios.orm.connection import AsyncQueryResult, AsyncCursor, AsyncDatabaseConnection
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class AioPgCursor(AsyncCursor):
    def __init__(self, cursor: aiopg.Cursor):
        self.cursor = cursor

    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> AsyncQueryResult:
        await self.cursor.execute(sql, parameters)
        return AsyncQueryResult(self)

    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> AsyncQueryResult:
        await self.cursor.executemany()
        return AsyncQueryResult(self)

    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = await self.cursor.fetchone()
        return convert_row(row)

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = await self.cursor.fetchall()
        return convert_rows(rows)

    async def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = await self.cursor.fetchmany(size)
        return convert_rows(rows)

    @property
    def description(self) -> Any:
        return self.cursor.description

    @property
    def rowcount(self) -> int:
        return self.cursor.rowcount

class AioPgConnection(AsyncDatabaseConnection):
    def __init__(self, connection: aiopg.Connection):
        self.connection = connection

    async def cursor(self) -> AsyncCursor:
        return AioPgCursor(self.connection.cursor_factory)

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
        return not self.connection.closed