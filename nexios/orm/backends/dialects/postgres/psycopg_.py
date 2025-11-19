from typing import Any, Tuple, List, Optional, LiteralString, cast
import psycopg
from nexios.orm.connection import SyncCursor, SyncDatabaseConnection


class PsycopgCursor(SyncCursor):
    def __init__(self, cursor: psycopg.cursor.Cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> Any:
        sql_to_execute = cast(LiteralString, sql)
        return self._cursor.execute(sql_to_execute, parameters)
    
    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any:
        sql_to_execute = cast(LiteralString, sql)
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
    
