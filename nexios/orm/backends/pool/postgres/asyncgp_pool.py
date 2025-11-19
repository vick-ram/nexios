import asyncio
from typing import Optional, Set, cast
import asyncpg
from nexios.orm.backends.dialects.postgres.base import PostgresConnection
from nexios.orm.backends.pool.base import BaseAsyncConnectionPool
from nexios.orm.connection import AsyncDatabaseConnection


class AsyncpgConnectionPool(BaseAsyncConnectionPool):
    def __init__(
        self,
        min_size: int = 1,
        max_size: int = 10,
        **kwargs,
    ) -> None:
        self._min_size = min_size
        self._max_size = max_size
        self._kwargs = kwargs

        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
        self._in_use: Set[AsyncDatabaseConnection] = set()
    
    async def _ensure_initialized(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                min_size=self._min_size,
                max_size=self._max_size,
                **self._kwargs,
            )
    
    async def get_connection(self) -> AsyncDatabaseConnection:
        await self._ensure_initialized()
        # _pool is guaranteed to be not None after _ensure_initialized
        assert self._pool is not None
        async with self._lock:
            raw_conn = await self._pool.acquire()
            conn = await PostgresConnection.connect_async(raw_conn)
            self._in_use.add(conn) # type: ignore
            return cast(AsyncDatabaseConnection, conn)
    
    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                if self._pool is not None:
                    await self._pool.release(conn.raw_connection)
    
    async def close(self) -> None:
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._pool = None
            self._in_use.clear()
    
    @property
    def size(self) -> int:
        return self._pool.get_size() if self._pool else 0
    
    @property
    def available(self) -> int:
        return self._pool.get_idle_size() if self._pool else 0
    
