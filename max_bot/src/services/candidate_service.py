import logging

from src.domain.entities import Sources
from src.domain.entities.candidate import CandidateQuestion
from src.domain.exceptions import CandidateNotFoundError
from src.domain.interfaces import ICandidateRepository, ICandidateQuestionRepository, IUnitOfWork
from src.services.interfaces import ICandidateService

logger = logging.getLogger(__name__)


class CandidateService(ICandidateService):
    def __init__(self, candidate_repo: ICandidateRepository,
                 question_repo: ICandidateQuestionRepository, uow: IUnitOfWork):
        self.__candidate_repo = candidate_repo
        self.__question_repo = question_repo
        self.__uow = uow

    async def get_candidates(self, region: str | None, page: int, limit: int) -> dict:
        async with self.__uow.atomic():
            candidates, total = await self.__candidate_repo.get_all(region, page, limit)
            items = []
            for c in candidates:
                in_prog, completed = await self.__candidate_repo.get_petitions_counts(c.id)
                items.append({
                    "id": c.id, "fio": c.fio, "region": c.region, "photo_url": c.photo_url,
                    "topics": c.topics, "petitions_in_progress": in_prog,
                    "petitions_completed": completed
                })
            return {"items": items, "page": page, "limit": limit, "total": total}

    async def get_candidate_by_id(self, candidate_id: int) -> dict:
        async with self.__uow.atomic():
            c = await self.__candidate_repo.get_by_id(candidate_id)
            if not c:
                raise CandidateNotFoundError("Кандидат не найден")

            in_prog_pets = await self.__candidate_repo.get_petitions_by_status(candidate_id,
                                                                               "in_progress")
            completed_pets = await self.__candidate_repo.get_petitions_by_status(candidate_id,
                                                                                 "completed")

            return {
                "id": c.id, "fio": c.fio, "region": c.region, "photo_url": c.photo_url,
                "bio": c.bio, "topics": c.topics, "social_links": c.social_links,
                "petitions_in_progress": in_prog_pets, "petitions_completed": completed_pets
            }

    async def ask_question(self, candidate_id: int, author_id: int, author_source: Sources,
                           text: str,
                           is_anonymous: bool) -> dict:
        async with self.__uow.atomic():
            c = await self.__candidate_repo.get_by_id(candidate_id)
            if not c:
                raise CandidateNotFoundError("Кандидат не найден")

            question = CandidateQuestion(
                id=0, candidate_id=candidate_id, author_id=author_id,
                author_source=author_source, text=text, is_anonymous=is_anonymous
            )
            saved_q = await self.__question_repo.create(question)
            return {"question_id": saved_q.id, "status": saved_q.status}

    async def get_my_questions(self, user_id: int, source: Sources, page: int, limit: int) -> dict:
        async with self.__uow.atomic():
            questions, total = await self.__question_repo.get_by_author(user_id, source, page, limit)
            return {
                "items": [{
                    "id": q.id,
                    "candidate_id": q.candidate_id,
                    "text": q.text,
                    "status": q.status,
                    "created_at": q.created_at.isoformat(),
                    "answer_text": q.answer_text,
                    "answer_voice_url": q.answer_voice_url,
                    "answer_video_url": q.answer_video_url
                } for q in questions],
                "page": page, "limit": limit, "total": total
            }
