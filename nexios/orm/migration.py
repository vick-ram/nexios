from __future__ import annotations

from datetime import datetime
import inspect
import os
import sys
from typing import Dict, List, Optional, Set, Type, Union, Any, Tuple
from enum import Enum
from nexios.orm.model import BaseModel
from nexios.orm.sessions import AsyncSession, Session


class MigrationStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Migration:
    def __init__(
        self, name: str, version: str, up_sql: str, down_sql: str = ""
    ) -> None:
        self.name = name
        self.version = version
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.created_at = datetime.now()


class MigrationManager:
    def __init__(self, session: Union[Session, AsyncSession]) -> None:
        self.session = session
        self.migrations: Dict[str, Migration] = {}
        self._migrations_table_created = False

    async def _execute(
        self,
        sql: str,
        params: Tuple[Any, ...] = (),
    ):
        if isinstance(self.session, AsyncSession):
            await self.session.execute(sql)
        else:
            self.session.execute(sql, params)

    async def _fetchall(self):
        if isinstance(self.session, AsyncSession):
            return await self.session.fetchall()
        else:
            return self.session.fetchall()

    async def _ensure_migrations_table(self) -> None:
        """
        Create migrations table if it doesn't exist

        :param session: database session
        :type session: Union[Session, AsyncSession
        """
        if not self._migrations_table_created:
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS _migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL
                )
                """
            await self._execute(create_table_sql)
            self._migrations_table_created = True

    def _scan_models(self) -> List[Type[BaseModel]]:
        models = []

        for module_name, module in sys.modules.items():
            if not module or module_name.startswith(("_", "builtins", "sys")):
                continue

            try:
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseModel)
                        and obj != BaseModel
                        and BaseModel.is_table
                        and obj.__module__ == module_name
                    ):
                        models.append(obj)
            except (ImportError, TypeError, AttributeError):
                continue

        return models

    def add_migration(self, migration: Migration) -> None:
        """Register a migration"""
        self.migrations[migration.version] = migration
    
    async def _up_sql_migration(self):
        models = self._scan_models()
        if isinstance(self.session, AsyncSession):
            await self.session.create_all(models)
        else:
            self.session.create_all(models)

    async def create_migration(self, name: str) -> str:
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
                        {await self._up_sql_migration()}
                    """,
                    down_sql="""
                        -- Add your DOWN Migration SQL here
                    """ 
                )
        '''
        with open(migration_file, "w") as f:
            f.write(template)

        return migration_file

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations"""
        await self._ensure_migrations_table()
        sql = "SELECT version FROM _migrations WHERE status = 'completed' ORDER BY version"
        await self._execute(sql)
        rows = await self._fetchall()
        return [row[0] for row in rows] if rows else []

    async def migrate(
        self,
        target_version: Optional[str] = None,
    ) -> None:
        """Run all pending migrations"""
        applied = await self.get_applied_migrations()

        # Ge pending migrations
        pending: List[Migration] = []
        for version in sorted(self.migrations.keys()):
            if version not in applied:
                pending.append(self.migrations[version])
        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        for migration in pending:
            print(f"Applying migration: {migration.name} ({migration.version})")

            try:
                # Record migratioon start
                await self._execute(
                    "INSERT OR REPLACE INTO _migrations (version, name, status) VALUES (?, ?, ?)",
                    (migration.version, migration.name, MigrationStatus.RUNNING.value),
                )

                # Execute migration SQL
                if migration.up_sql.strip():
                    statements = [
                        stmt.strip()
                        for stmt in migration.up_sql.split(";")
                        if stmt.strip()
                    ]
                    for statement in statements:
                        await self._execute(statement)

                # Mark as completed
                await self._execute(
                    "UPDATE _migrations SET status = ? WHERE version = ?",
                    (MigrationStatus.COMPLETED.value, migration.version),
                )
                print(f"✓ Applied migration: {migration.name}")

            except Exception as e:
                # Mark as failed
                await self._execute(
                    "UPDATE _migrations SET status = ? WHERE version = ?",
                    (MigrationStatus.FAILED.value, migration.version),
                )
                print(f"✗ Failed to apply migration {migration.name}: {e}")
                raise

    async def rollback(
        self,
        target_version: Optional[str] = None,
    ) -> None:
        """Rollbak migrations"""
        applied = await self.get_applied_migrations()

        to_rollback: List[Migration] = []
        for version in sorted(applied, reverse=True):
            migration = self.migrations.get(version)
            if migration and migration.down_sql.strip():
                to_rollback.append(migration)
            if target_version and version <= target_version:
                break

        for migration in to_rollback:
            print(f"Rolling back migration: {migration.name} ({migration.version})")

            try:
                # Execute rollback sql
                if migration.down_sql.strip():
                    statements = [
                        stmt.strip()
                        for stmt in migration.down_sql.split(";")
                        if stmt.strip()
                    ]
                    for statement in statements:
                        await self._execute(statement)
                await self._execute(
                    "DELETE FROM _migrations WHERE version = ?",
                    (migration.version,),
                )
                print(f"✓ Rolled back migration: {migration.name}")
            except Exception as e:
                print(f"✗ Failed to rollback migration {migration.name}: {e}")
                raise

    async def status(self) -> Dict[str, Any]:
        """Get migration status"""

        sql = """
            SELECT version, name, applied_at, status
            FROM _migrations
            ORDER BY version
        """
        await self._ensure_migrations_table()
        await self._execute(sql)

        _rows = await self._fetchall()
        _applied_versions = {
            row[0] for row in _rows if row[3] == MigrationStatus.COMPLETED.value
        }
        _all_versions = set(self.migrations.keys())

        return {
            "applied": len(_applied_versions),
            "pending": len(_all_versions - _applied_versions),
            "total": len(_all_versions),
            "migrations": [
                {"version": row[0], "name": row[1], "applied": row[2], "status": row[3]}
                for row in _rows
            ],
        }
