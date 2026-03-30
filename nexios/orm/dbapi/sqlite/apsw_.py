from __future__ import annotations

import apsw
from typing import Any, List, Tuple, Optional

from nexios.orm.connection import SyncDatabaseConnection, SyncCursor, SyncQueryResult
from nexios.orm.misc.row_to_tuple import convert_row, convert_rows


class ApswConnection(SyncDatabaseConnection):
    def __init__(self, conn: apsw.Connection) -> None:
        self.connection = conn
        self.__cursor = self.connection.cursor()

    def cursor(self) -> SyncCursor:
        return ApswCursor(self.connection.cursor())

    def commit(self) -> None:
        self.__cursor.execute("COMMIT")

    def rollback(self) -> None:
        self.__cursor.execute("ROLLBACK")

    def close(self) -> None:
        self.connection.close()

    @property
    def raw_connection(self) -> Any:
        return self.connection

    @property
    def is_connection_open(self) -> bool:
        return self.connection is not None


class ApswCursor(SyncCursor):
    def __init__(self, cur: apsw.Cursor):
        self.cursor = cur

    def execute(self, sql: str, parameters: Tuple[Any, ...] = ()) -> SyncQueryResult:
        self.cursor.execute("BEGIN").execute(sql, parameters)
        return SyncQueryResult(self)

    def executemany(
        self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]
    ) -> SyncQueryResult:
        self.cursor.execute("BEGIN").executemany(
            statements=sql, sequenceofbindings=seq_of_parameters
        )
        return SyncQueryResult(self)

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        row = self.cursor.fetchone()
        return convert_row(row)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        rows = self.cursor.fetchall()
        return convert_rows(rows)

    def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        rows = []
        while True:
            for _ in range(size):
                row = self.cursor.fetchone()
                if row is None:
                    break
                rows.append(row)
            if not rows:
                break
        return convert_rows(rows)

    @property
    def description(self) -> Any:
        return self.cursor.description

    @property
    def rowcount(self) -> int:
        return self.cursor.bindings_count
