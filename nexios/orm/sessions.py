from __future__ import annotations

import contextvars
import logging
import threading
from typing import TYPE_CHECKING, Any, Tuple, TypeVar
from typing_extensions import Optional, Type, List
from nexios.orm._model import set_session
from nexios.orm.connection import (
    AsyncDatabaseConnection,
    SyncCursor,
    AsyncCursor,
    SyncDatabaseConnection,
)

if TYPE_CHECKING:
    from nexios.orm.engine import Engine
    from nexios.orm.model import BaseModel
    from nexios.orm.query import Select

_T = TypeVar("_T", bound="BaseModel", covariant=True)

class Session:
    """Synchronous session managing a database transaction.""" 

    def __init__(self, engine: Engine, logger: Optional[logging.Logger] = None):
        from nexios.orm.config import DDLGenerator

        self.engine = engine
        self.connection: Optional[SyncDatabaseConnection] = None
        self._cursor: Optional[SyncCursor] = None
        self.logger = logger or logging.getLogger(__name__)
        self._ddl = DDLGenerator(engine.dialect)

        self._thread_local = threading.local()
        self._thread_local.session = self

    def __enter__(self):
        self.connection = self.engine.connect()
        self._cursor = self.connection.cursor() # type: ignore
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.rollback()
            else:
                self.commit()
        except Exception as e:
            self.logger.error(f"Failed to commit or rollback: {e}")
        finally:
            if self.connection:
                self.engine.return_connection(self.connection)
                self.connection = None
                self._cursor = None

                # Clear thread-local
                if hasattr(self._thread_local, 'session'):
                    delattr(self._thread_local, 'session')
    
    @property
    def _current_session(self):
        return getattr(self._thread_local, 'session', None)

    def exec(self, statement: Select[_T]):
        from nexios.orm.query import SyncResultSet
        return SyncResultSet(statement, self)
    
    def query(self, model: Type[_T]):
        from nexios.orm.query import select
        return select(model)

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
        if self.connection:
            self.connection.commit()

    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def add(self, instance: _T):
        sql, params = self._ddl.upsert(instance.__class__)
        self.execute(sql, params)
    
    def delete(self, model: _T):
        sql = self._ddl.delete(model.__class__)
        self.execute(sql)

    def create_all(self, models: List[Type[_T]]):
        """Create all tables for given models."""
        for model in models:
            sql = self._ddl.create_table(model)
            self.execute(sql)
        self.commit()
    
    def drop(self, model: Type[_T]):
        sql = self._ddl.drop_table(model)
        self.execute(sql)
    
    def refresh(self, model: _T):
        # To be completed TODO
        tbname = model.__orm_config__.table_name
        self.execute(f"SELECT * FROM {tbname}")
        self.fetchone()
    
    def create_indexes(self, model: Type[BaseModel]):
        for index in self._ddl.create_indexes(model):
            self.execute(index)


class AsyncSession:
    """Asynchronous session for async database operations."""

    def __init__(self, engine: Engine):
        from nexios.orm.config import DDLGenerator
        
        self.engine = engine
        self.connection: Optional[AsyncDatabaseConnection] = None
        self._cursor: Optional[AsyncCursor] = None
        self._ddl = DDLGenerator(engine.dialect)

        self._task_local = contextvars.ContextVar('session', default=None)
        self._token = None

    async def __aenter__(self):
        self.connection = await self.engine.async_connect()
        self._cursor = await self.connection.cursor()
        self._token = self._task_local.set(self) # type: ignore
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

                if self._token:
                    self._task_local.reset(self._token)
    
    @property
    def current_session(self):
        return self._task_local.get()
    
    def exec(self, statement: Select[_T]):
        from nexios.orm.query import AsyncResultSet
        return AsyncResultSet(statement, self)
    
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
        if self.connection:
            await self.connection.commit()

    async def rollback(self):
        if self.connection:
            await self.connection.rollback()

    async def add(self, instance: BaseModel):
        # sql, params = instance.save(self.engine.dialect)
        # await self.execute(sql, params)
        sql = self._ddl.create_table(instance.__class__)
        await self.execute(sql)

    async def create_all(self, models: list[Type["BaseModel"]]):
        for basemodel in models:
            # sql = basemodel.create_table()
            # await self.execute(sql)
            sql = self._ddl.create_table(basemodel)
            await self.execute(sql)
        await self.commit()
