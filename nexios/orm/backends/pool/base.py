from abc import ABC, abstractmethod
import asyncio
import threading
import time
from typing import Awaitable, Callable, List, Set
from nexios.orm.connection import AsyncDatabaseConnection, SyncDatabaseConnection


class BaseConnectionPool(ABC):
    @abstractmethod
    def get_connection(self) -> SyncDatabaseConnection:
        """Get connection from the pool"""
        pass

    @abstractmethod
    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        """Return connection to the pool"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close all connections in the pool"""
        pass

    @property
    @abstractmethod
    def size(self) -> int:
        """Current pool size"""
        pass

    @property
    @abstractmethod
    def available(self) -> int:
        """Number of available connections in the pool"""
        pass


class BaseAsyncConnectionPool(ABC):
    @abstractmethod
    async def get_connection(self) -> AsyncDatabaseConnection:
        """Get a connection from the pool"""
        pass

    @abstractmethod
    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Return a connection to the pool"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close all connections in the pool"""
        pass

    @property
    @abstractmethod
    def size(self) -> int:
        """Current pool size"""
        pass

    @property
    @abstractmethod
    def available(self) -> int:
        """Number of available connections in the pool"""
        pass


class GenericConnectionPool(BaseConnectionPool):
    """Generic connection pool implementation for synchronous databases"""

    def __init__(
        self,
        create_connection: Callable[[], SyncDatabaseConnection],
        min_size: int = 1,
        max_size: int = 10,
        timeout: float = 5.0,
    ) -> None:
        self._create_connection = create_connection
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout

        self._pool: List[SyncDatabaseConnection] = []
        self._in_use: Set[SyncDatabaseConnection] = set()
        self._lock = threading.Lock()
        
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the pool with minimum connections"""
        for _ in range(self.min_size):
            conn = self._create_connection()
            self._pool.append(conn)

    def get_connection(self) -> SyncDatabaseConnection:
        """Get a connection from the pool"""
        start = time.monotonic()
        while True:
            with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                    if not self._is_connection_alive(conn):
                        conn = self._create_connection()
                    self._in_use.add(conn)
                    return conn
                
                if len(self._in_use) < self.max_size:
                    conn = self._create_connection()
                    self._in_use.add(conn)
                    return conn
            
            # wait for availability
            if time.monotonic() - start > self.timeout:
                raise TimeoutError("Timeout while waiting for a database connection")
            time.sleep(0.05)

    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                try:
                    conn.rollback()
                except Exception:
                    pass
                self._pool.append(conn)

    def close(self) -> None:
        with self._lock:
            for conn in self._pool + list(self._in_use):
                try:
                    conn.close()
                except Exception:
                    pass
            self._pool.clear()
            self._in_use.clear()
    
    def _is_connection_alive(self, conn: 'SyncDatabaseConnection') -> bool:
        try:
            cur = conn.cursor()
            cur.execute("SELECCT 1")
            conn.close()
            return True
        except Exception:
            return False

    @property
    def size(self) -> int:
        return len(self._pool) + len(self._in_use)

    @property
    def available(self) -> int:
        return len(self._pool)

class GenericAsyncConnectionPool(BaseAsyncConnectionPool):
    """Generic connection pool implementation for asynchronous databases"""

    def __init__(
        self,
        create_connection: Callable[[], Awaitable[AsyncDatabaseConnection]],
        min_size: int = 1,
        max_size: int = 10,
        timeout: float = 5.0
    ) -> None:
        self._create_connection = create_connection
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout

        self._pool: List[AsyncDatabaseConnection] = []
        self._in_use: Set[AsyncDatabaseConnection] = set()
        self._lock = asyncio.Lock()

        self._intialized = False
    
    async def _ensure_initialized(self):
        if not self._intialized:
            for _ in range(self.min_size):
                conn = await self._create_connection()
                self._pool.append(conn)
            self._intialized = True

    async def get_connection(self) -> AsyncDatabaseConnection:
        """Get a connection from the pool"""
        await self._ensure_initialized()
        start = time.monotonic()

        while True:
            async with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                    if not await self._is_connection_alive(conn):
                        conn = await self._create_connection()
                    self._in_use.add(conn)
                    return conn
                
                if len(self._in_use) < self.max_size:
                    conn = await self._create_connection()
                    self._in_use.add(conn)
                    return conn

            if time.monotonic() - start > self.timeout:
                raise TimeoutError("Timeout while waiting for async database connection")
            
            await asyncio.sleep(0.05)

    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                try:
                    await conn.rollback()
                except Exception:
                    pass
                self._pool.append(conn)

    async def close(self) -> None:
        async with self._lock:
            for conn in self._pool + list(self._in_use):
                try:
                    await conn.close()
                except Exception:
                    pass
            self._pool.clear()
            self._in_use.clear()
            self._intialized = False
    
    async def _is_connection_alive(self, conn) -> bool:
        try:
            cur = await conn.cursor()
            await cur.execute("SELECT 1;")
            await cur.close()
            return True
        except Exception:
            return False

    @property
    def size(self) -> int:
        return len(self._pool) + len(self._in_use)

    @property
    def available(self) -> int:
        return len(self._pool)
