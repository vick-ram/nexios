from typing import Any, List, Optional, Tuple

import aiomysql
from nexios.orm.connection import AsyncCursor, AsyncDatabaseConnection, AsyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class MySQLAioMySQLCursor(AsyncCursor):
    def __init__(self, cursor: aiomysql.Cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> AsyncQueryResult:
        await self._cursor.execute(sql, parameters)
        last_id = self._cursor.lastrowid
        setattr(AsyncQueryResult, 'last_id', last_id)
        return AsyncQueryResult(self)

    async def executemany(
        self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]
    ) -> AsyncQueryResult:
        await self._cursor.executemany(sql, seq_of_parameters)
        return AsyncQueryResult(self)

    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = await self._cursor.fetchone() # type: ignore
        return convert_row(row)

    async def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchmany(size) # type: ignore
        return convert_rows(rows)

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchall() # type: ignore
        return convert_rows(rows)

class MySQLAioMySQLConnection(AsyncDatabaseConnection):
    def __init__(self, connection: aiomysql.Connection) -> None:
        self._connection = connection

    async def cursor(self) -> MySQLAioMySQLCursor:
        raw_cursor = self._connection.cursor()
        cur = await raw_cursor.__aenter__()
        return MySQLAioMySQLCursor(cur)

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()

    async def close(self) -> None:
        self._connection.close()
    
    @property
    def raw_connection(self) -> aiomysql.Connection:
        return self._connection
    
    @property
    def is_connection_open(self) -> bool:
        return not self._connection.closed
    
