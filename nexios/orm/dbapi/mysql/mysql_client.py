from __future__ import annotations

from typing import Any, List, LiteralString, Tuple, Optional, cast
from nexios.orm.connection import SyncDatabaseConnection, SyncCursor, SyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_rows, convert_row


class MySQLClientConnection(SyncDatabaseConnection):

    def __init__(self, conn: Any):
        self.connection = conn

    def cursor(self) -> SyncCursor:
        return MySQLClientCursor(self.connection.cursor())

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()

    @property
    def raw_connection(self) -> Any:
        return self.connection

    @property
    def is_connection_open(self) -> bool:
        return self.connection.open


class MySQLClientCursor(SyncCursor):

    def __init__(self, cur: Any):
        self.cursor = cur

    @property
    def rowcount(self) -> int:
        return self.cursor.rowcount

    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> SyncQueryResult:
        self.cursor.execute(sql, parameters)
        return SyncQueryResult(self)

    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> SyncQueryResult:
        self.cursor.executemany(cast(LiteralString, sql), seq_of_parameters)
        return SyncQueryResult(self)

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = self.cursor.fetchone()
        return convert_row(row)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = self.cursor.fetchall()
        return convert_rows(rows)

    def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = self.cursor.fetchmany(size)
        return convert_rows(rows)

    @property
    def description(self) -> Any:
        return self.cursor.description
