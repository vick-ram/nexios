from typing_extensions import Optional, Type, List, TYPE_CHECKING
from nexios.orm.connection import (
    AsyncDatabaseConnection,
    SyncCursor,
    AsyncCursor,
    SyncDatabaseConnection,
)
from nexios.orm.backends.engine import Engine
from nexios.orm.model import Model

# if TYPE_CHECKING:
#     from nexios.orm.query import Query


class Session:
    """Synchronous session managing a database transaction.""" 

    def __init__(self, engine: Engine):
        self.engine = engine
        self.connection: Optional[SyncDatabaseConnection] = None
        self._cursor: Optional[SyncCursor] = None
        self._in_transaction = False

    def __enter__(self):
        self.connection = self.engine.connect()
        self._cursor = self.connection.cursor()
        self._in_transaction = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.connection.close()  # type: ignore

    # --- Core methods ---
    def execute(self, sql: str, params: tuple = ()):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return self._cursor.execute(sql, params)  # type: ignore

    def fetchone(self):
        return self._cursor.fetchone()  # type: ignore

    def fetchall(self):
        return self._cursor.fetchall()  # type: ignore

    def commit(self):
        if self._in_transaction:
            self.connection.commit()  # type: ignore
            self._in_transaction = False

    def rollback(self):
        if self._in_transaction:
            self.connection.rollback()  # type: ignore
            self._in_transaction = False
    
    def query(self, model_cls: Type[Model]):
        from nexios.orm.query import Query
        return Query(self, model_cls)

    # ORM integration
    def add(self, instance: "Model"):
        sql, params = instance.save(self.engine.dialect) # type: ignore
        self.execute(sql, params)

    def create_all(self, models: List[Type["Model"]]):
        """Create all tables for given models."""
        for model in models:
            sql = model.create_table()
            self.execute(sql)
        self.commit()


class AsyncSession:
    """Asynchronous session for async database operations."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.connection: Optional[AsyncDatabaseConnection] = None
        self._cursor: Optional[AsyncCursor] = None
        self._in_transaction = False

    async def __aenter__(self):
        async with self.engine.async_connect() as conn:
            self.connection = conn
            self._cursor = await conn.cursor()
            self._in_transaction = True
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.connection.close()  # type: ignore

    async def execute(self, sql: str, params: tuple = ()):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return await self._cursor.execute(sql, params)  # type: ignore

    async def fetchone(self):
        return await self._cursor.fetchone()  # type: ignore

    async def fetchall(self):
        return await self._cursor.fetchall()  # type: ignore

    async def commit(self):
        if self._in_transaction:
            await self.connection.commit()  # type: ignore
            self._in_transaction = False

    async def rollback(self):
        if self._in_transaction:
            await self.connection.rollback()  # type: ignore
            self._in_transaction = False
    
    async def query(self, model_cls: Type[Model]):
        from nexios.orm.query import Query
        return Query(self, model_cls)

    async def add(self, instance: "Model"):
        sql, params = instance.save(self.engine.dialect) # type: ignore
        await self.execute(sql, params)

    async def create_all(self, models: list[Type["Model"]]):
        for model in models:
            sql = model.create_table()
            await self.execute(sql)
        await self.commit()
