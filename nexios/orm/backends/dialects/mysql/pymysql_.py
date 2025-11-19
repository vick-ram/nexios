from typing import Any, Optional, Tuple, List

import pymysql
from nexios.orm.connection import SyncCursor, SyncDatabaseConnection


class PyMySQLCursor(SyncCursor):
    def __init__(self, cursor: pymysql.cursors.Cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> Any:
        return self._cursor.execute(sql, parameters)
    
    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any:
        return self._cursor.executemany(sql, seq_of_parameters)
    
    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return tuple(row)
    
    def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchall()
        return [tuple(row) for row in rows]
    
    def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchmany(size)
        return [tuple(row) for row in rows]

class PyMySQLConnection(SyncDatabaseConnection):
    def __init__(self, connection: pymysql.Connection) -> None:
        self._connection = connection

    def cursor(self) -> SyncCursor:
        cursor = self._connection.cursor()
        return PyMySQLCursor(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()
    
    @property
    def raw_connection(self) -> pymysql.Connection:
        return self._connection