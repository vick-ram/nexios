import asyncio
from typing import Any, Dict, Set, cast

import aiosqlite
from nexios.orm.backends.pool.base import BaseAsyncConnectionPool
from nexios.orm.connection import AsyncDatabaseConnection


class AioSQLitePool(BaseAsyncConnectionPool):
    def __init__(
        self, min_size: int = 1, max_size: int = 10, timeout: int = 30, **kwargs
    ) -> None:
        self._min_size = min_size
        self._max_size = max_size
        self._kwargs = kwargs
        self._timeout = timeout

        self._pool: asyncio.Queue[AsyncDatabaseConnection] = asyncio.Queue(
            maxsize=max_size
        )
        self._in_use: Set[AsyncDatabaseConnection] = set()
        self._lock = asyncio.Lock()

        self._initialized = False
    
    async def _ensure_initialized(self):
        if not self._initialized:
            await self._initialize_pool()
            self._initialized = True

    async def _initialize_pool(self):
        for _ in range(self._min_size):
            conn = await self._create_connection()
            self._pool.put_nowait(conn)

    async def _wrap_connection(self, raw_conn: Any) -> AsyncDatabaseConnection:
        from nexios.orm.backends.dialects.sqlite.base import BaseSQLiteConnection

        return cast(AsyncDatabaseConnection, BaseSQLiteConnection.connection(raw_conn))

    async def _create_connection(self) -> AsyncDatabaseConnection:
        try:
            raw_conn = await aiosqlite.connect(**self._get_connection_kwargs())
            return await self._wrap_connection(raw_conn)
        except Exception as e:
            raise ConnectionError(f"Failed to create aiosqlite connection: {e}")

    def _get_connection_kwargs(self) -> Dict[str, Any]:
        connection_kwargs = self._kwargs.copy()

        connection_kwargs.pop("driver", None)

        connection_kwargs.setdefault("timeout", self._timeout)
        return connection_kwargs

    async def _is_connection_valid(self, conn: AsyncDatabaseConnection) -> bool:
        try:
            cursor = await conn.cursor()
            await cursor.execute("SELECT 1")
            await conn.close()
            return True
        except Exception:
            return False

    async def get_connection(self) -> AsyncDatabaseConnection:
        """Get a connection from the pool"""
        await self._ensure_initialized()

        try:
            # Try to get a connection without waiting
            conn = self._pool.get_nowait()
            if not await self._is_connection_valid(conn):
                try:
                    await conn.close()
                except Exception:
                    pass
                conn = await self._create_connection()
        except asyncio.QueueEmpty:
            # No available connections, check if we can create new one
            async with self._lock:
                total_connections = self._pool.qsize() + len(self._in_use)
                if total_connections < self._max_size:
                    conn = await self._create_connection()
                else:
                    # Wait for a connection to become available
                    try:
                        conn = await asyncio.wait_for(
                            self._pool.get(), timeout=self._timeout
                        )
                    except asyncio.TimeoutError:
                        raise TimeoutError(
                            f"Timeout waiting for connection after {self._timeout} seconds"
                        )

        async with self._lock:
            self._in_use.add(conn)

        return conn

    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Return a connection to the pool"""
        if conn not in self._in_use:
            try:
                await conn.close()
            except Exception:
                pass
            return

        async with self._lock:
            self._in_use.remove(conn)

        # Reset connection state
        try:
            await conn.rollback()
        except Exception:
            # Connection might be broken, don't return it to pool
            try:
                await conn.close()
            except Exception:
                pass
            return

        # Check if connection is still valid before returning to pool
        if await self._is_connection_valid(conn):
            try:
                self._pool.put_nowait(conn)
            except asyncio.QueueFull:
                # Pool is full, close the connection
                try:
                    await conn.close()
                except Exception:
                    pass
        else:
            # Connection is not valid, close it
            try:
                await conn.close()
            except Exception:
                pass

    async def close(self) -> None:
        """Close all connections in the pool"""
        async with self._lock:
            # Close all connections in the pool
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    try:
                        await conn.close()
                    except Exception:
                        pass
                except asyncio.QueueEmpty:
                    break

            # Close all in-use connections
            for conn in self._in_use.copy():
                try:
                    await conn.close()
                except Exception:
                    pass
                self._in_use.remove(conn)

    @property
    def size(self) -> int:
        """Total number of connections in the pool"""
        return self._pool.qsize() + len(self._in_use)

    @property
    def available(self) -> int:
        """Number of available connections in the pool"""
        return self._pool.qsize()
