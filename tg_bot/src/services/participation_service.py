from src.domain.entities.user import Sources
from src.domain.interfaces import IUnitOfWork, IParticipationRepository
from src.services.interfaces import IParticipationService


class ParticipationService(IParticipationService):
    def __init__(self, uow: IUnitOfWork, participation_repo: IParticipationRepository):
        self.__uow = uow
        self.__participation_repo = participation_repo

    async def is_participant(self, user_id: int, user_source: Sources) -> bool:
        async with self.__uow.atomic():
            return await self.__participation_repo.is_participant(user_id, user_source)

    async def activate_participation(self, user_id: int, user_source: Sources) -> int:
        async with self.__uow.atomic():
            return await self.__participation_repo.add(user_id, user_source)

    async def get_all_participation_ids(self, user_id: int, user_source: Sources) -> list[int]:
        async with self.__uow.atomic():
            return await self.__participation_repo.get_all_participation_ids(user_id, user_source)
