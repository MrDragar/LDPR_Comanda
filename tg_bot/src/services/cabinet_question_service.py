import logging
from src.domain.exceptions import CandidateNotAssignedError, QuestionNotFoundError
from src.domain.interfaces import ICandidateRepository, ICandidateQuestionRepository, IUnitOfWork
from src.services.interfaces import ICabinetQuestionService

logger = logging.getLogger(__name__)


class CabinetQuestionService(ICabinetQuestionService):
    def __init__(self, candidate_repo: ICandidateRepository,
                 question_repo: ICandidateQuestionRepository, uow: IUnitOfWork):
        self.__candidate_repo = candidate_repo
        self.__question_repo = question_repo
        self.__uow = uow

    async def __get_candidate(self, user_id: int, source: str):
        from src.domain.entities.user import Sources
        candidate = await self.__candidate_repo.get_by_user_id(user_id, Sources(source))
        if not candidate:
            raise CandidateNotAssignedError("Вы не являетесь кандидатом")
        return candidate

    async def get_questions(self, user_id: int, source: str, status: str | None, page: int,
                            limit: int) -> dict:
        async with self.__uow.atomic():
            candidate = await self.__get_candidate(user_id, source)
            questions, total = await self.__question_repo.get_for_candidate(candidate.id, status,
                                                                            page, limit)

            return {
                "items": [{
                    "id": q.id, "text": q.text, "is_anonymous": q.is_anonymous,
                    "author_name": "Аноним" if q.is_anonymous else f"User #{q.author_id}",
                    "status": q.status, "created_at": q.created_at.isoformat(),
                    "answer_text": q.answer_text,
                    "answer_voice_url": q.answer_voice_url,
                    "answer_video_url": q.answer_video_url
                } for q in questions],
                "page": page, "limit": limit, "total": total
            }

    async def answer_question(self, user_id: int, source: str, question_id: int, text: str | None,
                              voice_url: str | None, video_url: str | None) -> dict:
        async with self.__uow.atomic():
            candidate = await self.__get_candidate(user_id, source)
            q = await self.__question_repo.get_by_id(question_id)
            if not q or q.candidate_id != candidate.id:
                raise QuestionNotFoundError("Вопрос не найден или не закреплен за вами")

            await self.__question_repo.update_answer(question_id, text, voice_url, video_url)
            return {"answered": True, "question_id": question_id}
