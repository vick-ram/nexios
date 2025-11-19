import threading
from typing import List
import pg8000.dbapi
import pg8000.native
from nexios.orm.backends.dialects.postgres.base import PostgresConnection
from nexios.orm.backends.pool.base import BaseConnectionPool
from nexios.orm.connection import SyncDatabaseConnection


class Pg8000ConnectionPool(BaseConnectionPool):
    """
    A connection pool for pg8000 connections.
    """

    def __init__(self, min_connections: int = 1, max_connections: int = 10, **kwargs):
        self._min_connections = min_connections
        self._max_connections = max_connections
        self._kwargs = kwargs

        self._pool: List[SyncDatabaseConnection] = []
        self._used_connections: List[SyncDatabaseConnection] = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

        self._initialize_pool()

    def _initialize_pool(self):
        for _ in range(self._min_connections):
            self._pool.append(self._create_new_connection())

    def _create_new_connection(self) -> SyncDatabaseConnection:
        raw_conn = pg8000.dbapi.connect(**self._kwargs)
        return PostgresConnection.connect(raw_conn) # type: ignore


    def get_connection(self) -> SyncDatabaseConnection:
        with self._condition:
            while not self._pool and len(self._used_connections) >= self._max_connections:
                self._condition.wait()

            if self._pool:
                conn = self._pool.pop()
            else:
                raw_conn = self._create_new_connection()
                conn = PostgresConnection.connect(raw_conn)
            self._used_connections.append(conn) # type: ignore
            return conn # type: ignore
    
    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        with self._condition:
            try:
                self._used_connections.remove(conn)
                self._pool.append(conn)
            except ValueError:
                pass  # Connection was not in used_connections
            finally:
                self._condition.notify_all()
    
    def close(self) -> None:
        with self._lock:
            for conn in self._pool + self._used_connections:
                try:
                    conn.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")
            self._pool.clear()
            self._used_connections.clear()
    
    @property
    def size(self) -> int:
        return len(self._pool) + len(self._used_connections)
    
    @property
    def available(self) -> int:
        return len(self._pool)