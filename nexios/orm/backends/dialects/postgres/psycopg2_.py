from typing import Any, List, Optional, Tuple, cast

import psycopg2

from nexios.orm.connection import SyncCursor, SyncDatabaseConnection


class Psycopg2Cursor(SyncCursor):
    def __init__(self, cursor: psycopg2.extensions.cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> Any:
        sql_to_execute = cast(str, sql)
        return self._cursor.execute(sql_to_execute, parameters)
    
    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any:
        sql_to_execute = cast(str, sql)
        return self._cursor.executemany(sql_to_execute, seq_of_parameters)
    
    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = self._cursor.fetchone()
        return tuple(row) if row else None

    def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchall()
        return [tuple(row) for row in rows] if rows else []
    
    def fetchmany(self, size: int = -1) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchmany(size)
        return [tuple(row) for row in rows] if rows else []

class Psycopg2Connection(SyncDatabaseConnection):
    def __init__(self, connection: psycopg2.extensions.connection) -> None:
        self._connection = connection

    def cursor(self) -> Psycopg2Cursor:
        raw_cursor = self._connection.cursor()
        return Psycopg2Cursor(raw_cursor)
    
    def commit(self) -> None:
        self._connection.commit()
    
    def rollback(self) -> None:
        self._connection.rollback()