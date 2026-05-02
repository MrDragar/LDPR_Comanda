from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import IDatabase
from src.infrastructure.interfaces import IDatabaseUnitOfWork


class UnitOfWork(IDatabaseUnitOfWork):
    current_session: ContextVar[AsyncSession | None] =\
        ContextVar('current_session', default=None)

    def __init__(self, database: IDatabase):
        self.database = database

    @asynccontextmanager
    async def atomic(self) -> AsyncGenerator[None, None]:
        async with self.database.create_session() as session:
            token = self.current_session.set(session)
            try:
                yield None
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                self.current_session.reset(token)

    def get_session(self) -> AsyncSession:
        session = self.current_session.get()
        if session is None:
            raise RuntimeError("Use 'async with uow.atomic()' to create session")
        return session
