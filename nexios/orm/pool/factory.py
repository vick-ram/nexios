from typing import Callable, Awaitable
from nexios.orm.pool.base import (
    BaseConnectionPool,
    BaseAsyncConnectionPool,
    PoolConfig,
)
from nexios.orm.connection import SyncDatabaseConnection, AsyncDatabaseConnection
from nexios.orm.pool.connection_pool import ConnectionPool
from nexios.orm.pool.async_connection_pool import AsyncConnectionPool


class ConnectionPoolFactory:
    @staticmethod
    def config(min_size, max_size, **kwargs) -> PoolConfig:
        return PoolConfig(
            max_size=max_size,
            min_size=min_size,
            connection_timeout=kwargs.get("connection_timeout", 5.0),
            max_lifetime=kwargs.get("max_lifetime", 7200),
            idle_timeout=kwargs.get("idle_timeout", 300),
            health_check_interval=kwargs.get("health_check_interval", 60),
            shrink_interval=kwargs.get("shrink_interval", 30),
            max_idle=kwargs.get("max_idle", 10),
        )
    
    @staticmethod
    def create_sync_pool(
        connection: Callable[[], SyncDatabaseConnection],
        max_size: int = 10,
        min_size: int = 1,
        **kwargs,
    ) -> BaseConnectionPool:
        config = ConnectionPoolFactory.config(min_size, max_size, **kwargs)
        return ConnectionPool(connection, config)

    @staticmethod
    def create_async_pool(
        connection: Callable[[], Awaitable[AsyncDatabaseConnection]],
        max_size: int = 10,
        min_size: int = 1,
        **kwargs,
    ) -> BaseAsyncConnectionPool:
        config = ConnectionPoolFactory.config(min_size, max_size, **kwargs)
        return AsyncConnectionPool(connection, config)
