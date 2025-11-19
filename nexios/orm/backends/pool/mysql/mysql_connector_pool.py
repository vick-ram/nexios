from typing import Any, Set, List, Dict
from nexios.orm.backends.dialects.mysql.mysql_connector_ import MySQLConnectorConnection
from nexios.orm.connection import SyncDatabaseConnection
from nexios.orm.backends.pool.base import BaseConnectionPool

class MySQLConnectorPool(BaseConnectionPool):
    def __init__(self, min_size: int = 1, max_size: int = 5, **kwargs) -> None:
        self.kwargs = kwargs
        self.min_size = min_size
        self.max_size = max_size

        self._raw_pool = self._create_raw_pool()

        # Tracck our wrapper connections
        self._wrapper_pool: List[SyncDatabaseConnection] = []
        self._in_use: Set[SyncDatabaseConnection] = set()

    def _create_raw_pool(self):
        try:
            import mysql.connector.pooling
        except ImportError:
            raise ImportError(
                "mysql-connector is required for MySQLConnector connection pooling"
            )

        connection_kwargs = self._get_connection_kwargs()
        return mysql.connector.pooling.MySQLConnectionPool(
            pool_name="nexios", pool_size=self.max_size, **connection_kwargs
        )

    def _get_connection_kwargs(self) -> Dict[str, Any]:
        kwargs = self.kwargs.copy()
        kwargs.pop("driver", None)
        kwargs.pop("min_size", None)
        kwargs.pop("max_size", None)
        kwargs.pop("pool_size", None)
        return kwargs

    def _wrap_connection(self, raw_conn: Any) -> SyncDatabaseConnection:
        return MySQLConnectorConnection(raw_conn)

    def get_connection(self) -> SyncDatabaseConnection:
        raw_conn = self._raw_pool.get_connection()
        wrapper_conn = self._wrap_connection(raw_conn)

        # store raw connection so we can return it later
        setattr(wrapper_conn, "_pool", self)
        setattr(wrapper_conn, "_raw_connection", raw_conn)

        self._in_use.add(wrapper_conn)
        return wrapper_conn

    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        if conn in self._in_use and hasattr(conn, "_raw_connection"):  # type: ignore
            self._in_use.remove(conn)
            # Return the raw connection to psycopg2's pool
            _raw_connection = getattr(conn, "_raw_connection")
            # self._raw_pool.putconn(_raw_connection)
            self._raw_pool.add_connection(_raw_connection)
            # Clean up references
            delattr(conn, "_pool")
            delattr(conn, "_raw_connection")

    def close(self) -> None:
        """Close all connections in the pool"""
        self._raw_pool._remove_connections()  # Try to change
        self._in_use.clear()
        self._wrapper_pool.clear()

    @property
    def size(self) -> int:
        return len(self._in_use)

    @property
    def available(self) -> int:
        return max(0, self.max_size - len(self._in_use))
