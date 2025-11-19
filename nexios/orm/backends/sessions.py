from typing import Any, Tuple, TypeVar
from typing_extensions import Optional, Type, List
from nexios.orm.connection import (
    AsyncDatabaseConnection,
    SyncCursor,
    AsyncCursor,
    SyncDatabaseConnection,
)
from nexios.orm.backends.engine import Engine
from nexios.orm.model import Model
from nexios.orm.query import Select, select

_T = TypeVar("_T", bound="Model")

class Session:
    """Synchronous session managing a database transaction.""" 

    def __init__(self, engine: Engine):
        self.engine = engine
        self.connection: Optional[SyncDatabaseConnection] = None
        self._cursor: Optional[SyncCursor] = None
        self._in_transaction = False

    def __enter__(self):
        self.connection = self.engine.connect()
        self._cursor = self.connection.cursor() # type: ignore
        self._in_transaction = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            if self.connection:
                print(f"DEBUG: Returning connection, transaction state: {self._in_transaction}")  # DEBUG
                self.engine.return_connection(self.connection)
                self.connection = None
                self._cursor = None

    def exec(self, statement: Select[_T]) -> List[_T]:
        return statement.bind(self).all()
    
    def select(self, *entities: Any) -> Select[_T]:
        stmt = select(*entities)
        return stmt.bind(self)

    def execute(self, sql: str, params: tuple = ()):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return self._cursor.execute(sql, params)  # type: ignore
    
    def executemany(self, sql: str, params: List[Tuple[Any, ...]]):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return self._cursor.executemany(sql, params) # type: ignore

    def fetchone(self):
        return self._cursor.fetchone()  # type: ignore

    def fetchall(self):
        return self._cursor.fetchall()  # type: ignore
    
    def fetchmany(self, size: int):
        return self._cursor.fetchmany(size) # type: ignore

    def commit(self):
        if self._in_transaction and self.connection:
            self.connection.commit()  # type: ignore
            self._in_transaction = False

    def rollback(self):
        if self._in_transaction and self.connection:
            self.connection.rollback()  # type: ignore
            self._in_transaction = False

    def add(self, instance: "Model"):
        sql, params = instance.save(self.engine.dialect)
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
        self.connection = await self.engine.async_connect()
        self._cursor = await self.connection.cursor()
        self._in_transaction = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                await self.rollback()
            else:
                await self.commit()
        finally:
            if self.connection:
                await self.engine.return_async_connection(self.connection)
                self.connection = None
                self._cursor = None
    
    async def exec(self, statement: Select[_T]) -> List[_T]:
        return await statement.bind(self).all_async()
    
    def select(self, *entities: Any) -> Select[_T]:
        stmt = select(*entities)
        return stmt.bind(self)
    
    async def execute(self, sql: str, params: tuple = ()):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return await self._cursor.execute(sql, params)  # type: ignore
    
    async def executemany(self, sql: str, params: List[Tuple[Any, ...]]):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return await self._cursor.executemany(sql, params) # type: ignore

    async def fetchone(self):
        return await self._cursor.fetchone()  # type: ignore

    async def fetchall(self):
        return await self._cursor.fetchall()  # type: ignore
    
    async def fetchmany(self, size: int):
        return await self._cursor.fetchmany(size) # type: ignore

    async def commit(self):
        if self._in_transaction and self.connection:
            await self.connection.commit()  # type: ignore
            self._in_transaction = False

    async def rollback(self):
        if self._in_transaction and self.connection:
            await self.connection.rollback()  # type: ignore
            self._in_transaction = False

    async def add(self, instance: "Model"):
        sql, params = instance.save(self.engine.dialect) # type: ignore
        await self.execute(sql, params)

    async def create_all(self, models: list[Type["Model"]]):
        for model in models:
            sql = model.create_table()
            await self.execute(sql)
        await self.commit()
