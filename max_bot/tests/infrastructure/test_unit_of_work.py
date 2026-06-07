import asyncio
import re
from unittest.mock import Mock, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import IDatabase
from src.infrastructure.unit_of_work import UnitOfWork


class AsyncContextManager:
    """Helper class to create async context manager mocks"""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_get_session_inside_context():
    mock_db = Mock(spec=IDatabase)
    mock_session = AsyncMock(spec=AsyncSession)
    mock_db.create_session.return_value = AsyncContextManager(mock_session)

    uow = UnitOfWork(mock_db)
    async with uow.atomic():
        session = uow.get_session()
        assert session is mock_session


@pytest.mark.asyncio
async def test_commit_called_on_success():
    mock_db = Mock(spec=IDatabase)
    mock_session = AsyncMock(spec=AsyncSession)
    mock_db.create_session.return_value = AsyncContextManager(mock_session)

    uow = UnitOfWork(mock_db)
    async with uow.atomic():
        pass

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_rollback_called_on_exception():
    mock_db = Mock(spec=IDatabase)
    mock_session = AsyncMock(spec=AsyncSession)
    mock_db.create_session.return_value = AsyncContextManager(mock_session)

    uow = UnitOfWork(mock_db)
    with pytest.raises(Exception):
        async with uow.atomic():
            raise Exception("Test error")

    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_outside_context_raises():
    mock_db = Mock(spec=IDatabase)
    uow = UnitOfWork(mock_db)

    with pytest.raises(
        RuntimeError,
        match=re.escape("Use 'async with uow.atomic()' to create session")
    ):
        uow.get_session()


@pytest.mark.asyncio
async def test_nested_contexts():
    mock_db = Mock(spec=IDatabase)
    mock_session1 = AsyncMock(spec=AsyncSession)
    mock_session2 = AsyncMock(spec=AsyncSession)

    mock_db.create_session.side_effect = [
        AsyncContextManager(mock_session1),
        AsyncContextManager(mock_session2)
    ]

    uow = UnitOfWork(mock_db)

    async with uow.atomic():
        assert uow.get_session() is mock_session1

        async with uow.atomic():
            assert uow.get_session() is mock_session2

        assert uow.get_session() is mock_session1


@pytest.mark.asyncio
async def test_parallel_context():
    mock_db = Mock(spec=IDatabase)
    mock_session1 = Mock(spec=AsyncSession)
    mock_session2 = Mock(spec=AsyncSession)

    mock_db.create_session.side_effect = [
        AsyncContextManager(mock_session1),
        AsyncContextManager(mock_session2)
    ]

    uow = UnitOfWork(mock_db)

    async def first_run():
        await asyncio.sleep(1)
        async with uow.atomic():
            assert uow.get_session() is mock_session1
            await asyncio.sleep(1)
            assert uow.get_session() is mock_session1

    async def second_run():
        await asyncio.sleep(1.4)
        async with uow.atomic():
            assert uow.get_session() is mock_session2
            await asyncio.sleep(1)
            assert uow.get_session() is mock_session2

    await asyncio.gather(first_run(), second_run())
