from logging import getLogger
from typing import Optional
from typing_extensions import Tuple, Any
from nexios.orm.backends.manager import AsyncDatabaseManager, DatabaseManager
from nexios.orm.connection import AsyncDatabaseConnection, SyncDatabaseConnection


class Engine:
    """Database engine"""

    def __init__(
        self,
        url: Optional[str] = None,
        echo: bool = False,
        pool_size: int = 10,
        min_pool_size: int = 1,
        use_pool: bool = True,
        **kwargs,
    ):
        self.url = url
        self.echo = echo
        self.pool_size = pool_size
        self.min_pool_size = min_pool_size
        self.use_pool = use_pool
        self.kwargs = kwargs

        manager_kwargs = kwargs.copy()
        manager_kwargs.update({
            'use_pool': use_pool,
            'pool_min_size': min_pool_size,
            'pool_max_size': pool_size
        })

        # Initialize managers - they handle detection internally
        self.db_manager = DatabaseManager(url=url, **manager_kwargs)
        self.async_db_manager = AsyncDatabaseManager(url=url, **manager_kwargs)

        # Get detected dialect and driver from managers
        self.dialect = self.db_manager.db_type
        self.driver = self.db_manager.driver

        self.logger = getLogger(__name__)

    def connect(self) -> SyncDatabaseConnection:
        """Get a sync connection from pool or create direct connection"""
        return self.db_manager.connect()
    
    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        """Return a sync connection to pool or close it"""
        self.db_manager.return_connection(conn)

    async def async_connect(self) -> AsyncDatabaseConnection:
        """Get an async connection from pool or create direct connection"""
        return await self.async_db_manager.connect()

    async def return_async_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Return an async connection to pool or close it"""
        await self.async_db_manager.return_connection(conn)

    def _log_sql(self, sql: str, parameters: Tuple[Any, ...] = ()) -> None:
        """Log SQL statements if echo is enabled"""
        if self.echo:
            self.logger.info("SQL: %s, Parameters: %s", sql, parameters)

    def close(self) -> None:
        """Close all connections and pools"""
        self.db_manager.close()

    async def aclose(self) -> None:
        """Async close all connections and pools"""
        await self.async_db_manager.close()

def create_engine(
        url: Optional[str] = None,
        *,
        echo: bool = False,
        pool_size: int = 10,
        min_pool_size: int = 1,
        use_pool: bool = True,
        **kwargs
) -> Engine:
    """Create a database engine from URL or parameters"""
    return Engine(
        url=url,
        echo=echo,
        pool_size=pool_size,
        min_pool_size=min_pool_size,
        use_pool=use_pool,
        **kwargs
    )

