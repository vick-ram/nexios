from __future__ import annotations

from typing import Any, List, Tuple, Optional
import mariadb.connections
from nexios.orm.connection import SyncDatabaseConnection, SyncCursor, SyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class MariaDBConnection(SyncDatabaseConnection):
    def __init__(self, conn: mariadb.connections.Connection):
        self.connection = conn

    def cursor(self) -> SyncCursor:
        return MariaDBCursor(self.connection.cursor())

    def begin(self):
        self.connection.begin()

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

class MariaDBCursor(SyncCursor):
    def __init__(self, cur: mariadb.Cursor):
        self.cur = cur

    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> SyncQueryResult:
        self.cur.execute(sql, parameters)
        return SyncQueryResult(self)

    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> SyncQueryResult:
        self.cur.executemany(sql, seq_of_parameters)
        return SyncQueryResult(self)

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = self.cur.fetchone()
        return convert_row(row)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = self.cur.fetchall()
        return convert_rows(rows)

    def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = self.cur.fetchmany(size)
        return convert_rows(rows)

    @property
    def description(self) -> Any:
        return self.cur._description

    @property
    def rowcount(self) -> int:
        return self.cur.rowcount