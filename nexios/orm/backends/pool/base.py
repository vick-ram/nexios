from abc import ABC, abstractmethod
from dataclasses import dataclass
import statistics
from enum import StrEnum
from typing import List, Optional
from nexios.orm.connection import AsyncDatabaseConnection, SyncDatabaseConnection


@dataclass
class PoolConfig:
    min_size: int = 1
    max_size: int = 50
    connection_timeout: float = 5.0
    max_lifetime: int = 7200  # 2 hour in seconds
    idle_timeout: int = 300  # 5 minutes in seconds
    health_check_interval: int = 60  # 1 minute

    shrink_interval: int = 30  # Check every 30 seconds for shrinking
    max_idle: int = 10  # Maximum idle connections to keep

class PoolEvent(StrEnum):
    CONNECTION_CREATED = "connection_created"
    CONNECTION_CLOSED = "connection_closed"
    CONNECTION_INVALID = "connection_invalid"
    POOL_SHRINK = "pool_shrink"
    POOL_GROW = "pool_grow"

@dataclass
class PoolMetrics:
    total_connections: int = 0
    connections_created: int = 0
    connections_closed: int = 0
    connection_errors: int = 0
    total_operations: int = 0
    slow_operations: int = 0
    wait_times: Optional[List[float]] = None
    average_wait_time: float = 0.0

    def __post_init__(self):
        if self.wait_times is None:
            self.wait_times = []

    def record_wait_time(self, wait_time: float):
        if self.wait_times is not None:
            self.wait_times.append(wait_time)
            if len(self.wait_times) > 1000:
                self.wait_times.pop(0)
            self.average_wait_time = (
                statistics.mean(self.wait_times) if self.wait_times else 0.0
            )


class BaseConnectionPool(ABC):
    @abstractmethod
    def get_connection(self) -> SyncDatabaseConnection:
        """Get connection from the pool"""
        pass

    @abstractmethod
    def return_connection(self, conn: SyncDatabaseConnection) -> None:
        """Return connection to the pool"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close all connections in the pool"""
        pass

    @property
    @abstractmethod
    def size(self) -> int:
        """Current pool size"""
        pass

    @property
    @abstractmethod
    def available(self) -> int:
        """Number of available connections in the pool"""
        pass

    @abstractmethod
    def health_check(self) -> None:
        """Perform health check on connections"""
        pass


class BaseAsyncConnectionPool(ABC):
    @abstractmethod
    async def get_connection(self) -> AsyncDatabaseConnection:
        """Get a connection from the pool"""
        pass

    @abstractmethod
    async def return_connection(self, conn: AsyncDatabaseConnection) -> None:
        """Return a connection to the pool"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close all connections in the pool"""
        pass

    @property
    @abstractmethod
    async def size(self) -> int:
        """Current pool size"""
        pass

    @property
    @abstractmethod
    async def available(self) -> int:
        """Number of available connections in the pool"""
        pass

    @abstractmethod
    async def health_check(self) -> None:
        pass
