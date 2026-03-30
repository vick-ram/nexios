# from __future__ import annotations

# import inspect
# import logging
# import os
# import sys
# from datetime import datetime
# from enum import Enum
# from typing import Dict, List, Optional, Type, Union, Any, Tuple
# from nexios.orm.config import (
#     SQLiteDialect,
#     generate_placeholders,
#     get_param_placeholder,
# )
# from nexios.orm.misc.event_loop import NexiosEventLoop
# from nexios.orm.model import NexiosModel
# from nexios.orm.sessions import AsyncSession, Session


# class MigrationStatus(Enum):
#     RUNNING = "running"
#     COMPLETED = "completed"
#     FAILED = "failed"
#     ROLLED_BACK = "rolled_back"


# class Migration:
#     def __init__(
#         self, name: str, version: str, up_sql: str, down_sql: str = ""
#     ) -> None:
#         self.name = name
#         self.version = version
#         self.up_sql = up_sql
#         self.down_sql = down_sql
#         self.created_at = datetime.now()
#         self.checksum: Optional[str] = None
    
#     def compute_checksum(self) -> str:
#         import hashlib

#         content = f"{self.name}{self.version}{self.up_sql}{self.down_sql}"
#         return hashlib.md5(content.encode("utf-8")).hexdigest()

# class MigrationManager:
#     def __init__(self, session: Union[Session, AsyncSession]) -> None:
#         self.logger: logging.Logger = logging.getLogger(__name__)
#         self.session = session
#         self.migrations: Dict[str, Migration] = {}
#         self._migrations_table_created = False
#         self._loop = NexiosEventLoop()
#         self.__is_async = isinstance(self.session, AsyncSession)

#         self._load_migrations()
    
#     def _load_migrations(self) -> None:
#         migration_dir = "migrations"
#         if not os.path.exists(migration_dir):
#             return
        
#         for filename in os.listdir(migration_dir):
#             if filename.endswith(".py"):
#                 try:
#                     module_path = os.path.join(migration_dir, filename)
#                     import importlib.util
#                     spec = importlib.util.spec_from_file_location(f"migrations.{filename[:-3]}", module_path)
#                     if spec and spec.loader:
#                         module = importlib.util.module_from_spec(spec)
#                         spec.loader.exec_module(module)

#                         if hasattr(module, "get_migration"):
#                             migration = module.get_migration()
#                             self.add_migration(migration)
#                 except Exception as e:
#                     self.logger.warning(f"Failed to load migration {filename}: {e}")

#     def _execute(self, sql: str, params: Tuple[Any, ...] = ()):
#         async def execute_async(sess: AsyncSession):
#             return await sess.execute(sql, params)

#         if isinstance(self.session, AsyncSession):
#             return self._loop.run(execute_async(self.session))
#         else:
#             return self.session.execute(sql, params)

#     def _ensure_migrations_table(self) -> None:
#         """
#         Create migrations table if it doesn't exist
#         """
#         if self._migrations_table_created:
#             return

#         create_table_sql = """
#             CREATE TABLE IF NOT EXISTS _migrations (
#                 version TEXT PRIMARY KEY,
#                 name TEXT NOT NULL,
#                 applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 status TEXT NOT NULL,
#                 checksum TEXT,
#                 execution_time INTEGER
#             )
#             """

#         try:
#             self._execute(create_table_sql)
#             self._migrations_table_created = True
#             self.logger.debug("Migrations table ensured")
#         except Exception as e:
#             self.logger.error(f"Failed to create migrations table: {e}")
#             raise

#     def _scan_models(self) -> List[Type[NexiosModel]]:
#         models = []

#         for module_name, module in sys.modules.items():
#             if not module or module_name.startswith(("_", "builtins", "sys")):
#                 continue

#             try:
#                 is_table = (
#                     NexiosModel.model_config.get("table")
#                     or NexiosModel.__tablename__ is not None
#                 )
#                 for _, obj in inspect.getmembers(module, inspect.isclass):
#                     if (
#                         issubclass(obj, NexiosModel)
#                         and obj != NexiosModel
#                         and is_table
#                         and obj.__module__ == module_name
#                     ):
#                         models.append(obj)
#             except (ImportError, TypeError, AttributeError):
#                 continue

#         return models

#     def add_migration(self, migration: Migration) -> None:
#         """Register a migration"""
#         if migration.version in self.migrations:
#             self.logger.warning(f"Migration {migration.version} already registered")
#         self.migrations[migration.version] = migration

#     def _up_sql_migration(self):
#         models = self._scan_models()
#         ddl = self.session._ddl
#         statements = []

#         for model in models:
#             create_table_sql = ddl.create_table(model)
#             statements.append(create_table_sql)
        
#         return "\n".join(statements)
    
#     def _down_sql_migration(self):
#         models = self._scan_models()
#         ddl = self.session._ddl
#         statements = []

#         for model in models:
#             drop_table_sql = ddl.drop_table(model)
#             statements.append(drop_table_sql)

#         return "\n".join(statements)

#     def create_migration(self, name: str) -> str:
#         """Create a migration file"""
#         timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#         version = f"{timestamp}_{name}"

#         # Create migration directory if it doesn't exist
#         os.makedirs("migrations", exist_ok=True)

#         # Create migration file
#         migration_file = f"migrations/{version}.py"
#         template = f'''"""
#             Migration: {name}
#             Version: {version}
#             Created:{datetime.now()}
#         """
#             def get_migration():
#                 return Migration(
#                     name="{name}",
#                     version="{version}",
#                     up_sql="""
#                         -- Add your UP Migration SQL here
#                         {self._up_sql_migration()}
#                     """,
#                     down_sql="""
#                         -- Add your DOWN Migration SQL here
#                         {self._down_sql_migration()}
#                     """ 
#                 )
#         '''
#         try:
#             with open(migration_file, "w") as f:
#                 f.write(template)
            
#             self.logger.info(f"Created migration file: {migration_file}")
            
#             # Reload migrations
#             self._load_migrations()
            
#             return migration_file
#         except Exception as e:
#             self.logger.error(f"Failed to create migration file: {e}")
#             raise

#     def get_applied_migrations(self) -> List[Dict[str, Any]]:
#         """Get list of applied migrations"""
#         self._ensure_migrations_table()
#         # sql = "SELECT version FROM _migrations WHERE status = 'completed' ORDER BY version"
#         sql = """
#             SELECT version, name, applied_at, status, checksum 
#             FROM _migrations 
#             ORDER BY version
#         """

#         try:
#             async def async_fetch(sess: AsyncSession):
#                 result = await sess.execute(sql)
#                 return await result.fetchall()

#             if self.__is_async:
#                 rows = self._loop.run(async_fetch(self.session)) # type: ignore
#             else:
#                 rows = self.session.execute(sql).fetchall() # type: ignore

#             return [
#                 {
#                     "version": row[0],
#                     "name": row[1],
#                     "applied_at": row[2],
#                     "status": row[3],
#                     "checksum": row[4]
#                 }
#                 for row in rows
#             ]
#         except Exception as e:
#             self.logger.error(f"Failed to get applied migrations: {e}")
#             return []
    

#     def migrate(
#         self,
#         target_version: Optional[str] = None,
#     ) -> None:
#         """Run all pending migrations"""
#         self._ensure_migrations_table()

#         applied = {m["version"] for m in self.get_applied_migrations()
#                    if m["status"] == MigrationStatus.COMPLETED.value}
        
#         pending: List[Migration] = []
#         for version in sorted(self.migrations.keys()):
#             if version not in applied:
#                 pending.append(self.migrations[version])
#         if target_version:
#             pending = [m for m in pending if m.version <= target_version]

#         if not pending:
#             self.logger.info("No pending migrations to apply.")
#             return
        
#         self.logger.info(f"Found {len(pending)} pending migrations.")
        
#         for migration in pending:
#             self.logger.info(
#                 f"Applying migration: {migration.name} ({migration.version})"
#             )

#             start_time = datetime.now()
#             placeholder = get_param_placeholder(driver=self.session.engine.driver)
#             placeholders = generate_placeholders(
#                 driver=self.session.engine.driver, count=4, start_index=1
#             )

#             try:
#                 # Record migratioon start
#                 self._execute(
#                     f"INSERT OR REPLACE INTO _migrations (version, name, status, checksum) VALUES ({placeholders})",
#                     (migration.version, migration.name, MigrationStatus.RUNNING.value, migration.compute_checksum()),
#                 )

#                 # Execute migration SQL
#                 if migration.up_sql.strip():
#                     statements = [
#                         stmt.strip()
#                         for stmt in migration.up_sql.split(";")
#                         if stmt.strip()
#                     ]
#                     for statement in statements:
#                         if statement:
#                             self._execute(statement)
#                 execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

#                 # Mark as completed
#                 self._execute(
#                         f"UPDATE _migrations SET status = {placeholder}, "
#                         f"execution_time = {placeholder} WHERE version = {placeholder}",
#                         (
#                             MigrationStatus.COMPLETED.value,
#                             execution_time,
#                             migration.version
#                         )
#                     )
#                 self.logger.info(f"✓ Applied migration: {migration.name} in {execution_time} ms")

#             except Exception as e:
#                 # Mark as failed
#                 self._execute(
#                     f"UPDATE _migrations SET status = {placeholder} WHERE version = {placeholder}",
#                     (MigrationStatus.FAILED.value, migration.version),
#                 )
#                 self.logger.error(f"✗ Failed to apply migration {migration.name}: {e}")
#                 raise

#     def rollback(
#         self,
#         steps: int = 1,
#         target_version: Optional[str] = None,
#     ) -> None:
#         """Rollbak migrations"""
#         self._ensure_migrations_table()
        
#         applied_migrations = self.get_applied_migrations()
#         completed_migrations = [
#             m for m in applied_migrations 
#             if m["status"] == MigrationStatus.COMPLETED.value
#         ]
        
#         to_rollback: List[Migration] = []
#         count = 0
        
#         for migration_info in reversed(completed_migrations):
#             migration = self.migrations.get(migration_info["version"])
#             if migration and migration.down_sql.strip():
#                 to_rollback.append(migration)
#                 count += 1
#                 if (target_version and migration.version <= target_version) or count >= steps:
#                     break
        
#         if not to_rollback:
#             self.logger.info("No migrations to rollback")
#             return
        
#         self.logger.info(f"Rolling back {len(to_rollback)} migrations")
        
#         for migration in to_rollback:
#             self.logger.info(f"Rolling back migration: {migration.name} ({migration.version})")
            
#             try:
#                 # Execute rollback SQL if not faking
#                 if migration.down_sql.strip():
#                     statements = [
#                         stmt.strip()
#                         for stmt in migration.down_sql.split(";")
#                         if stmt.strip()
#                     ]
#                     for statement in statements:
#                         if statement:  # Skip empty statements
#                             self._execute(statement)
                
#                 # Mark as rolled back
#                 driver = getattr(self.session.engine, 'driver', 'sqlite3')
#                 placeholder = get_param_placeholder(driver)
                
#                 self._execute(
#                     f"UPDATE _migrations SET status = {placeholder} "
#                     f"WHERE version = {placeholder}",
#                     (MigrationStatus.ROLLED_BACK.value, migration.version)
#                 )
                
#                 self.logger.info(f"✓ Rolled back migration: {migration.name}")
                
#             except Exception as e:
#                 self.logger.error(f"✗ Failed to rollback migration {migration.name}: {e}")
#                 raise

#     def status(self) -> Dict[str, Any]:
#         """Get migration status."""
#         self._ensure_migrations_table()
        
#         try:
#             applied_migrations = self.get_applied_migrations()
#             applied_versions = {
#                 m["version"] for m in applied_migrations 
#                 if m["status"] == MigrationStatus.COMPLETED.value
#             }
#             all_versions = set(self.migrations.keys())
            
#             return {
#                 "applied": len(applied_versions),
#                 "pending": len(all_versions - applied_versions),
#                 "rolled_back": len([
#                     m for m in applied_migrations 
#                     if m["status"] == MigrationStatus.ROLLED_BACK.value
#                 ]),
#                 "failed": len([
#                     m for m in applied_migrations 
#                     if m["status"] == MigrationStatus.FAILED.value
#                 ]),
#                 "total": len(all_versions),
#                 "migrations": applied_migrations
#             }
#         except Exception as e:
#             self.logger.error(f"Failed to get migration status: {e}")
#             return {
#                 "applied": 0,
#                 "pending": 0,
#                 "rolled_back": 0,
#                 "failed": 0,
#                 "total": 0,
#                 "migrations": [],
#                 "error": str(e)
#             }
    
#     def validate(self) -> List[str]:
#         """Validate applied migrations against current files."""
#         self._ensure_migrations_table()
        
#         issues = []
#         applied_migrations = self.get_applied_migrations()
        
#         for applied in applied_migrations:
#             migration = self.migrations.get(applied["version"])
            
#             if not migration:
#                 issues.append(f"Migration {applied['version']} is applied but not found in files")
#                 continue
            
#             if applied.get("checksum"):
#                 file_checksum = migration.compute_checksum()
#                 if file_checksum != applied["checksum"]:
#                     issues.append(
#                         f"Migration {applied['version']} checksum mismatch. "
#                         f"Applied: {applied['checksum']}, File: {file_checksum}"
#                     )
        
#         return issues

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type, Union

from nexios.orm.config import generate_placeholders, get_param_placeholder
from nexios.orm.misc.event_loop import NexiosEventLoop
from nexios.orm.model import NexiosModel
from nexios.orm.sessions import AsyncSession, Session


class MigrationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class Migration:
    name: str
    version: str
    up_sql: str
    down_sql: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def checksum(self) -> str:
        payload = f"{self.name}|{self.version}|{self.up_sql}|{self.down_sql}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MigrationError(Exception):
    pass


class MigrationValidationError(MigrationError):
    pass


class MigrationExecutionError(MigrationError):
    pass


class MigrationLoader:
    def __init__(self, migrations_dir: Union[str, Path], logger: logging.Logger) -> None:
        self.migrations_dir = Path(migrations_dir)
        self.logger = logger

    def load(self) -> Dict[str, Migration]:
        migrations: Dict[str, Migration] = {}

        if not self.migrations_dir.exists():
            return migrations

        files = sorted(
            f for f in self.migrations_dir.iterdir()
            if f.is_file() and f.suffix == ".py" and not f.name.startswith("_")
        )

        for file_path in files:
            migration = self._load_single(file_path)

            if migration.version in migrations:
                raise MigrationValidationError(
                    f"Duplicate migration version detected: {migration.version}"
                )

            migrations[migration.version] = migration

        return migrations

    def _load_single(self, file_path: Path) -> Migration:
        module_name = f"migrations.{file_path.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if spec is None or spec.loader is None:
                raise MigrationValidationError(f"Could not load spec for {file_path.name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "get_migration"):
                raise MigrationValidationError(
                    f"{file_path.name} does not define get_migration()"
                )

            migration = module.get_migration()

            if not isinstance(migration, Migration):
                raise MigrationValidationError(
                    f"{file_path.name} get_migration() must return Migration"
                )

            return migration

        except Exception as exc:
            raise MigrationValidationError(
                f"Failed to load migration '{file_path.name}': {exc}"
            ) from exc


class SessionAdapter:
    """
    Thin wrapper over sync/async session behavior.

    Assumptions:
    - execute(sql, params) works for both Session and AsyncSession
    - sync session may expose begin/commit/rollback
    - async session may expose begin/commit/rollback as coroutines
    """

    def __init__(self, session: Union[Session, AsyncSession]) -> None:
        self.session = session
        self._loop = NexiosEventLoop()
        self.is_async = isinstance(session, AsyncSession)

    @property
    def driver(self) -> str:
        return getattr(getattr(self.session, "engine", None), "driver", "sqlite3")

    @property
    def ddl(self) -> Any:
        return getattr(self.session, "_ddl", None)

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> Any:
        if self.is_async:
            async def _run() -> Any:
                return await self.session.execute(sql, params)  # type: ignore[arg-type]
            return self._loop.run(_run())

        return self.session.execute(sql, params)  # type: ignore[arg-type]

    def fetchall(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Any]:
        if self.is_async:
            async def _run() -> List[Any]:
                result = await self.session.execute(sql, params)  # type: ignore[arg-type]
                return await result.fetchall()
            return self._loop.run(_run())

        result = self.session.execute(sql, params)  # type: ignore[arg-type]
        return result.fetchall()

    def begin(self) -> None:
        begin_fn = getattr(self.session, "begin", None)
        if begin_fn is None:
            return

        if self.is_async:
            async def _run() -> None:
                maybe = begin_fn()
                if inspect.isawaitable(maybe):
                    await maybe
            self._loop.run(_run())
            return

        maybe = begin_fn()
        if inspect.isawaitable(maybe):
            raise RuntimeError("Sync path received awaitable begin()")

    def commit(self) -> None:
        commit_fn = getattr(self.session, "commit", None)
        if commit_fn is None:
            return

        if self.is_async:
            async def _run() -> None:
                maybe = commit_fn()
                if inspect.isawaitable(maybe):
                    await maybe
            self._loop.run(_run())
            return

        maybe = commit_fn()
        if inspect.isawaitable(maybe):
            raise RuntimeError("Sync path received awaitable commit()")

    def rollback(self) -> None:
        rollback_fn = getattr(self.session, "rollback", None)
        if rollback_fn is None:
            return

        if self.is_async:
            async def _run() -> None:
                maybe = rollback_fn()
                if inspect.isawaitable(maybe):
                    await maybe
            self._loop.run(_run())
            return

        maybe = rollback_fn()
        if inspect.isawaitable(maybe):
            raise RuntimeError("Sync path received awaitable rollback()")


class MigrationRepository:
    TABLE_NAME = "_migrations"

    def __init__(self, db: SessionAdapter, logger: logging.Logger) -> None:
        self.db = db
        self.logger = logger
        self._ensured = False

    def ensure_table(self) -> None:
        if self._ensured:
            return

        sql = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TIMESTAMP NULL,
            execution_time INTEGER NULL
        )
        """.strip()

        self.db.execute(sql)
        self._ensured = True

    def all(self) -> List[Dict[str, Any]]:
        self.ensure_table()

        rows = self.db.fetchall(
            f"""
            SELECT version, name, status, checksum, applied_at, execution_time
            FROM {self.TABLE_NAME}
            ORDER BY version
            """.strip()
        )

        return [
            {
                "version": row[0],
                "name": row[1],
                "status": row[2],
                "checksum": row[3],
                "applied_at": row[4],
                "execution_time": row[5],
            }
            for row in rows
        ]

    def by_version(self, version: str) -> Optional[Dict[str, Any]]:
        self.ensure_table()

        rows = self.db.fetchall(
            f"""
            SELECT version, name, status, checksum, applied_at, execution_time
            FROM {self.TABLE_NAME}
            WHERE version = {get_param_placeholder(self.db.driver)}
            """.strip(),
            (version,),
        )

        if not rows:
            return None

        row = rows[0]
        return {
            "version": row[0],
            "name": row[1],
            "status": row[2],
            "checksum": row[3],
            "applied_at": row[4],
            "execution_time": row[5],
        }

    def record_running(self, migration: Migration) -> None:
        existing = self.by_version(migration.version)

        if existing is None:
            placeholders = generate_placeholders(
                driver=self.db.driver,
                count=4,
                start_index=1,
            )
            self.db.execute(
                f"""
                INSERT INTO {self.TABLE_NAME} (version, name, status, checksum)
                VALUES ({placeholders})
                """.strip(),
                (
                    migration.version,
                    migration.name,
                    MigrationStatus.RUNNING.value,
                    migration.checksum(),
                ),
            )
            return

        p = get_param_placeholder(self.db.driver)
        self.db.execute(
            f"""
            UPDATE {self.TABLE_NAME}
            SET name = {p},
                status = {p},
                checksum = {p},
                applied_at = NULL,
                execution_time = NULL
            WHERE version = {p}
            """.strip(),
            (
                migration.name,
                MigrationStatus.RUNNING.value,
                migration.checksum(),
                migration.version,
            ),
        )

    def record_completed(self, migration: Migration, execution_time_ms: int) -> None:
        p = get_param_placeholder(self.db.driver)
        self.db.execute(
            f"""
            UPDATE {self.TABLE_NAME}
            SET status = {p},
                applied_at = CURRENT_TIMESTAMP,
                execution_time = {p},
                checksum = {p}
            WHERE version = {p}
            """.strip(),
            (
                MigrationStatus.COMPLETED.value,
                execution_time_ms,
                migration.checksum(),
                migration.version,
            ),
        )

    def record_failed(self, migration: Migration) -> None:
        p = get_param_placeholder(self.db.driver)
        self.db.execute(
            f"""
            UPDATE {self.TABLE_NAME}
            SET status = {p}
            WHERE version = {p}
            """.strip(),
            (
                MigrationStatus.FAILED.value,
                migration.version,
            ),
        )

    def record_rolled_back(self, migration: Migration) -> None:
        p = get_param_placeholder(self.db.driver)
        self.db.execute(
            f"""
            UPDATE {self.TABLE_NAME}
            SET status = {p}
            WHERE version = {p}
            """.strip(),
            (
                MigrationStatus.ROLLED_BACK.value,
                migration.version,
            ),
        )


class MigrationManager:
    def __init__(
        self,
        session: Union[Session, AsyncSession],
        migrations_dir: Union[str, Path] = "migrations",
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db = SessionAdapter(session)
        self.repo = MigrationRepository(self.db, self.logger)
        self.loader = MigrationLoader(migrations_dir, self.logger)
        self.migrations_dir = Path(migrations_dir)
        self.migrations: Dict[str, Migration] = self.loader.load()

    def reload(self) -> None:
        self.migrations = self.loader.load()

    def add_migration(self, migration: Migration) -> None:
        if migration.version in self.migrations:
            raise MigrationValidationError(
                f"Migration version already registered: {migration.version}"
            )
        self.migrations[migration.version] = migration

    def _scan_models(self) -> List[Type[NexiosModel]]:
        models: List[Type[NexiosModel]] = []

        for module_name, module in list(sys.modules.items()):
            if not module or module_name.startswith(("_", "builtins", "sys")):
                continue

            try:
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if not issubclass(obj, NexiosModel) or obj is NexiosModel:
                        continue

                    if obj.__module__ != module_name:
                        continue

                    is_table = bool(
                        getattr(obj, "model_config", {}).get("table")
                        or getattr(obj, "__tablename__", None)
                    )
                    if is_table:
                        models.append(obj)

            except (ImportError, TypeError, AttributeError):
                continue

        # De-duplicate while preserving deterministic order
        unique: Dict[str, Type[NexiosModel]] = {}
        for model in models:
            unique[f"{model.__module__}.{model.__name__}"] = model

        return [unique[key] for key in sorted(unique.keys())]

    def _build_snapshot_up_sql(self) -> str:
        ddl = self.db.ddl
        if ddl is None:
            raise MigrationError("Session does not expose DDL generator via session._ddl")

        statements: List[str] = []
        for model in self._scan_models():
            statements.append(ddl.create_table(model))

        return "\n\n".join(statements)

    def _build_snapshot_down_sql(self) -> str:
        ddl = self.db.ddl
        if ddl is None:
            raise MigrationError("Session does not expose DDL generator via session._ddl")

        statements: List[str] = []
        for model in reversed(self._scan_models()):
            statements.append(ddl.drop_table(model))

        return "\n\n".join(statements)

    def create_migration(self, name: str) -> str:
        version = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{name}"
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        migration_file = self.migrations_dir / f"{version}.py"

        template = f'''"""
Migration: {name}
Version: {version}
Created: {datetime.utcnow().isoformat()}Z
"""

from your_migration_module import Migration


def get_migration() -> Migration:
    return Migration(
        name="{name}",
        version="{version}",
        up_sql=\"\"\"{self._build_snapshot_up_sql()}\"\"\",
        down_sql=\"\"\"{self._build_snapshot_down_sql()}\"\"\",
    )
'''

        migration_file.write_text(template, encoding="utf-8")
        self.logger.info("Created migration file: %s", migration_file)

        self.reload()
        return str(migration_file)

    def applied_migrations(self) -> List[Dict[str, Any]]:
        return self.repo.all()

    def pending_migrations(self, target_version: Optional[str] = None) -> List[Migration]:
        self.repo.ensure_table()
        applied = {
            row["version"]
            for row in self.repo.all()
            if row["status"] == MigrationStatus.COMPLETED.value
        }

        pending = [
            self.migrations[version]
            for version in sorted(self.migrations.keys())
            if version not in applied
        ]

        if target_version is not None:
            pending = [m for m in pending if m.version <= target_version]

        return pending

    def _split_sql_statements(self, sql: str) -> List[str]:
        """
        Conservative splitter.

        Best practice is still one statement per execute block or storing statements
        as a list, but this is already safer than a raw split(';') because it ignores
        empty chunks and preserves content more cleanly.

        If your migrations may contain procedures/triggers/functions with internal
        semicolons, replace this with a dialect-aware parser.
        """
        parts = [part.strip() for part in sql.split(";")]
        return [part for part in parts if part]

    def _execute_migration_sql(self, sql: str) -> None:
        for statement in self._split_sql_statements(sql):
            self.db.execute(statement)

    def migrate(self, target_version: Optional[str] = None) -> None:
        self.repo.ensure_table()
        pending = self.pending_migrations(target_version=target_version)

        if not pending:
            self.logger.info("No pending migrations to apply.")
            return

        self.logger.info("Found %d pending migrations.", len(pending))

        for migration in pending:
            self.logger.info(
                "Applying migration %s (%s)",
                migration.name,
                migration.version,
            )
            start = perf_counter()

            try:
                self.db.begin()
                self.repo.record_running(migration)

                if migration.up_sql.strip():
                    self._execute_migration_sql(migration.up_sql)

                execution_time_ms = int((perf_counter() - start) * 1000)
                self.repo.record_completed(migration, execution_time_ms)
                self.db.commit()

                self.logger.info(
                    "Applied migration %s in %d ms",
                    migration.version,
                    execution_time_ms,
                )

            except Exception as exc:
                try:
                    self.db.rollback()
                except Exception:
                    self.logger.exception(
                        "Rollback failed while handling migration failure: %s",
                        migration.version,
                    )

                try:
                    self.repo.record_failed(migration)
                except Exception:
                    self.logger.exception(
                        "Failed to record migration failure state: %s",
                        migration.version,
                    )

                raise MigrationExecutionError(
                    f"Failed to apply migration {migration.version}: {exc}"
                ) from exc

    def rollback(
        self,
        steps: int = 1,
        target_version: Optional[str] = None,
    ) -> None:
        """
        Rollback semantics:
        - If target_version is provided:
            rollback completed migrations newer than target_version.
            target_version itself remains applied.
        - Else:
            rollback the latest `steps` completed migrations.
        """
        self.repo.ensure_table()

        completed = [
            row for row in self.repo.all()
            if row["status"] == MigrationStatus.COMPLETED.value
        ]
        completed_sorted = sorted(completed, key=lambda x: x["version"], reverse=True)

        if target_version is not None:
            candidates = [
                self.migrations[row["version"]]
                for row in completed_sorted
                if row["version"] > target_version and row["version"] in self.migrations
            ]
        else:
            candidates = []
            for row in completed_sorted:
                migration = self.migrations.get(row["version"])
                if migration is not None:
                    candidates.append(migration)
                if len(candidates) >= steps:
                    break

        rollbackable = [m for m in candidates if m.down_sql.strip()]

        if not rollbackable:
            self.logger.info("No migrations to rollback.")
            return

        self.logger.info("Rolling back %d migrations.", len(rollbackable))

        for migration in rollbackable:
            self.logger.info(
                "Rolling back migration %s (%s)",
                migration.name,
                migration.version,
            )
            try:
                self.db.begin()

                if migration.down_sql.strip():
                    self._execute_migration_sql(migration.down_sql)

                self.repo.record_rolled_back(migration)
                self.db.commit()

                self.logger.info("Rolled back migration %s", migration.version)

            except Exception as exc:
                try:
                    self.db.rollback()
                except Exception:
                    self.logger.exception(
                        "Rollback transaction failed while reverting migration %s",
                        migration.version,
                    )

                raise MigrationExecutionError(
                    f"Failed to rollback migration {migration.version}: {exc}"
                ) from exc

    def status(self) -> Dict[str, Any]:
        rows = self.repo.all()
        applied = [r for r in rows if r["status"] == MigrationStatus.COMPLETED.value]
        rolled_back = [r for r in rows if r["status"] == MigrationStatus.ROLLED_BACK.value]
        failed = [r for r in rows if r["status"] == MigrationStatus.FAILED.value]

        applied_versions = {r["version"] for r in applied}
        pending_count = len(set(self.migrations.keys()) - applied_versions)

        return {
            "applied": len(applied),
            "pending": pending_count,
            "rolled_back": len(rolled_back),
            "failed": len(failed),
            "total": len(self.migrations),
            "migrations": rows,
        }

    def validate(self) -> List[str]:
        self.repo.ensure_table()
        issues: List[str] = []

        applied = self.repo.all()
        disk_versions = set(self.migrations.keys())

        for row in applied:
            version = row["version"]
            migration = self.migrations.get(version)

            if migration is None:
                issues.append(
                    f"Migration {version} is recorded in DB but missing from files."
                )
                continue

            actual_checksum = migration.checksum()
            if row["checksum"] != actual_checksum:
                issues.append(
                    f"Checksum mismatch for {version}: "
                    f"db={row['checksum']} file={actual_checksum}"
                )

        for version in sorted(disk_versions):
            if not self._is_valid_version(version):
                issues.append(f"Invalid migration version format: {version}")

        return issues

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        if "_" not in version:
            return False

        prefix, _ = version.split("_", 1)
        return len(prefix) == 14 and prefix.isdigit()
