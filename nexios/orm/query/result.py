from __future__ import annotations

from typing import TYPE_CHECKING, Generic, List, Optional, TypeVar
from nexios.orm.query.builder import Select
from nexios.orm.sessions import Session, AsyncSession

if TYPE_CHECKING:
    from nexios.orm.model import NexiosModel


_T = TypeVar("_T", bound="NexiosModel")

class ResultSet(Generic[_T]):
    """Base class for result sets"""

    def __init__(self, statement: Select[_T]) -> None:
        self.statement = statement

    def all(self) -> List[_T]:
        raise NotImplementedError

    def first(self) -> Optional[_T]:
        raise NotImplementedError

    def one(self) -> _T:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def exists(self) -> bool:
        raise NotImplementedError


class SyncResultSet(ResultSet[_T]):
    """Synchronous result set"""

    def __init__(self, statement: Select[_T], session: Session) -> None:
        super().__init__(statement)
        self.statement._bind(session)

    def all(self) -> List[_T]:
        return self.statement._all()

    def first(self) -> Optional[_T]:
        return self.statement._first()

    def one(self) -> _T:
        result = self.first()
        if result is None:
            raise ValueError("No row was found for one()")
        return result

    def count(self) -> int:
        return self.statement._count()

    def exists(self) -> bool:
        return self.statement._exists()


class AsyncResultSet(ResultSet[_T]):
    """Asynchronous result set"""

    def __init__(self, statement: Select[_T], session: AsyncSession) -> None:
        super().__init__(statement)
        self.statement._bind(session)

    async def all(self) -> List[_T]:  # type: ignore[override]
        return await self.statement._all_async()

    async def first(self) -> Optional[_T]:  # type: ignore[override]
        return await self.statement._first_async()

    async def one(self) -> _T:  # type: ignore[override]
        result = await self.first()
        if result is None:
            raise ValueError("No row was found for one()")
        return result

    async def count(self) -> int:  # type: ignore[override]
        return await self.statement._async_count()

    async def exists(self) -> bool:  # type: ignore[override]
        return await self.statement._async_exists()
