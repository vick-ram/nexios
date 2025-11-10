from contextlib import asynccontextmanager
from logging import getLogger
from typing_extensions import Tuple, Any, AsyncGenerator
from nexios.orm.backends.manager import AsyncDatabaseManager, DatabaseManager
from nexios.orm.connection import AsyncDatabaseConnection, SyncDatabaseConnection
from nexios.orm.backends.types import DatabaseDialect

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

    def _log_sql(self, sql: str, parameters: Tuple[Any, ...] = ()) ->None:
        if self.echo:
            self.logger.info("SQL: %s, Parameters: %s", sql, parameters)

def create_engine(dialect: DatabaseDialect = 'sqlite', echo: bool = False, **kwargs: Any) -> Engine:
    return Engine(dialect, echo=echo, **kwargs)
