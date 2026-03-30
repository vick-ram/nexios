from __future__ import annotations

from typing import Any, List, Optional, Tuple

import asyncpg
import asyncpg.cursor

from nexios.orm.connection import AsyncCursor, AsyncDatabaseConnection, AsyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class AsyncPgCursor(AsyncCursor):
    def __init__(self, connection: AsyncPgConnection):
        self._conn = connection
        self._result: Optional[List[asyncpg.Record]] = None
        self._position: int = 0
        self._description: Optional[List[Tuple]] = None
        self._in_transaction: bool = False
    
    @property
    def description(self) -> Any:
        # return None
        if self._description is None:
            return None
        return self._description
    
    @property
    def rowcount(self) -> int:
        # return -1
        if self._result is None:
            return -1
        return len(self._result)

    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> AsyncQueryResult:
        self._result = None
        self._position = 0

        if hasattr(self._conn, '_ensure_transaction'):
            await self._conn._ensure_transaction()

        try:
            self._result = await self._conn.raw_connection.fetch(sql, *parameters)
            if self._result:
                first_record = self._result[0]
                self._description = [
                    (key, type(value).__module__, None, None, None, None)
                    for key, value in first_record.items()
                ]
            else:
                self._description = []
            return AsyncQueryResult(self)
        except asyncpg.exceptions.PostgresError as e:
            self._result = None
            self._description = None
            raise e
        except Exception as e:
            raise e

    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> AsyncQueryResult:
        await self._conn.raw_connection.executemany(sql, seq_of_parameters)
        self._result = None
        self._description = None
        self._position = 0
        return AsyncQueryResult(self)

    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self._result is None:
            raise RuntimeError("No query has been executed yet. Call execute() first.")

        if self._position >= len(self._result):
            return None

        row = self._result[self._position]
        self._position += 1
        return convert_row(row)

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        if self._result is None:
            raise RuntimeError("No query has been executed yet. Call execute() first.")

        rows = self._result[self._position:]
        self._position = len(self._result)
        return convert_rows(rows)

    async def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        if self._result is None:
            raise RuntimeError("No query has been executed yet. Call execute() first.")

        end_pos = min(self._position + size, len(self._result))
        rows = self._result[self._position:end_pos]
        self._position = end_pos
        return convert_rows(rows)
    
class AsyncPgConnection(AsyncDatabaseConnection):
    def __init__(self, connection: asyncpg.Connection):
        from asyncpg.transaction import Transaction

        self._connection = connection
        self._transaction:Optional[Transaction] = None
        self._transaction_depth: int = 0
        self._auto_start_transaction = True

    async def _ensure_transaction(self):
        if self._auto_start_transaction and self._transaction_depth == 0:
            self._transaction = self._connection.transaction()
            await self._transaction.start()
            self._transaction_depth += 1

    async def cursor(self) -> AsyncPgCursor:
        return AsyncPgCursor(self)

    async def commit(self) -> None:
        if self._transaction_depth <= 0:
            return

        self._transaction_depth -= 1
        if self._transaction_depth == 0 and self._transaction:
            await self._transaction.commit()
            self._transaction = None

    async def rollback(self) -> None:
        if self._transaction_depth <= 0:
            return

        self._transaction_depth -= 1
        if self._transaction_depth == 0 and self._transaction:
            await self._transaction.rollback()
            self._transaction = None

    async def close(self) -> None:
        if self._transaction_depth > 0 and self._transaction:
            await self._transaction.rollback()
        await self._connection.close()
    
    @property
    def raw_connection(self) -> asyncpg.Connection:
        return self._connection
    
    @property
    def is_connection_open(self) -> bool:
        return not self._connection.is_closed()