import logging
from src.domain.entities import PetitionStatus, Sources
from src.domain.exceptions import PetitionNotAvailableError, PetitionAlreadyTakenError, \
    CandidateNotAssignedError
from src.domain.interfaces import ICandidateRepository, IPetitionRepository, IUnitOfWork
from src.services.interfaces import ICabinetPetitionService, INotificationService

logger = logging.getLogger(__name__)


class CabinetPetitionService(ICabinetPetitionService):
    def __init__(self, candidate_repo: ICandidateRepository, petition_repo: IPetitionRepository,
                 uow: IUnitOfWork, notification_service: INotificationService):
        self.__candidate_repo = candidate_repo
        self.__petition_repo = petition_repo
        self.__uow = uow
        self.__notification_service = notification_service

    async def __get_candidate(self, user_id: int, source: Sources):
        from src.domain.entities.user import Sources
        candidate = await self.__candidate_repo.get_by_user_id(user_id, source)
        if not candidate:
            raise CandidateNotAssignedError("Вы не являетесь кандидатом")
        return candidate

    async def get_petitions(self, user_id: int, source: Sources, status: str, page: int,
                            limit: int) -> dict:
        async with self.__uow.atomic():
            candidate = await self.__get_candidate(user_id, source)

            if status == "available":
                petitions, total = await self.__petition_repo.get_available_for_candidate(
                    candidate.region, page, limit)
            else:
                # my_in_progress или my_completed
                db_status = PetitionStatus.IN_PROGRESS if status == "my_in_progress" else PetitionStatus.COMPLETED
                petitions, total = await self.__petition_repo.get_by_candidate(candidate.id,
                                                                               db_status.value,
                                                                               page, limit)

            return {
                "items": [self._to_dict(p) for p in petitions],
                "page": page, "limit": limit, "total": total
            }

    async def take_petition(self, user_id: int, source: Sources, petition_id: int,
                            initial_comment: str) -> dict:
        async with self.__uow.atomic():
            candidate = await self.__get_candidate(user_id, source)
            petition = await self.__petition_repo.get_by_id(petition_id)

            if not petition or petition.status != PetitionStatus.PUBLISHED or petition.candidate_id is not None:
                raise PetitionNotAvailableError("Петиция недоступна для взятия в работу")
            if petition.region != candidate.region:
                raise PetitionNotAvailableError("Петиция из другого региона")

            await self.__petition_repo.take_petition(petition_id, candidate.id, candidate.fio,
                                                     initial_comment)
            await self.__notification_service.notify_user(
                petition.author_id, petition.author_source, 
                f"Кандидат {candidate.fio} взял вашу петицию «{petition.title}» в работу"
            )
            return {"status": "in_progress", "message": "Петиция взята в работу"}

    async def update_progress(self, user_id: int, source: Sources, petition_id: int,
                              comment: str) -> dict:
        async with self.__uow.atomic():
            candidate = await self.__get_candidate(user_id, source)
            petition = await self.__petition_repo.get_by_id(petition_id)
            if not petition or petition.candidate_id != candidate.id:
                raise CandidateNotAssignedError("Петиция не закреплена за вами")

            await self.__petition_repo.update_progress(petition_id, comment)
            await self.__notification_service.notify_user(
                petition.author_id, petition.author_source,
                f"Обновление по работе с петицией «{petition.title}»: {comment}"
            )
            return {"updated": True, "current_progress": comment}

    async def complete_petition(self, user_id: int, source: Sources, petition_id: int, result: str,
                                result_image_url: str | None) -> dict:
        async with self.__uow.atomic():
            candidate = await self.__get_candidate(user_id, source)
            petition = await self.__petition_repo.get_by_id(petition_id)
            if not petition or petition.candidate_id != candidate.id:
                raise CandidateNotAssignedError("Петиция не закреплена за вами")

            await self.__petition_repo.complete_petition(petition_id, result, result_image_url)
            await self.__notification_service.notify_user(
                petition.author_id, petition.author_source,
                f"Работа с петицией «{petition.title}» завершена.\n\nРезультат:\n{result}"
            )
            return {"status": "completed", "message": "Петиция завершена"}

    def _to_dict(self, p) -> dict:
        return {
            "id": p.id, "title": p.title, "region": p.region, "support_count": p.support_count,
            "status": p.status.value, "created_at": p.created_at.isoformat()
        }
