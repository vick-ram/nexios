from __future__ import annotations

import inspect
import logging
import os
import sys
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Type, Union, Any, Tuple
from nexios.orm.config import (
    SQLiteDialect,
    generate_placeholders,
    get_param_placeholder,
)
from nexios.orm.misc.event_loop import NexiosEventLoop
from nexios.orm.model import NexiosModel
from nexios.orm.sessions import AsyncSession, Session


class MigrationStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Migration:
    def __init__(
        self, name: str, version: str, up_sql: str, down_sql: str = ""
    ) -> None:
        self.name = name
        self.version = version
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.created_at = datetime.now()
        self.checksum: Optional[str] = None
    
    def compute_checksum(self) -> str:
        import hashlib

        content = f"{self.name}{self.version}{self.up_sql}{self.down_sql}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

class MigrationManager:
    def __init__(self, session: Union[Session, AsyncSession]) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.session = session
        self.migrations: Dict[str, Migration] = {}
        self._migrations_table_created = False
        self._loop = NexiosEventLoop()
        self.__is_async = isinstance(self.session, AsyncSession)

        self._load_migrations()
    
    def _load_migrations(self) -> None:
        migration_dir = "migrations"
        if not os.path.exists(migration_dir):
            return
        
        for filename in os.listdir(migration_dir):
            if filename.endswith(".py"):
                try:
                    module_path = os.path.join(migration_dir, filename)
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"migrations.{filename[:-3]}", module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        if hasattr(module, "get_migration"):
                            migration = module.get_migration()
                            self.add_migration(migration)
                except Exception as e:
                    self.logger.warning(f"Failed to load migration {filename}: {e}")

    def _execute(self, sql: str, params: Tuple[Any, ...] = ()):
        async def execute_async(sess: AsyncSession):
            return await sess.execute(sql, params)

        if isinstance(self.session, AsyncSession):
            return self._loop.run(execute_async(self.session))
        else:
            return self.session.execute(sql, params)

    def _ensure_migrations_table(self) -> None:
        """
        Create migrations table if it doesn't exist
        """
        if self._migrations_table_created:
            return

        create_table_sql = """
            CREATE TABLE IF NOT EXISTS _migrations (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                checksum TEXT,
                execution_time INTEGER
            )
            """

        try:
            self._execute(create_table_sql)
            self._migrations_table_created = True
            self.logger.debug("Migrations table ensured")
        except Exception as e:
            self.logger.error(f"Failed to create migrations table: {e}")
            raise

    def _scan_models(self) -> List[Type[NexiosModel]]:
        models = []

        for module_name, module in sys.modules.items():
            if not module or module_name.startswith(("_", "builtins", "sys")):
                continue

            try:
                is_table = (
                    NexiosModel.model_config.get("table")
                    or NexiosModel.__tablename__ is not None
                )
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, NexiosModel)
                        and obj != NexiosModel
                        and is_table
                        and obj.__module__ == module_name
                    ):
                        models.append(obj)
            except (ImportError, TypeError, AttributeError):
                continue

        return models

    def add_migration(self, migration: Migration) -> None:
        """Register a migration"""
        if migration.version in self.migrations:
            self.logger.warning(f"Migration {migration.version} already registered")
        self.migrations[migration.version] = migration

    def _up_sql_migration(self):
        models = self._scan_models()
        ddl = self.session._ddl
        statements = []

        for model in models:
            create_table_sql = ddl.create_table(model)
            statements.append(create_table_sql)
        
        return "\n".join(statements)
    
    def _down_sql_migration(self):
        models = self._scan_models()
        ddl = self.session._ddl
        statements = []

        for model in models:
            drop_table_sql = ddl.drop_table(model)
            statements.append(drop_table_sql)

        return "\n".join(statements)

    def create_migration(self, name: str) -> str:
        """Create a migration file"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        version = f"{timestamp}_{name}"

        # Create migration directory if it doesn't exist
        os.makedirs("migrations", exist_ok=True)

        # Create migration file
        migration_file = f"migrations/{version}.py"
        template = f'''"""
            Migration: {name}
            Version: {version}
            Created:{datetime.now()}
        """
            def get_migration():
                return Migration(
                    name="{name}",
                    version="{version}",
                    up_sql="""
                        -- Add your UP Migration SQL here
                        {self._up_sql_migration()}
                    """,
                    down_sql="""
                        -- Add your DOWN Migration SQL here
                        {self._down_sql_migration()}
                    """ 
                )
        '''
        try:
            with open(migration_file, "w") as f:
                f.write(template)
            
            self.logger.info(f"Created migration file: {migration_file}")
            
            # Reload migrations
            self._load_migrations()
            
            return migration_file
        except Exception as e:
            self.logger.error(f"Failed to create migration file: {e}")
            raise

    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of applied migrations"""
        self._ensure_migrations_table()
        # sql = "SELECT version FROM _migrations WHERE status = 'completed' ORDER BY version"
        sql = """
            SELECT version, name, applied_at, status, checksum 
            FROM _migrations 
            ORDER BY version
        """

        try:
            async def async_fetch(sess: AsyncSession):
                result = await sess.execute(sql)
                return await result.fetchall()

            if self.__is_async:
                rows = self._loop.run(async_fetch(self.session)) # type: ignore
            else:
                rows = self.session.execute(sql).fetchall() # type: ignore

            return [
                {
                    "version": row[0],
                    "name": row[1],
                    "applied_at": row[2],
                    "status": row[3],
                    "checksum": row[4]
                }
                for row in rows
            ]
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []
    

    def migrate(
        self,
        target_version: Optional[str] = None,
    ) -> None:
        """Run all pending migrations"""
        self._ensure_migrations_table()

        applied = {m["version"] for m in self.get_applied_migrations()
                   if m["status"] == MigrationStatus.COMPLETED.value}
        
        pending: List[Migration] = []
        for version in sorted(self.migrations.keys()):
            if version not in applied:
                pending.append(self.migrations[version])
        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            self.logger.info("No pending migrations to apply.")
            return
        
        self.logger.info(f"Found {len(pending)} pending migrations.")
        
        for migration in pending:
            self.logger.info(
                f"Applying migration: {migration.name} ({migration.version})"
            )

            start_time = datetime.now()
            placeholder = get_param_placeholder(driver=self.session.engine.driver)
            placeholders = generate_placeholders(
                driver=self.session.engine.driver, count=4, start_index=1
            )

            try:
                # Record migratioon start
                self._execute(
                    f"INSERT OR REPLACE INTO _migrations (version, name, status, checksum) VALUES ({placeholders})",
                    (migration.version, migration.name, MigrationStatus.RUNNING.value, migration.compute_checksum()),
                )

                # Execute migration SQL
                if migration.up_sql.strip():
                    statements = [
                        stmt.strip()
                        for stmt in migration.up_sql.split(";")
                        if stmt.strip()
                    ]
                    for statement in statements:
                        if statement:
                            self._execute(statement)
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

                # Mark as completed
                self._execute(
                        f"UPDATE _migrations SET status = {placeholder}, "
                        f"execution_time = {placeholder} WHERE version = {placeholder}",
                        (
                            MigrationStatus.COMPLETED.value,
                            execution_time,
                            migration.version
                        )
                    )
                self.logger.info(f"✓ Applied migration: {migration.name} in {execution_time} ms")

            except Exception as e:
                # Mark as failed
                self._execute(
                    f"UPDATE _migrations SET status = {placeholder} WHERE version = {placeholder}",
                    (MigrationStatus.FAILED.value, migration.version),
                )
                self.logger.error(f"✗ Failed to apply migration {migration.name}: {e}")
                raise

    def rollback(
        self,
        steps: int = 1,
        target_version: Optional[str] = None,
    ) -> None:
        """Rollbak migrations"""
        self._ensure_migrations_table()
        
        applied_migrations = self.get_applied_migrations()
        completed_migrations = [
            m for m in applied_migrations 
            if m["status"] == MigrationStatus.COMPLETED.value
        ]
        
        to_rollback: List[Migration] = []
        count = 0
        
        for migration_info in reversed(completed_migrations):
            migration = self.migrations.get(migration_info["version"])
            if migration and migration.down_sql.strip():
                to_rollback.append(migration)
                count += 1
                if (target_version and migration.version <= target_version) or count >= steps:
                    break
        
        if not to_rollback:
            self.logger.info("No migrations to rollback")
            return
        
        self.logger.info(f"Rolling back {len(to_rollback)} migrations")
        
        for migration in to_rollback:
            self.logger.info(f"Rolling back migration: {migration.name} ({migration.version})")
            
            try:
                # Execute rollback SQL if not faking
                if migration.down_sql.strip():
                    statements = [
                        stmt.strip()
                        for stmt in migration.down_sql.split(";")
                        if stmt.strip()
                    ]
                    for statement in statements:
                        if statement:  # Skip empty statements
                            self._execute(statement)
                
                # Mark as rolled back
                driver = getattr(self.session.engine, 'driver', 'sqlite3')
                placeholder = get_param_placeholder(driver)
                
                self._execute(
                    f"UPDATE _migrations SET status = {placeholder} "
                    f"WHERE version = {placeholder}",
                    (MigrationStatus.ROLLED_BACK.value, migration.version)
                )
                
                self.logger.info(f"✓ Rolled back migration: {migration.name}")
                
            except Exception as e:
                self.logger.error(f"✗ Failed to rollback migration {migration.name}: {e}")
                raise

    def status(self) -> Dict[str, Any]:
        """Get migration status."""
        self._ensure_migrations_table()
        
        try:
            applied_migrations = self.get_applied_migrations()
            applied_versions = {
                m["version"] for m in applied_migrations 
                if m["status"] == MigrationStatus.COMPLETED.value
            }
            all_versions = set(self.migrations.keys())
            
            return {
                "applied": len(applied_versions),
                "pending": len(all_versions - applied_versions),
                "rolled_back": len([
                    m for m in applied_migrations 
                    if m["status"] == MigrationStatus.ROLLED_BACK.value
                ]),
                "failed": len([
                    m for m in applied_migrations 
                    if m["status"] == MigrationStatus.FAILED.value
                ]),
                "total": len(all_versions),
                "migrations": applied_migrations
            }
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {
                "applied": 0,
                "pending": 0,
                "rolled_back": 0,
                "failed": 0,
                "total": 0,
                "migrations": [],
                "error": str(e)
            }
    
    def validate(self) -> List[str]:
        """Validate applied migrations against current files."""
        self._ensure_migrations_table()
        
        issues = []
        applied_migrations = self.get_applied_migrations()
        
        for applied in applied_migrations:
            migration = self.migrations.get(applied["version"])
            
            if not migration:
                issues.append(f"Migration {applied['version']} is applied but not found in files")
                continue
            
            if applied.get("checksum"):
                file_checksum = migration.compute_checksum()
                if file_checksum != applied["checksum"]:
                    issues.append(
                        f"Migration {applied['version']} checksum mismatch. "
                        f"Applied: {applied['checksum']}, File: {file_checksum}"
                    )
        
        return issues
