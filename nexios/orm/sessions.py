from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Tuple, TypeVar, Optional, Type, List

from nexios.orm.connection import (
    AsyncDatabaseConnection,
    SyncCursor,
    AsyncCursor,
    SyncDatabaseConnection,
)
from nexios.orm.misc.context import set_context_data, reset_context_data

if TYPE_CHECKING:
    from nexios.orm.engine import Engine
    from nexios.orm.model import NexiosModel
    from nexios.orm.query.builder import Select

_T = TypeVar("_T", bound="NexiosModel")

class Session:
    """Synchronous session managing a database transaction.""" 

    def __init__(self, engine: Engine, logger: Optional[logging.Logger] = None):
        from nexios.orm.config import DDLGenerator

        self.engine = engine
        self.connection: Optional[SyncDatabaseConnection] = None
        self._cursor: Optional[SyncCursor] = None
        self.logger = logger or logging.getLogger(__name__)
        self._ddl = DDLGenerator(engine.dialect, self.engine.driver)

        self._token = None

    @property
    def cursor(self) -> SyncCursor:
        """Return the active cursor or raise a helpful error if none exists."""
        if self._cursor is None:
            raise RuntimeError("No active DB cursor. Use 'with Session(engine) as s' or call 'connect()' first.")
        return self._cursor

    def connect(self):
        """Explicitly open a connection and cursor outside a context manager."""
        if self.connection is None:
            self.connection = self.engine.connect()
            self._cursor = self.engine.sync_cursor()
        return self

    def close(self):
        """Close any opened connection and clear the cursor."""
        if self.connection:
            self.engine.return_connection(self.connection)
            self.connection = None
            self._cursor = None

    def __enter__(self):
        sess = self.connect()
        self._token = set_context_data("session", sess)
        return sess

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
                self.close()

                if self._token:
                    reset_context_data("session", self._token)

    def exec(self, statement: Select[_T]):
        from nexios.orm.query.result import SyncResultSet
        return SyncResultSet(statement, self)

    def execute(self, sql: str, params: tuple = ()):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return self.cursor.execute(sql, params)
    
    def executemany(self, sql: str, params: List[Tuple[Any, ...]]):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return self.cursor.executemany(sql, params)

    def commit(self):
        if self.connection:
            self.connection.commit()

    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def add(self, instance: _T):
        from nexios.orm.query.expressions import ColumnExpression
        from nexios.orm.config import MySQLDialect, SQLiteDialect, PostgreSQLDialect

        sql, params = self._ddl.upsert(instance)

        primary_key = self._ddl._get_primary_key(instance)

        if isinstance(primary_key, ColumnExpression):
            primary_key_field = primary_key.field_name
        else:
            primary_key_field = primary_key
        
        fields = instance.get_fields()
        field_info = fields.get(primary_key_field)
        auto_increment = getattr(field_info, 'auto_increment', False) if field_info else False
        if auto_increment:
            if isinstance(self._ddl.dialect, SQLiteDialect):
                self.execute(sql, params)
                result = self.execute("SELECT last_insert_rowid()").fetchone()
                last_id = result[0] if result else None
                setattr(instance, primary_key_field, last_id)
            elif isinstance(self._ddl.dialect, PostgreSQLDialect):
                result = self.execute(sql, params).fetchone()
                last_id = result[0] if result else None
                setattr(instance, primary_key_field, last_id)
            elif isinstance(self._ddl.dialect, MySQLDialect):
                self.execute(sql, params)
                result = self.execute("SELECT LAST_INSERT_ID()").fetchone()
                setattr(instance, primary_key_field, result[0]) if result else None
            else:
                self.execute(sql, params)
        else:
            self.execute(sql, params)
    
    def delete(self, model: _T):
        sql, params = self._ddl.delete(model)
        self.execute(sql, params)

    def create_all(self, *models: Type[_T]):
        """Create all tables for given models."""
        try:
            for model in models:
                sql = self._ddl.create_table(model)
                # Create tables
                self.execute(sql)
                # Create indexes
                index_sql = self._ddl.create_indexes(model)
                for idx in index_sql:
                    self.execute(idx)
            self.commit()
        except Exception as e:
            self.rollback()
            raise e
    
    def drop(self, model: Type[_T]):
        sql = self._ddl.drop_table(model)
        self.execute(sql)

    def update(self):
        pass
    
    def refresh(self, model: _T):
        """
        Refresh the given instance wit the current database state

        Args:
            model: Model instance to refresh
        """
        from nexios.orm.query.expressions import ColumnExpression
        from nexios.orm.query.builder import select


        primary_key = self._ddl._get_primary_key(model)
        if isinstance(primary_key, ColumnExpression):
            primary_key_field = primary_key.field_name
        else:
            primary_key_field = primary_key

        model_class = type(model)
        pk_value = getattr(model, primary_key_field, None)
        if pk_value is None:
            raise ValueError(f"Cannot refresh {model_class.__name__}:primary key is None")

        query = select(model_class).where(getattr(model_class, primary_key_field) == pk_value)
        refreshed = self.exec(query).first()

        if refreshed is None:
            raise ValueError(f"{model_class.__name__} with {primary_key_field}={pk_value} no longer exists")

        for field_name in model.get_fields().keys():
            new_value = getattr(refreshed, field_name, None)
            setattr(model, field_name, new_value)


class AsyncSession:
    """Asynchronous session for async database operations."""

    def __init__(self, engine: Engine, logger: Optional[logging.Logger] = None):
        from nexios.orm.config import DDLGenerator
        
        self.engine = engine
        self.connection: Optional[AsyncDatabaseConnection] = None
        self._cursor: Optional[AsyncCursor] = None
        self.logger = logger or logging.getLogger(__name__)
        self._ddl = DDLGenerator(engine.dialect, self.engine.driver)

        self._token = None

    @property
    def cursor(self) -> AsyncCursor:
        """Return the active async cursor or raise a helpful error if none exists."""
        if self._cursor is None:
            raise RuntimeError("No active async DB cursor. Use 'async with AsyncSession(engine) as s' or call 'await connect()' first.")
        return self._cursor

    async def connect(self):
        """Explicitly open an async connection and cursor outside of an async context manager."""
        if self.connection is None:
            self.connection = await self.engine.async_connect()
            self._cursor = await self.connection.cursor()
        return self

    async def close(self):
        """Close any opened async connection and clear the cursor."""
        if self.connection:
            await self.engine.return_async_connection(self.connection)
            self.connection = None
            self._cursor = None

    async def __aenter__(self):
        sess = await self.connect()
        self._token = set_context_data("session", sess)
        return sess

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                await self.rollback()
            else:
                await self.commit()
        finally:
            if self.connection:
                await self.close()

                if self._token:
                    reset_context_data("session", self._token)
    
    def exec(self, statement: Select[_T]):
        from nexios.orm.query.result import AsyncResultSet
        return AsyncResultSet(statement, self)
    
    async def execute(self, sql: str, params: tuple = ()):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return await self.cursor.execute(sql, params)
    
    async def executemany(self, sql: str, params: List[Tuple[Any, ...]]):
        if self.engine.echo:
            print("SQL:", sql, "params:", params)
        return await self.cursor.executemany(sql, params)

    async def commit(self):
        if self.connection:
            await self.connection.commit()

    async def rollback(self):
        if self.connection:
            await self.connection.rollback()

    async def add(self, instance: NexiosModel):
        from nexios.orm.query.expressions import ColumnExpression
        from nexios.orm.config import MySQLDialect, SQLiteDialect, PostgreSQLDialect

        sql, params = self._ddl.upsert(instance)

        primary_key = self._ddl._get_primary_key(instance)
        if isinstance(primary_key, ColumnExpression):
            primary_key_field = primary_key.field_name
        else:
            primary_key_field = primary_key

        fields = instance.get_fields()
        field_info = fields.get(primary_key_field)
        auto_increment = getattr(field_info, 'auto_increment', False) if field_info else False
        if auto_increment:
            if isinstance(self._ddl.dialect, SQLiteDialect):
                await self.execute(sql, params)
                result = await (await self.execute("SELECT last_insert_rowid()")).fetchone()
                last_id = result[0] if result else None
                setattr(instance, primary_key_field, last_id)
            elif isinstance(self._ddl.dialect, PostgreSQLDialect):
                result = await (await self.execute(sql, params)).fetchone()
                last_id = result[0] if result else None
                setattr(instance, primary_key_field, last_id)
            elif isinstance(self._ddl.dialect, MySQLDialect):
                exec_stmt = await self.execute(sql, params)
                last_id = getattr(exec_stmt, 'last_id', None)
                setattr(instance, primary_key_field, last_id)
            else:
                await self.execute(sql, params)
        else:
            await self.execute(sql, params)

    async def delete(self, model: _T):
        sql, params = self._ddl.delete(model)
        await self.execute(sql, params)

    async def create_all(self, *models: Type[_T]):
        try:
            for nexiosmodel in models:
                sql = self._ddl.create_table(nexiosmodel)
                # Create tables
                await self.execute(sql)
                # Create indexes
                index_sql = self._ddl.create_indexes(nexiosmodel)
                for idx in index_sql:
                    await self.execute(idx)
            await self.commit()
        except Exception as e:
            await self.rollback()
            raise e

    async def drop(self, model: Type[_T]):
        sql = self._ddl.drop_table(model)
        await self.execute(sql)

    async def refresh(self, model: _T):
        """
        Refresh the given instance wit the current database state

        Args:
            model: Model instance to refresh
        """
        from nexios.orm.query.expressions import ColumnExpression
        from nexios.orm.query.builder import select

        primary_key = self._ddl._get_primary_key(model)
        if isinstance(primary_key, ColumnExpression):
            primary_key_field = primary_key.field_name
        else:
            primary_key_field = primary_key

        model_class = type(model)
        pk_value = getattr(model, primary_key_field, None)
        if pk_value is None:
            raise ValueError(f"Cannot refresh {model_class.__name__}:primary key is None")

        query = select(model_class).where(getattr(model_class, primary_key_field) == pk_value)
        refreshed = await self.exec(query).first()

        if refreshed is None:
            raise ValueError(f"{model_class.__name__} with {primary_key_field}={pk_value} no longer exists")

        for field_name in model.get_fields().keys():
            new_value = getattr(refreshed, field_name, None)
            setattr(model, field_name, new_value)
