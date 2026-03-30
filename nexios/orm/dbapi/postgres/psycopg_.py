from typing import Any, Tuple, List, Optional, LiteralString, cast

import psycopg

from nexios.orm.connection import SyncCursor, SyncDatabaseConnection, SyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class PsycopgCursor(SyncCursor):
    def __init__(self, cursor: psycopg.cursor.Cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> SyncQueryResult:
        sql_to_execute = cast(LiteralString, sql)
        self._cursor.execute(sql_to_execute, parameters)
        return SyncQueryResult(self)
    
    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> SyncQueryResult:
        sql_to_execute = cast(LiteralString, sql)
        self._cursor.executemany(sql_to_execute, seq_of_parameters)
        return SyncQueryResult(self)
    
    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = self._cursor.fetchone()
        return convert_row(row)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchall()
        return convert_rows(rows)
    
    def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchmany(size)
        return convert_rows(rows)

class PsycopgConnection(SyncDatabaseConnection):
    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def cursor(self) -> SyncCursor:
        raw_cursor = self._connection.cursor()
        return PsycopgCursor(raw_cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()
    
    def close(self) -> None:
        self._connection.close()
    
    @property
    def raw_connection(self) -> psycopg.Connection:
        return self._connection
    
    @property
    def is_connection_open(self) -> bool:
        return not self._connection.closed
    
