
from datetime import datetime
import os
from typing import Dict, List, Optional, Set, Union, Any, Tuple

from nexios.orm.backends.types import MigrationStatus
from nexios.orm.backends.sessions import AsyncSession, Session


class Migration:
    def __init__(self, name: str, version: str, up_sql: str, down_sql: str = "") -> None:
        self.name = name
        self.version = version
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.created_at = datetime.now()


class MigrationManager:
    def __init__(self) -> None:
        self.migrations: Dict[str, Migration] = {}
        self._migrations_table_created = False
    
    async def _execute(self,session: Union[Session, AsyncSession], sql: str,  params: Tuple[Any, ...] = ()):
        if isinstance(session, AsyncSession):
            await session.execute(sql)
        else:
            session.execute(sql, params)
    
    async def _ensure_migrations_table(self, session: Union[Session, AsyncSession]) -> None:
        """Create migrations table if it doesn't exist"""
        if not self._migrations_table_created:
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS _migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL
                )
                """
            if isinstance(session, AsyncSession):
                await session.execute(create_table_sql)
            else:
                session.execute(create_table_sql)
            self._migrations_table_created = True
    
    def add_migration(self, migration: Migration) -> None:
        """Register a migration"""
        self.migrations[migration.version] = migration
    
    def create_migration(self, name: str) -> str:
        """Create a migration file"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
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
            from nexios.orm.backends.migrations import Migration

            def get_migration():
                return Migration(
                    name="{name}",
                    version="{version}",
                    up_sql="""
                        -- Add your UP Migration SQL here
                    """,
                    down_sql="""
                        -- Add your DOWN Migration SQL here
                    """ 
                )
        '''
        with open(migration_file, 'w') as f:
            f.write(template)
        
        return migration_file
    
    async def get_applied_migrations(self, session: Union[Session, AsyncSession]) -> List[str]:
        """Get list of applied migrations"""
        await self._ensure_migrations_table(session)
        if isinstance(session, AsyncSession):
            await session.execute("SELECT version FROM _migrations WHERE status = 'completed' ORDER BY version")
            rows = await session.fetchall()
            return [row[0] for row in rows] if rows else []
        else:
            session.execute("SELECT version FROM _migrations WHERE status = 'completed' ORDER BY version")
            rows = session.fetchall()
            return [row[0] for row in rows] if rows else []
    
    async def migrate(self, session: Union[Session, AsyncSession], target_version: Optional[str] = None) -> None:
        """Run all pending migrations"""
        applied = await self.get_applied_migrations(session)

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
                await self._execute(session, "INSERT OR REPLACE INTO _migrations (version, name, status) VALUES (?, ?, ?)",
                        (migration.version, migration.name, MigrationStatus.RUNNING.value))
                
                # Execute migration SQL
                if migration.up_sql.strip():
                    statements = [stmt.strip() for stmt in migration.up_sql.split(';') if stmt.strip()]
                    for statement in statements:
                        await self._execute(session, statement)
                
                # Mark as completed
                await self._execute(
                    session,
                    "UPDATE _migrations SET status = ? WHERE version = ?",
                        (MigrationStatus.COMPLETED.value, migration.version)
                )
                print(f"✓ Applied migration: {migration.name}")
            
            except Exception as e:
                # Mark as failed
                await self._execute(
                    session,
                    "UPDATE _migrations SET status = ? WHERE version = ?",
                    (MigrationStatus.FAILED.value, migration.version)
                )
                print(f"✗ Failed to apply migration {migration.name}: {e}")
                raise
        
    
    async def rollback(self, session: Union[Session, AsyncSession], target_version: Optional[str] = None) -> None:
        """Rollbak migrations"""
        applied = await self.get_applied_migrations(session)

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
                    statements = [stmt.strip() for stmt in migration.down_sql.split(';') if stmt.strip()]
                    for statement in statements:
                        await self._execute(session, statement)
                await self._execute(session, "DELETE FROM _migrations WHERE version = ?", (migration.version,))
                print(f"✓ Rolled back migration: {migration.name}")
            except Exception as e:
                print(f"✗ Failed to rollback migration {migration.name}: {e}")
                raise

    
    async def status(self, session: Union[Session, AsyncSession]) -> Dict[str, Any]:
        """Get migration status"""
        _applied_versions: Set[Any] = set()
        _all_versions: Set[str] = set()
        _rows: List[Any] = []

        sql = """
            SELECT version, name, applied_at, status
            FROM _migrations
            ORDER BY version
        """
        await self._ensure_migrations_table(session)
        await self._execute(session, sql)
        
        if isinstance(session, AsyncSession):
            _rows = await session.fetchall()
            _applied_versions = {row[0] for row in _rows if row[3] == MigrationStatus.COMPLETED.value}
            _all_versions = set(self.migrations.keys())
        else:
            _rows = session.fetchall()
            _applied_versions = {row[0] for row in _rows if row[3] == MigrationStatus.COMPLETED.value}
            _all_versions = set(self.migrations.keys())
        
        return {
            'applied': len(_applied_versions),
            'pending': len(_all_versions - _applied_versions),
            'total': len(_all_versions),
            'migrations': [
                {
                    'version': row[0],
                    'name': row[1],
                    'applied': row[2],
                    'status': row[3]
                }
                for row in _rows
            ]
        }