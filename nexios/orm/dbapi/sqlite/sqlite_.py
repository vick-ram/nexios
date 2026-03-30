import sqlite3
from typing import Any, List, Optional, Tuple

from nexios.orm.connection import SyncCursor, SyncDatabaseConnection, SyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class SQLiteCursor(SyncCursor):
    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cursor = cursor
    
    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> SyncQueryResult:
        self._cursor.execute(sql, parameters)
        return SyncQueryResult(self)
    
    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> SyncQueryResult:
        self._cursor.executemany(sql, seq_of_parameters)
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


class SQLiteConnection(SyncDatabaseConnection):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def cursor(self) -> SyncCursor:
        cursor = self._connection.cursor()
        return SQLiteCursor(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()
    
    @property
    def raw_connection(self) -> sqlite3.Connection:
        return self._connection
    
    @property
    def is_connection_open(self) -> bool:
        try:
            stmt = "SELECT 1"
            self._connection.execute(stmt)
            return True
        except sqlite3.ProgrammingError:
            return False