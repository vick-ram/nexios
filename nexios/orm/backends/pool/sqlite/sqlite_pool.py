import queue
import sqlite3
import threading
from typing import Dict, Set, Any, cast
from nexios.orm.backends.pool.base import BaseConnectionPool
from nexios.orm.connection import SyncDatabaseConnection


class SQLitePool(BaseConnectionPool):
    def __init__(
        self, min_size: int = 1, max_size: int = 10, timeout: int = 30, **kwargs
    ) -> None:
        self._min_size = min_size
        self._max_size = max_size
        self._kwargs = kwargs

        self._pool: queue.Queue[SyncDatabaseConnection] = queue.Queue(maxsize=max_size)
        self._in_use: Set[SyncDatabaseConnection] = set()
        self._lock = threading.RLock()
        self._timeout = timeout

        self._initialize_pool()

    def _initialize_pool(self) -> None:
        for _ in range(self._min_size):
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _wrap_connection(self, raw_conn: Any) -> SyncDatabaseConnection:
        from nexios.orm.backends.dialects.sqlite.base import BaseSQLiteConnection
        return cast(SyncDatabaseConnection, BaseSQLiteConnection.connection(raw_conn))
    
    def _create_connection(self) -> SyncDatabaseConnection:
        try:
            conn = sqlite3.connect(**self._get_connection_kwargs())
            return self._wrap_connection(conn)
        except Exception as e:
            raise e
    
    def _get_connection_kwargs(self) -> Dict[str, Any]:
        connection_kwargs = self._kwargs.copy()
        print(f"Raw connection_kwargs: {connection_kwargs}")
        connection_kwargs.pop('driver', None)

        if 'database' not in connection_kwargs:
            connection_kwargs['database'] = ':memory:'

        return connection_kwargs

    def _is_connection_valid(self, conn: SyncDatabaseConnection) -> bool:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False
    
    def get_connection(self) -> SyncDatabaseConnection:
        try:
            conn = self._pool.get_nowait()
            if not self._is_connection_valid(conn):
                try:
                    conn.close()
                except Exception:
                    pass
                conn = self._create_connection()
        except queue.Empty:
            # No available connections, check if we can create new one
            with self._lock:
                total_connections = self._pool.qsize() + len(self._in_use)
                if total_connections < self._max_size:
                    conn = self._create_connection()
                else:
                    # Wait for a connection to become available
                    conn = self._pool.get(timeout=30)  # 30 second timeout
        
        with self._lock:
            self._in_use.add(conn)
            
        return conn
    
    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        if conn not in self._in_use:
            try:
                conn.close()
            except Exception:
                pass
            return

        with self._lock:
            self._in_use.remove(conn)
        
        try:
            conn.rollback()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return
        
        if self._is_connection_valid(conn):
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            try:
                conn.close()
            except Exception:
                pass
    
    def close(self) -> None:
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    try:
                        conn.close()
                    except Exception:
                        pass
                except queue.Empty:
                    break
            
            for conn in self._in_use.copy():
                try:
                    conn.close()
                except Exception:
                    pass
                self._in_use.remove(conn)
    
    @property
    def size(self) -> int:
        return self._pool.qsize() + len(self._in_use)

    @property
    def available(self) -> int:
        return self._pool.qsize()
