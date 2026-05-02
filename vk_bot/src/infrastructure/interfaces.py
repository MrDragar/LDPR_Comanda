from abc import abstractmethod, ABC

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.interfaces import IUnitOfWork


class IDatabaseUnitOfWork(IUnitOfWork, ABC):
    @abstractmethod
    def get_session(self) -> AsyncSession:
        ...


class IDatabase(ABC):
    @abstractmethod
    def create_session(self) -> AsyncSession:
        ...

    @abstractmethod
    async def create_database(self) -> None:
        ...

