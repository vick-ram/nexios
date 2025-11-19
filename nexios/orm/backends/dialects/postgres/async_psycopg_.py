from typing import Any, List, Optional, Tuple, cast, LiteralString
import psycopg

from nexios.orm.connection import AsyncCursor, AsyncDatabaseConnection

class AsyncPsycopgCursor(AsyncCursor):
    def __init__(self, cursor: psycopg.AsyncCursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> Any:
        sql_to_execute = cast(LiteralString, sql)
        return await self._cursor.execute(sql_to_execute, *parameters)

    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any:
        sql_to_execute = cast(LiteralString, sql)
        return await self._cursor.executemany(sql_to_execute, seq_of_parameters)

    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = await self._cursor.fetchone()
        return tuple(row) if row else None

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchall()
        return [tuple(row) for row in rows] if rows else []

    async def fetchmany(self, size: int = -1) -> List[Tuple[Any, ...]]:
        rows = await self._cursor.fetchmany(size)
        return [tuple(row) for row in rows] if rows else []

class AsyncPsycopgConnection(AsyncDatabaseConnection):
    def __init__(self, connection: psycopg.AsyncConnection) -> None:
        self._connection = connection

    async def cursor(self) -> AsyncPsycopgCursor:
        raw_cursor = self._connection.cursor()
        return AsyncPsycopgCursor(raw_cursor)

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()
    
    async def close(self) -> None:
        await self._connection.close()
    
    @property
    def raw_connection(self) -> psycopg.AsyncConnection:
        return self._connection