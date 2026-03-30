from typing import Optional

import pytest

from nexios.orm.engine import create_engine, Engine
from nexios.orm.model import NexiosModel
from nexios.orm.sessions import Session, AsyncSession

DATABASE_CONFIGS = {
    'postgres': {
        'host': 'localhost',
        'port': 5432,
        'user': 'vickram',
        'password': 'Vickram9038',
        'dbname': 'nexios'
    },
    'mysql': {
        'host': 'localhost',
        'port': 3306,
        'user': 'vickram',
        'password': 'Vickram9038',
        'database': 'nexios'
    },
    'sqlite': {
        'database': 'nexios.db'
    }
}

@pytest.fixture(params=['postgres', 'sqlite', 'mysql'])
def sync_session(request: pytest.FixtureRequest):

    import sys
    sys.stdout.flush()

    engine: Optional[Engine] = None

    from nexios.orm.config import PostgreSQLDialect, MySQLDialect

    config = DATABASE_CONFIGS[request.param]

    if request.param == 'postgres':
        try:
            # import psycopg
            import asyncpg
            engine = create_engine(echo=True, **config, use_pool=False)
        except ImportError:
            pytest.skip('psycopg not installed')
        except Exception as e:
            pytest.skip(str(e))
    elif request.param == 'mysql':
        try:
            import pymysql # noqa
            engine = create_engine(echo=True, **config, use_pool=False)
        except ImportError:
            pytest.skip("MySQL driver not installed")
        except Exception as e:
            pytest.skip(f"MySQL not available: {e}")
    else:  # sqlite
        engine = create_engine(echo=True, **config)


    with Session(engine) as sess:
        for table in ('posts', 'addresses', 'profiles', 'users'):

            dialect = engine.dialect

            if isinstance(dialect, PostgreSQLDialect):
                sess.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            elif isinstance(dialect, MySQLDialect):
                sess.execute("SET FOREIGN_KEY_CHECKS = 0")
                sess.execute(f"DROP TABLE IF EXISTS {table}")
                sess.execute(f"SET FOREIGN_KEY_CHECKS = 1")
            else:
                sess.execute("PRAGMA foreign_keys = 1")
                sess.execute(f"DROP TABLE IF EXISTS {table}")
                sess.execute("PRAGMA foreign_keys = 1")
        sess.commit()

        yield sess


@pytest.fixture(params=['postgres', 'mysql', 'sqlite'])
async def async_session(request):
    """Create an async session for different databases"""
    from nexios.orm.config import PostgreSQLDialect, MySQLDialect

    engine: Optional[Engine] = None

    config = DATABASE_CONFIGS[request.param]

    if request.param == 'postgres':
        try:
            # import asyncpg
            import psycopg
            engine = create_engine(echo=True, **config, use_pool=False)
        except ImportError:
            pytest.skip("asyncpg not installed")
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
    elif request.param == 'mysql':
        try:
            import aiomysql
            engine = create_engine(echo=True, **config, use_pool=False)
        except ImportError:
            pytest.skip("AIOMySQL driver not installed")
        except Exception as e:
            pytest.skip(f"AIOMySQL not available: {e}")
    else:  # sqlite
        try:
            import aiosqlite
            engine = create_engine(echo=True, **config, use_pool=False)
        except ImportError:
            pytest.skip("aiosqlite not installed")

    async with AsyncSession(engine) as session:
        # Clean up
        for table in ('posts', 'addresses', 'profiles', 'users'):
            dialect = engine.dialect

            if isinstance(dialect, PostgreSQLDialect):
                await session.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            elif isinstance(dialect, MySQLDialect):
                await session.execute("SET FOREIGN_KEY_CHECKS = 0")
                await session.execute(f"DROP TABLE IF EXISTS {table}")
                await session.execute(f"SET FOREIGN_KEY_CHECKS = 1")
            else:
                await session.execute("PRAGMA foreign_keys = 1")
                await session.execute(f"DROP TABLE IF EXISTS {table}")
                await session.execute("PRAGMA foreign_keys = 1")

        await session.commit()

        yield session

class BaseTestModel(NexiosModel):
    """Base model for testing with common functionality"""

    @classmethod
    def create_table(cls, session):
        session.create_all([cls])

    @classmethod
    def drop_table(cls, session):
        session.drop(cls)

    @classmethod
    def count(cls, session):
        from nexios.orm.query.builder import select
        query = select(cls)
        return session.exec(query).count()
