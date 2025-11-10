# This module calls out all the specific implementations for Postgres dialect.
# including asyncpg, pg8000, psycopg2, psycopg3, and others.
from typing import Any, Optional

import asyncpg
import psycopg
import psycopg2

from nexios.orm.backends.dialects.postgres.async_psycopg_ import AsyncPsycopgConnection
from nexios.orm.backends.dialects.postgres.asyncpg_ import AsyncPgConnection
from nexios.orm.backends.dialects.postgres.psycopg2_ import Psycopg2Connection
from nexios.orm.backends.dialects.postgres.psycopg_ import PsycopgConnection
from nexios.orm.connection import AsyncDatabaseConnection, SyncDatabaseConnection

class PostgresConnection:
    
    @staticmethod
    def connect(connection: Any) -> Optional["SyncDatabaseConnection"]:
        if isinstance(connection, psycopg2.extensions.connection):
            return Psycopg2Connection(connection)
        elif isinstance(connection, psycopg.Connection):
            return PsycopgConnection(connection)
        else:
            return None
        
    @staticmethod
    async def connect_async(connection: Any) -> Optional["AsyncDatabaseConnection"]:
        if isinstance(connection, psycopg.AsyncConnection):
            return AsyncPsycopgConnection(connection)
        elif isinstance(connection, asyncpg.Connection):
            return AsyncPgConnection(connection)
        return None