import queue
import threading
import time
from typing import Any, Dict, Set

import pymysql
from nexios.orm.backends.dialects.mysql.base import MySQLConnection_
from nexios.orm.backends.pool.base import BaseConnectionPool
from nexios.orm.connection import SyncDatabaseConnection


class PyMySQLConnectionPool(BaseConnectionPool):
    """
    Optimized connection pool for PyMySQL with connection health checks
    and better error handling.
    """

    def __init__(
        self,
        min_size: int = 1,
        max_size: int = 10,
        health_check_timeout: int = 30,
        **kwargs,
    ) -> None:
        self.min_size = min_size
        self.max_size = max_size
        self.health_check_timeout = health_check_timeout

        self._pool: queue.Queue = queue.Queue(maxsize=max_size)
        self._in_use: Set[SyncDatabaseConnection] = set()
        self._lock = threading.RLock()
        self._last_health_check = time.time()

        self.kwargs = kwargs
        self._initialize_pool()
    
    def _initialize_pool(self):
        for _ in range(self.min_size):
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _wrap_connection(self, raw_conn: Any) -> SyncDatabaseConnection:
        return MySQLConnection_.connection(raw_conn) # type: ignore
    
    def _create_connection(self) -> SyncDatabaseConnection:
        """Create a new connection with PyMySQL specific settings"""
        try:
            conn = pymysql.connect(**self._get_pymysql_kwargs())
            conn = self._wrap_connection(conn)
            return conn
        except Exception as e:
            raise ConnectionError(f"Failed to create PyMySQL connection: {e}")
    
    def _get_pymysql_kwargs(self) -> Dict[str, Any]:
        """Extract PyMySQL specific connection parameters"""
        pymysql_kwargs = self.kwargs.copy()
        
        # PyMySQL specific optimizations
        pymysql_kwargs.setdefault('autocommit', False)
        pymysql_kwargs.setdefault('charset', 'utf8mb4')
        pymysql_kwargs.setdefault('connect_timeout', 10)
        
        return pymysql_kwargs
    
    def _is_connection_valid(self, conn: SyncDatabaseConnection) -> bool:
        """Check if a connection is still valid"""
        try:
            # Use a simple test query to check connection health
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def _health_check(self):
        """Perform periodic health checks on connections"""
        current_time = time.time()
        if current_time - self._last_health_check < self.health_check_timeout:
            return
            
        with self._lock:
            temp_pool = []
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    if self._is_connection_valid(conn):
                        temp_pool.append(conn)
                    else:
                        try:
                            conn.close()
                        except Exception:
                            pass
                except queue.Empty:
                    break
            
            # Refill the pool if below min_size
            while len(temp_pool) < self.min_size and len(temp_pool) + len(self._in_use) < self.max_size:
                try:
                    new_conn = self._create_connection()
                    temp_pool.append(new_conn)
                except Exception:
                    break
            
            # Put valid connections back in pool
            for conn in temp_pool:
                self._pool.put(conn)
                
            self._last_health_check = current_time

    def get_connection(self) -> SyncDatabaseConnection:
        """Get a connection from the pool with health checks"""
        self._health_check()
        
        try:
            # Try to get connection without waiting
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
                if total_connections < self.max_size:
                    conn = self._create_connection()
                else:
                    # Wait for a connection to become available
                    conn = self._pool.get(timeout=30)  # 30 second timeout
        
        with self._lock:
            self._in_use.add(conn)
            
        return conn

    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        """Return a connection to the pool"""
        if conn not in self._in_use:
            # Connection not from this pool, close it
            try:
                conn.close()
            except Exception:
                pass
            return
            
        with self._lock:
            self._in_use.remove(conn)
            
        # Reset connection state before returning to pool
        try:
            conn.rollback()
        except Exception:
            # Connection might be broken, don't return it
            try:
                conn.close()
            except Exception:
                pass
            return
            
        # Check if connection is still valid before returning to pool
        if self._is_connection_valid(conn):
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                # Pool is full, close the connection
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            # Connection is not valid, close it
            try:
                conn.close()
            except Exception:
                pass

    def close(self) -> None:
        """Close all connections in the pool"""
        with self._lock:
            # Close all connections in the pool
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    try:
                        conn.close()
                    except Exception:
                        pass
                except queue.Empty:
                    break
            
            # Close all in-use connections
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
