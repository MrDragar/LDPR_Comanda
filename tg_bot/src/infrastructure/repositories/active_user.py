import logging
from sqlalchemy import select
from src.domain.entities.user import Sources
from src.domain.interfaces import IActiveUserRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.active_user import ActiveUserORM

logger = logging.getLogger(__name__)


class ActiveUserRepository(IActiveUserRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def save_if_not_exists(self, user_id: int, user_source: Sources) -> None:
        session = self.__uow.get_session()
        stmt = select(ActiveUserORM).where(
            ActiveUserORM.user_id == user_id,
            ActiveUserORM.user_source == user_source
        ).limit(1)
        existing = await session.scalar(stmt)
        if existing:
            return

        orm = ActiveUserORM(user_id=user_id, user_source=user_source)
        session.add(orm)
        await session.flush()
        logger.debug(f"Logged active user {user_id} ({user_source.value})")
