import logging
from src.domain.entities.petition import PetitionStatus
from src.domain.exceptions import PetitionError, PetitionAlreadyModeratedError
from src.domain.interfaces import IPetitionRepository, IUnitOfWork
from src.services.interfaces import IAdminPetitionService, INotificationService

logger = logging.getLogger(__name__)


class AdminPetitionService(IAdminPetitionService):
    def __init__(self, petition_repo: IPetitionRepository, uow: IUnitOfWork,
                 notification_service: INotificationService):
        self.__petition_repo = petition_repo
        self.__uow = uow
        self.__notify_src = notification_service

    async def approve_petition(self, petition_id: int) -> dict:
        async with self.__uow.atomic():
            petition = await self.__petition_repo.get_by_id(petition_id)
            if not petition:
                raise PetitionError("Петиция не найдена")
            if petition.status != PetitionStatus.MODERATION:
                raise PetitionAlreadyModeratedError("Петиция уже была модерирована")

            await self.__petition_repo.update_status(petition_id, PetitionStatus.PUBLISHED)
            await self.__notify_src.notify_user(
                petition.author_id, petition.author_source,
                text=f"Ваша петиция «{petition.title}» прошла модерацию и была опубликована!"
            )
            return {"status": "published", "message": "Петиция одобрена и опубликована"}

    async def reject_petition(self, petition_id: int, reason: str) -> dict:
        async with self.__uow.atomic():
            petition = await self.__petition_repo.get_by_id(petition_id)
            if not petition:
                raise PetitionError("Петиция не найдена")
            if petition.status != PetitionStatus.MODERATION:
                raise PetitionAlreadyModeratedError("Петиция уже была модерирована")

            await self.__petition_repo.update_status(petition_id, PetitionStatus.REJECTED)
            await self.__notify_src.notify_user(
                petition.author_id, petition.author_source,
                text=f"Ваша петиция «{petition}» не прошла проверку.\n\nПричина:\n{reason}"
            )
            return {"status": "rejected", "message": "Петиция отклонена"}
