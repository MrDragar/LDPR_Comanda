import logging
from sqlalchemy import select, func, update
from src.domain.entities.candidate import Candidate, CandidateQuestion
from src.domain.entities.petition import PetitionStatus
from src.domain.entities.user import Sources
from src.domain.interfaces import ICandidateRepository, ICandidateQuestionRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.candidate import CandidateORM, CandidateQuestionORM
from src.infrastructure.models.petition import PetitionORM

logger = logging.getLogger(__name__)


class CandidateRepository(ICandidateRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow
    
    async def create(self, candidate: Candidate) -> Candidate:
        session = self.__uow.get_session()
        orm = CandidateORM(
            user_id=candidate.user_id, source=candidate.source, fio=candidate.fio,
            region=candidate.region, photo_url=candidate.photo_url, bio=candidate.bio,
            topics=candidate.topics, social_links=candidate.social_links
        )
        session.add(orm)
        await session.flush()
        candidate.id = orm.id
        return candidate

    async def get_by_user_id(self, user_id: int, source: Sources) -> Candidate | None:
        session = self.__uow.get_session()
        stmt = select(CandidateORM).where(CandidateORM.user_id == user_id, CandidateORM.source == source)
        orm = await session.scalar(stmt)
        return self._to_domain(orm) if orm else None
    
    async def get_all(self, region: str | None, page: int, limit: int) -> tuple[
        list[Candidate], int]:
        session = self.__uow.get_session()
        stmt = select(CandidateORM)
        if region:
            stmt = stmt.where(CandidateORM.region == region)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0

        stmt = stmt.offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    async def get_by_id(self, candidate_id: int) -> Candidate | None:
        session = self.__uow.get_session()
        stmt = select(CandidateORM).where(CandidateORM.id == candidate_id)
        orm = await session.scalar(stmt)
        return self._to_domain(orm) if orm else None

    async def get_petitions_counts(self, candidate_id: int) -> tuple[int, int]:
        session = self.__uow.get_session()
        in_progress = await session.scalar(
            select(func.count()).select_from(PetitionORM).where(
                PetitionORM.candidate_id == candidate_id,
                PetitionORM.status == PetitionStatus.IN_PROGRESS
            )
        ) or 0
        completed = await session.scalar(
            select(func.count()).select_from(PetitionORM).where(
                PetitionORM.candidate_id == candidate_id,
                PetitionORM.status == PetitionStatus.COMPLETED
            )
        ) or 0
        return in_progress, completed

    async def get_petitions_by_status(self, candidate_id: int, status: str) -> list[dict]:
        session = self.__uow.get_session()
        stmt = select(PetitionORM.id, PetitionORM.title).where(
            PetitionORM.candidate_id == candidate_id,
            PetitionORM.status == status
        )
        result = await session.execute(stmt)
        return [{"id": row.id, "title": row.title} for row in result.all()]

    def _to_domain(self, orm: CandidateORM) -> Candidate:
        return Candidate(
            id=orm.id, user_id=orm.user_id, source=orm.source, fio=orm.fio,
            region=orm.region, photo_url=orm.photo_url, bio=orm.bio,
            topics=orm.topics or [], social_links=orm.social_links or {},
            created_at=orm.created_at
        )


class CandidateQuestionRepository(ICandidateQuestionRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def create(self, question: CandidateQuestion) -> CandidateQuestion:
        session = self.__uow.get_session()
        orm = CandidateQuestionORM(
            candidate_id=question.candidate_id, author_id=question.author_id,
            author_source=question.author_source, text=question.text,
            is_anonymous=question.is_anonymous
        )
        session.add(orm)
        await session.flush()
        question.id = orm.id
        return question

    async def get_by_id(self, question_id: int) -> CandidateQuestion | None:
        session = self.__uow.get_session()
        stmt = select(CandidateQuestionORM).where(CandidateQuestionORM.id == question_id)
        orm = await session.scalar(stmt)
        if not orm: return None
        return CandidateQuestion(
            id=orm.id, candidate_id=orm.candidate_id, author_id=orm.author_id,
            author_source=orm.author_source, text=orm.text, is_anonymous=orm.is_anonymous,
            answer_text=orm.answer_text, answer_voice_url=orm.answer_voice_url,
            answer_video_url=orm.answer_video_url, status=orm.status, created_at=orm.created_at
        )

    async def get_for_candidate(self, candidate_id: int, status: str | None, page: int,
                                limit: int) -> tuple[list[CandidateQuestion], int]:
        session = self.__uow.get_session()
        stmt = select(CandidateQuestionORM).where(CandidateQuestionORM.candidate_id == candidate_id)
        if status:
            stmt = stmt.where(CandidateQuestionORM.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(CandidateQuestionORM.created_at.desc()).offset(
            (page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    async def update_answer(self, question_id: int, text: str | None, voice_url: str | None,
                            video_url: str | None) -> None:
        session = self.__uow.get_session()
        await session.execute(
            update(CandidateQuestionORM).where(CandidateQuestionORM.id == question_id).values(
                answer_text=text, answer_voice_url=voice_url, answer_video_url=video_url,
                status="answered"
            )
        )
        await session.flush()

    async def get_by_author(self, user_id: int, source: Sources, page: int, limit: int) -> tuple[list[CandidateQuestion], int]:
        session = self.__uow.get_session()
        stmt = select(CandidateQuestionORM).where(
            CandidateQuestionORM.author_id == user_id,
            CandidateQuestionORM.author_source == source
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(CandidateQuestionORM.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(o) for o in result.scalars().all()], total

    def _to_domain(self, orm: CandidateQuestionORM) -> CandidateQuestion:
        return CandidateQuestion(
            id=orm.id, candidate_id=orm.candidate_id, author_id=orm.author_id,
            author_source=orm.author_source, text=orm.text, is_anonymous=orm.is_anonymous,
            answer_text=orm.answer_text, answer_voice_url=orm.answer_voice_url,
            answer_video_url=orm.answer_video_url, status=orm.status, created_at=orm.created_at
        )