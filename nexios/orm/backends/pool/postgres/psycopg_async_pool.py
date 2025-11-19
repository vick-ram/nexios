import asyncio
from typing import Any, Dict, Set

import psycopg_pool
from nexios.orm.backends.dialects.postgres.base import PostgresConnection
from nexios.orm.backends.pool.base import BaseAsyncConnectionPool
from nexios.orm.connection import AsyncDatabaseConnection


class PsycopgAsynConnectioncPool(BaseAsyncConnectionPool):
    def __init__(self, min_size: int = 1, max_size: int = 5, **kwargs) -> None:
        self.kwargs = kwargs
        self.min_size = min_size
        self.max_size = max_size
        self._kwargs = kwargs

        self._raw_pool: psycopg_pool.AsyncConnectionPool
        self._lock = asyncio.Lock()
        self._in_use: Set[AsyncDatabaseConnection] = set()

    async def _initialize_pool(self):
        try:
            import psycopg_pool
        except ImportError:
            raise ImportError(
                "psycopg-pool is required for psycopg3 connection pooling"
            )

        connection_kwargs = self._get_connection_kwargs()
        conninfo = self._build_conninfo(connection_kwargs)

        self._raw_pool = psycopg_pool.AsyncConnectionPool(
            conninfo=conninfo,
            min_size=self.min_size,
            max_size=self.max_size,
            **{
                k: v
                for k, v in self.kwargs.items()
                if k not in ["min_size", "max_size", "pool_size"]
            },
        )
        await self._raw_pool.open()

    def _get_connection_kwargs(self) -> Dict[str, Any]:
        kwargs = self._kwargs.copy()
        kwargs.pop("driver", None)
        return kwargs

    def _build_conninfo(self, kwargs: Dict[str, Any]) -> str:
        """Build connection string from kwargs"""
        parts = []
        if "host" in kwargs:
            parts.append(f"host={kwargs['host']}")
        if "port" in kwargs:
            parts.append(f"port={kwargs['port']}")
        if "database" in kwargs:
            parts.append(f"dbname={kwargs['database']}")
        if "user" in kwargs:
            parts.append(f"user={kwargs['user']}")
        if "password" in kwargs:
            parts.append(f"password={kwargs['password']}")
        return " ".join(parts)

    async def _wrap_connection(self, raw_conn: Any) -> AsyncDatabaseConnection:
        """Wrap raw psycopg3 connection with our abstraction"""
        return await PostgresConnection.connect_async(raw_conn) # type: ignore

    async def get_connection(self) -> AsyncDatabaseConnection:
        """Get a connection from the pool"""
        if not self._raw_pool:
            await self._initialize_pool()

        raw_conn = await self._raw_pool.getconn()
        wrapper_conn = await self._wrap_connection(raw_conn)

        # Store references for proper cleanup
        setattr(wrapper_conn, "_pool", self)
        setattr(wrapper_conn, "_raw_connection", raw_conn)

        async with self._lock:
            self._in_use.add(wrapper_conn)

        return wrapper_conn

    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Return a connection to the pool"""
        _raw_connection = getattr(conn, "_raw_connection")
        if hasattr(conn, "_raw_connection") and _raw_connection:
            async with self._lock:
                if conn in self._in_use:
                    self._in_use.remove(conn)

            # Return the raw connection to psycopg3's pool
            await self._raw_pool.putconn(_raw_connection)

            # Clean up references
            delattr(conn, "_pool")
            delattr(conn, "_raw_connection")

    async def close(self) -> None:
        """Close all connections in the pool"""
        if self._raw_pool:
            await self._raw_pool.close()
        self._in_use.clear()

    @property
    def size(self) -> int:
        return len(self._in_use)

    @property
    def available(self) -> int:
        if not self._raw_pool:
            return 0
        return max(0, self.max_size - len(self._in_use))
