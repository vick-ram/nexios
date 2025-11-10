# This module calls out all the specific implementations for Postgres dialect.
# including asyncpg, pg8000, psycopg2, psycopg3, and others.
import asyncio
from typing import Any, Optional, Tuple, Union

import asyncpg
import psycopg
import psycopg2


class PostgresConnection:
    def __init__(self, connection: Union[psycopg.Connection, psycopg.AsyncConnection, psycopg2.extensions.connection, asyncpg.Connection]) -> None:
        self._connection = connection
    
    def connect(self):
        if isinstance(self._connection, psycopg2.extensions.connection):
            # Handle psycopg2 connection
            psycopg2.connect(**self.kwargs)
        elif isinstance(self._connection, psycopg.Connection):
            # Handle psycopg3 connection
            self._connection.connect(**self.kwargs)
        elif isinstance(self._connection, psycopg.AsyncConnection):
            # Handle asyncpg connection
            asyncio.run(self._connection.connect(**self.kwargs))
        elif isinstance(self._connection, asyncpg.Connection):
            # Handle asyncpg connection
            asyncio.run(asyncpg.connect(**self.kwargs))