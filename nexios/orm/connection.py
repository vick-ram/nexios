from abc import ABC, abstractmethod
from typing_extensions import Any, Optional, Tuple, List, Union

class BaseCursor(ABC):
    @property
    @abstractmethod
    def description(self) -> Any: ...

    @property
    @abstractmethod
    def rowcount(self) -> int: ...



class SyncCursor(BaseCursor):
    @abstractmethod
    def execute(self, sql: str, parameters: Tuple[Any, ...] = ...) -> Any: ...

    @abstractmethod
    def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any: ...

    @abstractmethod
    def fetchone(self) -> Optional[Tuple[Any, ...]]: ...

    @abstractmethod
    def fetchall(self) -> List[Tuple[Any, ...]]: ...

    @abstractmethod
    def fetchmany(self, size: int = ...) -> List[Tuple[Any, ...]]: ...

class AsyncCursor(BaseCursor):
    @abstractmethod
    async def execute(self, sql: str, parameters: Tuple[Any, ...] = ...) -> Any: ...

    @abstractmethod
    async def executemany(self, sql: str, seq_of_parameters: List[Tuple[Any, ...]]) -> Any: ...

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

