from sqlalchemy import select
from src.domain.entities.user import Sources
from src.domain.interfaces import IParticipationRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.participation import ParticipationORM


class ParticipationRepository(IParticipationRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def add(self, user_id: int, user_source: Sources) -> int:
        session = self.__uow.get_session()
        participation_orm = ParticipationORM(user_id=user_id, user_source=user_source)
        session.add(participation_orm)
        await session.flush()
        return participation_orm.id

    async def is_participant(self, user_id: int, user_source: Sources) -> bool:
        session = self.__uow.get_session()
        stmt = select(ParticipationORM).where(
            ParticipationORM.user_id == user_id,
            ParticipationORM.user_source == user_source
        ).limit(1)
        result = await session.scalar(stmt)
        return result is not None

    async def get_all_participation_ids(self, user_id: int, user_source: Sources) -> list[int]:
        session = self.__uow.get_session()
        stmt = select(ParticipationORM.id).where(
            ParticipationORM.user_id == user_id,
            ParticipationORM.user_source == user_source
        )
        result = await session.scalars(stmt)
        return list(result.all())
