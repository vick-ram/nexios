import asyncio
from typing import Any, Dict, Set

import aiomysql
from nexios.orm.backends.dialects.mysql.aiomysql_ import MySQLAioMySQLConnection
from nexios.orm.backends.dialects.mysql.base import MySQLConnection_
from nexios.orm.backends.manager import AsyncDatabaseManager
from nexios.orm.backends.pool.base import BaseAsyncConnectionPool
from nexios.orm.connection import AsyncDatabaseConnection


class AioMySQLPool(BaseAsyncConnectionPool):
    def __init__(
        self,
        db_manager: "AsyncDatabaseManager",
        min_size: int = 1,
        max_size: int = 10,
        **kwargs,
    ) -> None:
        self.db_manager = db_manager
        self.kwargs = kwargs
        self.min_size = min_size
        self.max_size = max_size

        self._raw_pool: aiomysql.Pool
        self._wrapped_connections: Dict[AsyncDatabaseConnection, Any] = {}
        self._in_use: Set[AsyncDatabaseConnection] = set()
        self._lock = asyncio.Lock()
    
    async def _ensure_initialized(self):
        if self._raw_pool is None:
            await self._initialize_pool()
    
    async def _initialize_pool(self):
        try:
            import aiomysql
        except ImportError:
            raise ImportError("aiomysql is required for AioMySQL connection pooling")
        
        connection_kwargs = self._get_connection_kwargs()

        self._raw_pool = await aiomysql.create_pool(
            minsize=self.min_size,
            maxsize=self.max_size,
            **connection_kwargs
        )


    def _get_connection_kwargs(self) -> Dict[str, Any]:
        kwargs = self.db_manager.connection_params.copy()
        kwargs.pop('use_pool', None)
        kwargs.pop("driver", None)
        kwargs.pop("min_size", None)
        kwargs.pop("max_size", None)
        kwargs.pop("pool_size", None)

        # Set aiomysql specific defaults
        kwargs.setdefault('autocommit', False)
        kwargs.setdefault('charset', 'utf8mb4')
        return kwargs
    
    async def get_connection(self) -> AsyncDatabaseConnection:
        await self._ensure_initialized()
        async with self._lock:
            try:
                raw_conn: aiomysql.Connection = await self._raw_pool.acquire()
                conn = await MySQLConnection_.connection_async(raw_conn)
                self._wrapped_connections[conn] = raw_conn # type: ignore
                self._in_use.add(conn) # type: ignore
                return conn # type: ignore
            except Exception as e:
                raise ConnectionError(f"Failed to get connection from aiomysql pool: {e}")
    
    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Return a connection to the aiomysql pool"""
        if conn not in self._in_use:
            return
            
        async with self._lock:
            self._in_use.remove(conn)

            raw_conn = self._wrapped_connections.get(conn)
            if raw_conn:
                try:
                    await conn.rollback()
                except Exception:
                    pass
                self._raw_pool.release(raw_conn)
                del self._wrapped_connections[conn]
            else:
                # If we don't have the raw connection mapping, just close the wrapped connection
                try:
                    await conn.close()
                except Exception:
                    pass

    async def close(self) -> None:
        """Close the aiomysql pool and all connections"""
        async with self._lock:
            # Close all connections that are in use
            for conn in self._in_use.copy():
                try:
                    await conn.close()
                except Exception:
                    pass
                self._in_use.remove(conn)
            
            self._wrapped_connections.clear()
            
            # clear the aiomysql pool
            if self._raw_pool:
                self._raw_pool.close()
                await self._raw_pool.wait_closed()
    @property
    def size(self) -> int:
        """Total number of connections in the pool"""
        if self._raw_pool is None:
            return 0
        return self.min_size + len(self._in_use)

    @property
    def available(self) -> int:
        """Number of available connections"""
        if self._raw_pool is None:
            return 0
        return max(0, self.max_size - len(self._in_use))

