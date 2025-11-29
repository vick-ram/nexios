import logging
import threading
import time
from typing import Callable, Dict, Optional, Tuple, Deque, List
from contextlib import contextmanager
from nexios.orm.backends.pool.base import BaseConnectionPool, PoolConfig, PoolEvent
from nexios.orm.connection import SyncDatabaseConnection
import statistics
import weakref
from collections import deque

class ConnectionPool(BaseConnectionPool):
    """
    Production-ready connection pool with active maintenance like psycopg
    """
    
    def __init__(
        self,
        create_connection: Callable[[], SyncDatabaseConnection],
        config: Optional[PoolConfig] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._create_connection = create_connection
        self.config = config or PoolConfig()
        self.logger = logger or logging.getLogger(__name__)

        if self.logger.level == logging.NOTSET:
            self.logger.setLevel(logging.INFO)

        # Connection storage with last-used timestamps
        self._available: Deque[Tuple[SyncDatabaseConnection, float]] = deque()
        self._in_use: Dict[SyncDatabaseConnection, float] = {}
        self._all_connections: weakref.WeakSet[SyncDatabaseConnection] = weakref.WeakSet()
        
        # Threading
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        
        # Tracking
        self._connection_times: Dict[SyncDatabaseConnection, float] = {}
        self._connection_usage: Dict[SyncDatabaseConnection, int] = {}
        self._closed = False
        
        # Event callbacks
        self._event_handlers: Dict[PoolEvent, List[Callable]] = {}
        
        # Background workers
        self._maintenance_thread: Optional[threading.Thread] = None
        self._shrink_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self._stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'acquire_requests': 0,
            'acquire_timeouts': 0,
        }
        
        self._initialize_pool()
        self._start_background_workers()
        
        self.logger.info(
            f"Connection pool initialized: min={self.config.min_size}, max={self.config.max_size}"
        )

    def _initialize_pool(self):
        """Initialize with minimum connections"""
        for _ in range(self.config.min_size):
            try:
                conn = self._create_connection()
                self._available.append((conn, time.monotonic()))
                self._all_connections.add(conn)
                self._connection_times[conn] = time.monotonic()
                self._connection_usage[conn] = 0
                self._stats['connections_created'] += 1
                self._fire_event(PoolEvent.CONNECTION_CREATED, conn)
            except Exception as e:
                self.logger.error(f"Initial connection creation failed: {e}")

    def _start_background_workers(self):
        """Start maintenance and shrinking workers"""
        def maintenance_worker():
            while not self._stop_event.is_set():
                try:
                    time.sleep(self.config.health_check_interval)
                    if not self._stop_event.is_set():
                        self._background_health_check()
                except Exception as e:
                    self.logger.error(f"Maintenance worker error: {e}")

        def shrink_worker():
            while not self._stop_event.is_set():
                try:
                    time.sleep(self.config.shrink_interval)
                    if not self._stop_event.is_set():
                        self._background_shrink()
                except Exception as e:
                    self.logger.error(f"Shrink worker error: {e}")

        self._maintenance_thread = threading.Thread(
            target=maintenance_worker, daemon=True, name="pool-maintenance"
        )
        self._shrink_thread = threading.Thread(
            target=shrink_worker, daemon=True, name="pool-shrink"
        )
        
        self._maintenance_thread.start()
        self._shrink_thread.start()

    def _background_health_check(self):
        """Background health check of idle connections"""
        with self._lock:
            if self._closed:
                return
                
            current_time = time.monotonic()
            bad_connections = []
            
            # Check idle connections
            for conn, last_used in list(self._available):
                # Check if connection is too old
                if current_time - self._connection_times.get(conn, 0) > self.config.max_lifetime:
                    bad_connections.append(conn)
                    continue
                    
                # Check if connection needs health validation
                if current_time - last_used > 60:  # Validate if idle > 1 minute
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")
                    except Exception:
                        bad_connections.append(conn)
                        self._fire_event(PoolEvent.CONNECTION_INVALID, conn)
            
            # Remove bad connections
            for conn in bad_connections:
                self._available = deque([
                    (c, t) for c, t in self._available if c != conn
                ])
                self._safe_close_connection(conn)
                self._stats['connections_closed'] += 1

    def _background_shrink(self):
        """Shrink pool by closing excess idle connections"""
        with self._lock:
            if self._closed:
                return
                
            current_time = time.monotonic()
            total_size = len(self._available) + len(self._in_use)
            
            # Don't shrink below min_size
            if total_size <= self.config.min_size:
                return
                
            # Calculate how many idle connections to keep
            max_idle_to_keep = max(
                self.config.min_size - len(self._in_use),  # At least enough for current in_use
                self.config.max_idle  # But no more than max_idle
            )
            
            # Remove excess idle connections (oldest first)
            while len(self._available) > max_idle_to_keep:
                conn, last_used = self._available.popleft()
                self._safe_close_connection(conn)
                self._stats['connections_closed'] += 1
                self._fire_event(PoolEvent.POOL_SHRINK, conn)
                
            # Also remove connections that have been idle too long
            current_available = list(self._available)
            self._available.clear()
            
            for conn, last_used in current_available:
                if current_time - last_used > self.config.idle_timeout:
                    self._safe_close_connection(conn)
                    self._stats['connections_closed'] += 1
                    self._fire_event(PoolEvent.CONNECTION_CLOSED, conn)
                else:
                    self._available.append((conn, last_used))

    def get_connection(self) -> SyncDatabaseConnection:
        """Optimized connection acquisition"""
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        self._stats['acquire_requests'] += 1
        start_time = time.monotonic()

        with self._condition:
            # FAST PATH: Try to get available connection
            while self._available:
                conn, last_used = self._available.pop()
                if self._quick_validate(conn, last_used):
                    self._in_use[conn] = start_time
                    self._connection_usage[conn] = self._connection_usage.get(conn, 0) + 1
                    return conn
                else:
                    self._safe_close_connection(conn)
                    self._stats['connections_closed'] += 1

            # MEDIUM PATH: Create new connection if under max
            current_size = len(self._all_connections)
            if current_size < self.config.max_size:
                try:
                    conn = self._create_connection()
                    self._all_connections.add(conn)
                    self._in_use[conn] = start_time
                    self._connection_times[conn] = start_time
                    self._connection_usage[conn] = 1
                    self._stats['connections_created'] += 1
                    self._fire_event(PoolEvent.CONNECTION_CREATED, conn)
                    self._fire_event(PoolEvent.POOL_GROW, conn)
                    return conn
                except Exception as e:
                    self.logger.error(f"Failed to create connection: {e}")

            # SLOW PATH: Wait for connection with timeout
            timeout = self.config.connection_timeout - (time.monotonic() - start_time)
            if timeout <= 0:
                self._stats['acquire_timeouts'] += 1
                raise TimeoutError("Connection timeout exceeded")

            # Wait for connection to become available
            end_time = time.monotonic() + timeout
            while time.monotonic() < end_time:
                remaining = end_time - time.monotonic()
                if remaining <= 0:
                    break
                    
                self._condition.wait(remaining)
                
                # Check if connection became available
                while self._available:
                    conn, last_used = self._available.pop()
                    if self._quick_validate(conn, last_used):
                        self._in_use[conn] = time.monotonic()
                        self._connection_usage[conn] = self._connection_usage.get(conn, 0) + 1
                        return conn
                    else:
                        self._safe_close_connection(conn)
                        self._stats['connections_closed'] += 1

            self._stats['acquire_timeouts'] += 1
            raise TimeoutError(f"Timeout waiting for connection after {timeout:.1f}s")

    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        """Return connection to pool"""
        if self._closed:
            self._safe_close_connection(conn)
            return

        return_time = time.monotonic()
        
        with self._condition:
            # Remove from in_use
            if conn in self._in_use:
                del self._in_use[conn]
            else:
                self._safe_close_connection(conn)
                return

            # Validate before returning to pool
            if self._quick_validate(conn):
                self._reset_connection(conn)
                self._available.append((conn, return_time))
                # Notify waiting threads
                self._condition.notify()
            else:
                self._safe_close_connection(conn)
                self._stats['connections_closed'] += 1
                self._fire_event(PoolEvent.CONNECTION_INVALID, conn)

    def _quick_validate(self, conn: SyncDatabaseConnection, last_used: Optional[float] = None) -> bool:
        """Fast connection validation"""
        try:
            if conn.is_connection_open:
                if last_used is not None:
                    conn_time = self._connection_times.get(conn, 0)
                    current_time = time.monotonic()
                    return (current_time - conn_time) <= self.config.max_lifetime
                return True
            return False
            
        except Exception:
            return False

    def _reset_connection(self, conn: SyncDatabaseConnection) -> None:
        """Reset connection state"""
        try:
            if hasattr(conn, 'rollback'):
                conn.rollback()
        except Exception:
            pass

    def _safe_close_connection(self, conn: SyncDatabaseConnection) -> None:
        """Safely close a connection"""
        try:
            if conn in self._all_connections:
                self._all_connections.remove(conn)
            if conn in self._connection_times:
                del self._connection_times[conn]
            if conn in self._connection_usage:
                del self._connection_usage[conn]
            conn.close()
            self._fire_event(PoolEvent.CONNECTION_CLOSED, conn)
        except Exception:
            pass

    def _fire_event(self, event: PoolEvent, conn: SyncDatabaseConnection) -> None:
        """Fire event to registered handlers"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(conn)
                except Exception as e:
                    self.logger.error(f"Event handler error: {e}")

    def add_event_handler(self, event: PoolEvent, handler: Callable) -> None:
        """Add event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def close(self) -> None:
        """Close pool and all background workers"""
        if self._closed:
            return
            
        self._closed = True
        self._stop_event.set()
        
        with self._condition:
            # Close all connections
            for conn, _ in self._available:
                self._safe_close_connection(conn)
            self._available.clear()
            
            for conn in self._in_use:
                self._safe_close_connection(conn)
            self._in_use.clear()
            
            # Wake any waiting threads
            self._condition.notify_all()

    def health_check(self) -> None:
        """Manual health check"""
        self._background_health_check()

    @property
    def size(self) -> int:
        """Total pool size"""
        with self._lock:
            return len(self._all_connections)

    @property
    def available(self) -> int:
        """Available connections"""
        with self._lock:
            return len(self._available)

    def get_stats(self) -> Dict:
        """Get pool statistics"""
        with self._lock:
            return {
                **self._stats,
                'total_connections': len(self._all_connections),
                'idle_connections': len(self._available),
                'in_use_connections': len(self._in_use),
                'avg_usage_per_conn': statistics.mean(self._connection_usage.values()) if self._connection_usage else 0,
            }

    @contextmanager
    def connection(self):
        """Context manager for connections"""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        except Exception:
            if conn:
                with self._lock:
                    if conn in self._in_use:
                        del self._in_use[conn]
                self._safe_close_connection(conn)
            raise
        finally:
            if conn:
                self.return_connection(conn)