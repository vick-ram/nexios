import asyncio
from collections import deque
from contextlib import asynccontextmanager
import logging
import time
from typing import Awaitable, Callable, Deque, Dict, List, Optional, Tuple
import weakref
from nexios.orm.backends.pool.base import BaseAsyncConnectionPool, PoolConfig, PoolEvent
from nexios.orm.connection import AsyncDatabaseConnection


class AsyncConnectionPool(BaseAsyncConnectionPool):
    """High-performance asynchronous connection pool for database connections."""

    def __init__(
        self,
        create_connection: Callable[[], Awaitable[AsyncDatabaseConnection]],
        config: Optional[PoolConfig] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._create_connection = create_connection
        self.config = config or PoolConfig()
        self.logger = logger or logging.getLogger(__name__)

        if self.logger.level == logging.NOTSET:
            self.logger.setLevel(logging.INFO)

        self._available: Deque[Tuple[AsyncDatabaseConnection, float]] = deque()
        self._in_use: Dict[AsyncDatabaseConnection, float] = {}
        self._all_connections: weakref.WeakSet[AsyncDatabaseConnection] = weakref.WeakSet()

        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)

        self._connection_times: Dict[AsyncDatabaseConnection, float] = {}
        self._connection_usage: Dict[AsyncDatabaseConnection, int] = {}
        self._closed = False

        self._event_handlers: Dict[PoolEvent, List[Callable[..., None]]] = {}

        self._maintenance_task: Optional[asyncio.Task[None]] = None
        self._shrink_task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

        self._stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'acquire_requests': 0,
            'acquire_timeouts': 0,
        }

        self._initialized = False
    
    async def initialize(self):
        if self._initialized:
            return
        
        await self._initialize_pool()
        self._start_background_tasks()
        self._initialized = True

        self.logger.info("AsyncConnectionPool initialized with config: %s", self.config)

    async def _initialize_pool(self):
        """Initialize the pool with minimum connections."""
        for _ in range(self.config.min_size):
            try:
                conn = await self._create_connection()
                self._available.append((conn, time.monotonic()))
                self._all_connections.add(conn)
                self._connection_times[conn] = time.monotonic()
                self._connection_usage[conn] = 0
                self._stats['connections_created'] += 1
                await self._trigger_event(PoolEvent.CONNECTION_CREATED, conn)
            except Exception as e:
                self.logger.error("Failed to create initial connection: %s", e)
        

    def _start_background_tasks(self):
        """Start maintenance and shrinking background tasks."""
        async def maintenance_worker():
            while not self._stop_event.is_set():
                try:
                    await asyncio.sleep(self.config.health_check_interval)

                    if not self._stop_event.is_set():
                        await self._background_health_check()
                except Exception as e:
                    self.logger.error("Error in maintenance worker: %s", e)
    
        async def shrink_worker():
            while not self._stop_event.is_set():
                try:
                    await asyncio.sleep(self.config.shrink_interval)

                    if not self._stop_event.is_set():
                        await self._background_shrink()
                except Exception as e:
                    self.logger.error("Error in shrink worker: %s", e)
        
        self._maintenance_task = asyncio.create_task(maintenance_worker())
        self._shrink_task = asyncio.create_task(shrink_worker())
    
    async def _background_health_check(self):
        """Perform health checks on idle connections."""
        async with self._lock:
            if self._closed:
                return
            
            current_time = time.monotonic()
            bad_connections = []

            for conn, last_used in list(self._available):
                if current_time - self._connection_times.get(conn, 0) > self.config.max_lifetime:
                    bad_connections.append(conn)
                    continue

                if current_time - last_used > self.config.idle_timeout:
                    try:
                        if not conn.is_connection_open:
                            bad_connections.append(conn)
                            await self._trigger_event(PoolEvent.CONNECTION_INVALID, conn)
                    except Exception:
                        bad_connections.append(conn)
                        await self._trigger_event(PoolEvent.CONNECTION_INVALID, conn)
                
                for conn in bad_connections:
                    self._available = deque([
                        (c, t) for c, t in self._available if c != conn
                    ])
                    await self._safe_close_connection(conn)
                    self._stats['connections_closed'] += 1
    
    async def _background_shrink(self):
        """Shrink pool by closing excess idle connections"""
        async with self._lock:
            if self._closed:
                return

        current_time = time.monotonic()
        total_size = len(self._available) + len(self._in_use)

        if total_size <= self.config.min_size:
            return
        
        max_idle_to_keep = max(
            self.config.min_size - len(self._in_use), 
            self.config.max_idle
        )

        while len(self._available) > max_idle_to_keep:
            conn, _ = self._available.popleft()
            await self._safe_close_connection(conn)
            self._stats['connections_closed'] += 1
            await self._trigger_event(PoolEvent.POOL_SHRINK, conn)
        
        current_available = list(self._available)
        self._available.clear()

        for conn, last_used in current_available:
            if current_time - last_used > self.config.idle_timeout:
                await self._safe_close_connection(conn)
                self._stats['connections_closed'] += 1
                await self._trigger_event(PoolEvent.CONNECTION_CLOSED, conn)
            else:
                self._available.append((conn, last_used))
    
    async def get_connection(self) -> AsyncDatabaseConnection:
        """Async connection acquisition"""
        if not self._initialized:
            await self.initialize()
        
        if self._closed:
            raise RuntimeError("Connection pool is closed.")
        
        self._stats['acquire_requests'] += 1
        start_time = time.monotonic()

        async with self._condition:
            while self._available:
                conn, last_used = self._available.pop()
                if await self._quick_validate(conn, last_used):
                    self._in_use[conn] = start_time
                    self._connection_usage[conn] = self._connection_usage.get(conn, 0) + 1
                    return conn
                else:
                    await self._safe_close_connection(conn)
                    self._stats['connections_closed'] += 1
            
            current_size = len(self._all_connections)
            if current_size < self.config.max_size:
                try:
                    conn = await self._create_connection()
                    self._all_connections.add(conn)
                    self._in_use[conn] = start_time
                    self._connection_times[conn] = start_time
                    self._connection_usage[conn] = 1
                    self._stats['connections_created'] += 1
                    await self._trigger_event(PoolEvent.CONNECTION_CREATED, conn)
                    await self._trigger_event(PoolEvent.POOL_GROW, conn)
                    return conn
                except Exception as e:
                    self.logger.error("Failed to create new connection: %s", e)
                    raise
            
            timeout = self.config.connection_timeout - (time.monotonic() - start_time)
            if timeout <= 0:
                self._stats['acquire_timeouts'] += 1
                raise asyncio.TimeoutError("Timed out waiting for a connection from the pool.")
            
            try:
                await asyncio.wait_for(self._condition.wait(), timeout)
            except asyncio.TimeoutError:
                self._stats['acquire_timeouts'] += 1
                raise asyncio.TimeoutError(f"Timed out waiting for a connection from the pool after: {timeout:.1f}s")
            
            while self._available:
                conn, last_used = self._available.pop()
                if await self._quick_validate(conn, last_used):
                    self._in_use[conn] = time.monotonic()
                    self._connection_usage[conn] = self._connection_usage.get(conn, 0) + 1
                    return conn
                else:
                    await self._safe_close_connection(conn)
                    self._stats['connections_closed'] += 1
            
            self._stats['acquire_timeouts'] += 1
            raise asyncio.TimeoutError("Timed out waiting for a connection from the pool.")
    
    async def _quick_validate(self, conn: AsyncDatabaseConnection, last_used: Optional[float] = None) -> bool:
        """Connetion validation"""
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
    
    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Return connection to pool"""
        if self._closed:
            await self._safe_close_connection(conn)
            return
        
        return_time = time.monotonic()

        async with self._condition:
            if conn in self._in_use:
                del self._in_use[conn]
            else:
                await self._safe_close_connection(conn)
                return
            
            if await self._quick_validate(conn):
                await self._reset_connection(conn)
                self._available.append((conn, return_time))
                self._condition.notify()
            else:
                await self._safe_close_connection(conn)
                self._stats['connections_closed'] += 1
                await self._trigger_event(PoolEvent.CONNECTION_INVALID, conn)
    
    async def _reset_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Reset connection state before returning to pool."""
        try:
            await conn.rollback()
        except Exception as e:
            pass
    
    async def _safe_close_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Safely close a connection."""
        try:
            if conn in self._all_connections:
                self._all_connections.discard(conn)
            if conn in self._connection_times:
                del self._connection_times[conn]
            if conn in self._connection_usage:
                del self._connection_usage[conn]
            await conn.close()
            await self._trigger_event(PoolEvent.CONNECTION_CLOSED, conn)
        except Exception as e:
            self.logger.debug("Error closing connection: %s", e)
    
    async def _trigger_event(self, event: PoolEvent, conn: AsyncDatabaseConnection) -> None:
        """Trigger event handlers for a specific pool event."""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(conn)
                    else:
                        handler(conn)
                except Exception as e:
                    self.logger.error("Error in event handler for %s: %s", event, e)
    
    async def add_event_handler(
        self, 
        event: PoolEvent, 
        handler: Callable[..., None]
    ) -> None:
        """Add event handler for a specific pool event."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    async def close(self) -> None:
        """Close the connection pool and all its connections."""
        if self._closed:
            return
        
        self._closed = True
        self._stop_event.set()

        if self._maintenance_task:
            self._maintenance_task.cancel()
        if self._shrink_task:
            self._shrink_task.cancel()

        async with self._condition:
            for conn, _ in self._available:
                await self._safe_close_connection(conn)
            self._available.clear()

            for conn in list(self._in_use.keys()):
                await self._safe_close_connection(conn)
            self._in_use.clear()

            self._condition.notify_all()

        self.logger.info("Connection pool closed.")
    
    async def health_check(self) -> None:
        """Manual health check of all connections in the pool."""
        await self._background_health_check()
    
    @property
    async def size(self) -> int:
        async with self._lock:
            return len(self._all_connections)
    
    @property
    async def available(self) -> int:
        async with self._lock:
            return len(self._available)
    
    async def get_stats(self) -> Dict:
        """Get pool statistics."""
        async with self._lock:
            usage_counts = list(self._connection_usage.values())
            return {
                **self._stats,
                'total_connections': len(self._all_connections),
                'idle_connections': len(self._available),
                'in_use_connections': len(self._in_use),
                'avg_usage_per_conn': sum(usage_counts) / len(usage_counts) if usage_counts else 0
            }
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for connections"""
        conn = None
        try:
            conn = await self.get_connection()
            yield conn
        except Exception:
            if conn:
                async with self._lock:
                    if conn in self._in_use:
                        del self._in_use[conn]
                await self._safe_close_connection(conn)
            raise
        finally:
            if conn:
                await self.return_connection(conn)
    
