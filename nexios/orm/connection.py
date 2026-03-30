from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple, List


class SyncQueryResult:
    def __init__(self, cursor: SyncCursor) -> None:
        self.cursor = cursor

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        return self.cursor.fetchone()

    def fetchall(self) -> List[Tuple[Any, ...]]:
        return self.cursor.fetchall()

    def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        return self.cursor.fetchmany(size=size)


class AsyncQueryResult:
    def __init__(self, cursor: AsyncCursor) -> None:
        self.cursor = cursor

    def __await__(self):
        async def _await():
            return self
        return _await().__await__()

    async def fetchone(self) -> Optional[Tuple[Any, ...]]:
        return await self.cursor.fetchone()

    async def fetchall(self) -> List[Tuple[Any, ...]]:
        return await self.cursor.fetchall()

    async def fetchmany(self, size: int = 1) -> List[Tuple[Any, ...]]:
        return await self.cursor.fetchmany(size=size)


class BaseCursor(ABC):
    @property
    @abstractmethod
    def description(self) -> Any: ...

    @property
    @abstractmethod
    def rowcount(self) -> int: ...


class SyncCursor(BaseCursor):
    @abstractmethod
    def execute(self, sql: str, parameters: Tuple[Any, ...] = ...) -> SyncQueryResult: ...

    @abstractmethod
    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> SyncQueryResult: ...

    @abstractmethod
    def fetchone(self) -> Optional[Tuple[Any, ...]]: ...

    @abstractmethod
    def fetchall(self) -> List[Tuple[Any, ...]]: ...

    @abstractmethod
    def fetchmany(self, size: int = ...) -> List[Tuple[Any, ...]]: ...

class AsyncCursor(BaseCursor):
    @abstractmethod
    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ...) -> AsyncQueryResult: ...

    @abstractmethod
    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> AsyncQueryResult: ...

    @abstractmethod
    async def fetchone(self) -> Optional[Tuple[Any, ...]]: ...

    @abstractmethod
    async def fetchall(self) -> List[Tuple[Any, ...]]: ...

    @abstractmethod
    async def fetchmany(self, size: int = ...) -> List[Tuple[Any, ...]]: ...

class SyncDatabaseConnection(ABC):
    @abstractmethod
    def cursor(self) -> SyncCursor: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def raw_connection(self) -> Any: ...

    @property
    @abstractmethod
    def is_connection_open(self) -> bool: ...

class AsyncDatabaseConnection(ABC):
    @abstractmethod
    async def cursor(self) -> AsyncCursor: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @property
    @abstractmethod
    def raw_connection(self) -> Any: ...

    @property
    @abstractmethod
    def is_connection_open(self) -> bool: ...

