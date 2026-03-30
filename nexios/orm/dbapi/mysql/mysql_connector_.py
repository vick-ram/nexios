from typing import Any, List, Optional, Tuple

import mysql.connector
import mysql.connector.cursor

from nexios.orm.connection import SyncCursor, SyncDatabaseConnection, SyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class MySQLConnectorCursor(SyncCursor):
    def __init__(self, cursor: mysql.connector.cursor.MySQLCursor) -> None:
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
        return  convert_row(row)
    def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchall()
        return convert_rows(rows)
    
    def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = self._cursor.fetchmany(size)
        return convert_rows(rows)

class MySQLConnectorConnection(SyncDatabaseConnection):
    def __init__(self, connection: mysql.connector.connection.MySQLConnection) -> None:
        self._connection = connection

    def cursor(self) -> SyncCursor:
        cursor = self._connection.cursor()
        return MySQLConnectorCursor(cursor) # type: ignore

    def begin(self):
        self._connection

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()
    
    @property
    def raw_connection(self) -> mysql.connector.connection.MySQLConnection:
        return self._connection
    
    @property
    def is_connection_open(self) -> bool:
        return self._connection.is_connected()