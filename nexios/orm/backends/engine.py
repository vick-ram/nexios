from contextlib import asynccontextmanager
from logging import getLogger
from typing import Optional
from typing_extensions import Tuple, Any, AsyncGenerator
from nexios.orm.backends.config import DatabaseDetector, DatabaseDialect
from nexios.orm.backends.manager import AsyncDatabaseManager, DatabaseManager
from nexios.orm.connection import AsyncDatabaseConnection, SyncDatabaseConnection


class Engine:
    """Database engine"""

    def __init__(
        self,
        dialect: DatabaseDialect,
        echo: bool = False,
        **kwargs,
    ):
        self.dialect = dialect
        self.echo = echo
        self.kwargs = kwargs
        self.db_manager = DatabaseManager(dialect, **kwargs)
        self.async_db_manager = AsyncDatabaseManager(dialect, **kwargs)
        self.logger = getLogger(__name__)

    def connect(self) -> SyncDatabaseConnection:
        conn = self.db_manager.connect()
        return conn

    @asynccontextmanager
    async def async_connect(self) -> AsyncGenerator[AsyncDatabaseConnection]:
        conn = await self.async_db_manager.connect()
        try:
            yield conn
        finally:
            await conn.close()

    def _log_sql(self, sql: str, parameters: Tuple[Any, ...] = ()) -> None:
        if self.echo:
            self.logger.info("SQL: %s, Parameters: %s", sql, parameters)


def create_engine(
    url: Optional[str] = None,
    dialect: Optional[DatabaseDialect] = None,
    driver: Optional[str] = None,
    echo: bool = False,
    **kwargs: Any,
) -> Engine:
    if url:
        detected_dialect, detected_driver, connection_params = DatabaseDetector.detect_from_url(url)
        kwargs.update(connection_params)

        if dialect and dialect != detected_dialect:
            raise ValueError(f"Dialect mismatch: provided {dialect}, detected {detected_dialect}")
        
        if driver and driver != detected_driver:
            raise ValueError(f"Driver mismatch: provided {driver}, detected {detected_driver}")
        
        dialect = detected_dialect
        driver = detected_driver
    
    elif not dialect:
        dialect, driver = DatabaseDetector.detect_from_kwargs(kwargs)

    if driver:
        kwargs['driver'] = driver
    
    return Engine(dialect=dialect, echo=echo, **kwargs)
