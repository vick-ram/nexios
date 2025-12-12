from typing import Any, Optional, Tuple, List
import pg8000
import pg8000.dbapi
from nexios.orm.connection import SyncCursor, SyncDatabaseConnection


class Pg8000Cursor(SyncCursor):
    def __init__(self, cursor: pg8000.dbapi.Cursor):
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
        return tuple(row) if row else None

    def fetchall(self) -> List[Tuple[Any, ...]]:
        return [tuple(row) for row in self._cursor.fetchall()]

    def fetchmany(self, size: int = -1) -> List[Tuple[Any, ...]]:
        return [tuple(row) for row in self._cursor.fetchmany(size)]

class Pg8000Connection(SyncDatabaseConnection):
    def __init__(self, connection: pg8000.dbapi.Connection):
        self._connection = connection

    def cursor(self) -> Pg8000Cursor:
        cursor = self._connection.cursor()
        return Pg8000Cursor(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()
    
    @property
    def raw_connection(self) -> pg8000.dbapi.Connection:
        return self._connection
    
    @property
    def is_connection_open(self) -> bool:
        # return not self._connection.closed
        try:
            stmt = "SELECT 1"
            cur = self._connection.cursor()
            cur.execute(stmt)
            return True
        except pg8000.dbapi.InterfaceError:
            return False