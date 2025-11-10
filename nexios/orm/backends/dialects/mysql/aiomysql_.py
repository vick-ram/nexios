from typing import Any, List, Optional, Tuple
import aiomysql
from nexios.orm.connection import AsyncCursor, AsyncDatabaseConnection


class MySQLAioMySQLCursor(AsyncCursor):
    def __init__(self, cursor: aiomysql.Cursor) -> None:
        self._cursor = cursor

    async def _convert_row(self, row: Any) -> Optional[Tuple[Any, ...]]:
        if row is None:
            return None
        if isinstance(row, tuple):
            return row
        return (
            tuple(row)
            if hasattr(row, "__iter__") and not isinstance(row, (str, bytes))
            else (row,)
        )

    @property
    def description(self) -> Any:
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> Any:
        return await self._cursor.execute(sql, parameters)

    async def executemany(
        self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]
    ) -> Any:
        return await self._cursor.executemany(sql, seq_of_parameters)

    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = await self._cursor.fetchone()
        return await self._convert_row(row)

    async def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchmany(size)
        return [
            converted_row
            for row in rows
            if (converted_row := await self._convert_row(row)) is not None
        ]

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchall()
        return [
            converted_row
            for row in rows
            if (converted_row := await self._convert_row(row)) is not None
        ]


class MySQLAioMySQLConnection(AsyncDatabaseConnection):
    def __init__(self, connection: aiomysql.Connection) -> None:
        self._connection = connection

    async def cursor(self) -> MySQLAioMySQLCursor:
        raw_cursor = await self._connection.cursor()
        return MySQLAioMySQLCursor(raw_cursor)

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()

    async def close(self) -> None:
        self._connection.close()
