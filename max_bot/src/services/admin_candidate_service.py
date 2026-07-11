import logging
from src.domain.entities.candidate import Candidate
from src.domain.entities.user import Sources, UserRole
from src.domain.exceptions import CandidateAlreadyExistsError, UserNotFoundError
from src.domain.interfaces import ICandidateRepository, IUserRepository, IUnitOfWork
from src.services.interfaces import IAdminCandidateService

logger = logging.getLogger(__name__)


class AdminCandidateService(IAdminCandidateService):
    def __init__(self, candidate_repo: ICandidateRepository, user_repo: IUserRepository,
                 uow: IUnitOfWork):
        self.__candidate_repo = candidate_repo
        self.__user_repo = user_repo
        self.__uow = uow

    async def create_candidate(self, user_id: int, source: Sources, fio: str, region: str,
                               photo_url: str | None,
                               bio: str | None, topics: list[str],
                               social_links: dict[str, str]) -> dict:
        async with self.__uow.atomic():
            user = await self.__user_repo.get_user(user_id, source)

            existing = await self.__candidate_repo.get_by_user_id(user_id, source)
            if existing:
                raise CandidateAlreadyExistsError("Пользователь уже является кандидатом")

            candidate = Candidate(
                id=0, user_id=user_id, source=source, fio=fio, region=region,
                photo_url=photo_url, bio=bio, topics=topics, social_links=social_links
            )
            created = await self.__candidate_repo.create(candidate)

            # Назначаем роль CANDIDATE пользователю
            await self.__user_repo.update_user_role(user_id, source, UserRole.CANDIDATE)

            return {"candidate_id": created.id, "message": "Кандидат успешно добавлен"}
