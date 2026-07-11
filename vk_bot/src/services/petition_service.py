import logging
from src.domain.entities.petition import Petition, PetitionStatus, PetitionScope
from src.domain.entities.user import Sources, UserRole
from src.domain.exceptions import PetitionError
from src.domain.interfaces import IPetitionRepository, IUserRepository, IUnitOfWork
from src.services.interfaces import IPetitionService

logger = logging.getLogger(__name__)


class PetitionService(IPetitionService):
    def __init__(self, petition_repo: IPetitionRepository, user_repo: IUserRepository,
                 uow: IUnitOfWork):
        self.__petition_repo = petition_repo
        self.__user_repo = user_repo
        self.__uow = uow

    async def create_petition(self, user_id: int, source: Sources, title: str, description: str,
                              image_url: str | None, scope: str) -> Petition:
        async with self.__uow.atomic():
            user = await self.__user_repo.get_user(user_id, source)
            if scope == PetitionScope.FEDERAL.value and user.role != UserRole.STAFF_CA:
                raise PetitionError("Только сотрудник ЦА может создавать федеральные петиции")

            author_name = f"{user.surname} {user.name[0] if user.name else ''}.".strip()

            petition = Petition(
                id=0, title=title, description=description, region=user.region or "Россия",
                scope=PetitionScope(scope), image_url=image_url, author_id=user_id,
                author_source=source, author_name=author_name, status=PetitionStatus.MODERATION
            )
            return await self.__petition_repo.create(petition)

    async def get_petition(self, petition_id: int, user_id: int | None, source: Sources | None) -> dict:
        async with self.__uow.atomic():
            petition = await self.__petition_repo.get_by_id(petition_id)
            if not petition:
                raise PetitionError("Петиция не найдена")

            await self.__petition_repo.increment_view(petition_id)

            is_supported = False
            if user_id and source:
                is_supported = await self.__petition_repo.is_supported(petition_id, user_id, source)

            return self._to_dict(petition, is_supported)

    async def get_feed(self, user_id: int, source: Sources, scope: str | None, region: str | None, limit: int) -> list[dict]:
        async with self.__uow.atomic():
            petitions = await self.__petition_repo.get_feed(scope, region, limit, user_id, source)
            return [self._to_dict(p) for p in petitions]

    async def get_all(self, scope: str | None, status: str | None, region: str | None, page: int,
                      limit: int) -> dict:
        async with self.__uow.atomic():
            petitions, total = await self.__petition_repo.get_all(scope, status, region, page,
                                                                  limit)
            return {
                "items": [self._to_dict(p) for p in petitions],
                "page": page, "limit": limit, "total": total
            }

    async def get_my(self, user_id: int, source: Sources, page: int, limit: int) -> dict:
        async with self.__uow.atomic():
            petitions, total = await self.__petition_repo.get_my(user_id, source, page, limit)
            return {
                "items": [self._to_dict(p) for p in petitions],
                "page": page, "limit": limit, "total": total
            }

    async def get_supported(self, user_id: int, source: Sources, page: int, limit: int) -> dict:
        async with self.__uow.atomic():
            petitions, total = await self.__petition_repo.get_supported(user_id, source, page,
                                                                        limit)
            return {
                "items": [self._to_dict(p) for p in petitions],
                "page": page, "limit": limit, "total": total
            }

    async def support_petition(self, petition_id: int, user_id: int, source: Sources) -> int:
        async with self.__uow.atomic():
            petition = await self.__petition_repo.get_by_id(petition_id)
            if not petition:
                raise PetitionError("Петиция не найдена")
            if petition.status != PetitionStatus.PUBLISHED:
                raise PetitionError("Петиция на модерации или отклонена")

            success = await self.__petition_repo.support(petition_id, user_id, source)
            if not success:
                raise PetitionError("Вы уже поддержали эту петицию")

            return petition.support_count + 1

    async def skip_petition(self, petition_id: int, user_id: int, source: Sources) -> dict:
        async with self.__uow.atomic():
            await self.__petition_repo.skip_petition(petition_id, user_id, source)
        return {"skipped": True}

    async def share_petition(self, petition_id: int) -> dict:
        async with self.__uow.atomic():
            await self.__petition_repo.increment_share(petition_id)
            return {
                "share_url_vk": f"https://vk.me/app...?ref=pet_{petition_id}_vk",
                "share_url_tg": f"https://t.me/app...?start=pet_{petition_id}_tg",
                "share_url_max": f"https://max.ru/app...?start=pet_{petition_id}_max"
            }

    def _to_dict(self, p: Petition, is_supported: bool = False) -> dict:
        return {
            "id": p.id, "title": p.title, "description": p.description,
            "region": p.region, "scope": p.scope.value, "image_url": p.image_url,
            "author_id": p.author_id, "author_name": p.author_name,
            "support_count": p.support_count, "share_count": p.share_count,
            "view_count": p.view_count, "status": p.status.value,
            "candidate_id": p.candidate_id, "candidate_name": p.candidate_name,
            "candidate_progress": p.candidate_progress, "candidate_result": p.candidate_result,
            "is_supported_by_me": is_supported, "created_at": p.created_at.isoformat(),
            "candidate_result_image": p.candidate_result_image
        }
