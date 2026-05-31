import logging
from sqlalchemy import select
from src.domain.entities.user import Sources
from src.domain.interfaces import ILearningRepository
from src.domain.entities.learning import LearningTestAttempt
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.learning import LearningTestAttemptORM

logger = logging.getLogger(__name__)


class LearningRepository(ILearningRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_attempt(self, user_id: int, user_source: Sources) -> LearningTestAttempt | None:
        session = self.__uow.get_session()
        stmt = select(LearningTestAttemptORM).where(
            LearningTestAttemptORM.user_id == user_id,
            LearningTestAttemptORM.user_source == user_source
        )
        orm = await session.scalar(stmt)
        if not orm: return None
        return LearningTestAttempt(
            user_id=orm.user_id, user_source=orm.user_source,
            score=orm.score, passed_at=orm.passed_at, is_passed=orm.is_passed
        )

    async def save_attempt(self, attempt: LearningTestAttempt) -> None:
        session = self.__uow.get_session()
        existing = await session.get(LearningTestAttemptORM, (attempt.user_id, attempt.user_source))
        if existing:
            existing.score = attempt.score
            existing.passed_at = attempt.passed_at
            existing.is_passed = attempt.is_passed
            logger.info(f"Updated learning attempt for user {attempt.user_id}")
        else:
            orm = LearningTestAttemptORM(**{k: v for k, v in vars(attempt).items()})
            session.add(orm)
            logger.info(f"Created learning attempt for user {attempt.user_id}")
        await session.flush()
    
    async def is_passed(self, user_id: int, user_source: Sources) -> bool:
        session = self.__uow.get_session()
        stmt = select(LearningTestAttemptORM).where(
            LearningTestAttemptORM.user_id == user_id,
            LearningTestAttemptORM.user_source == user_source,
            LearningTestAttemptORM.is_passed == True
        )
        return (await session.scalar(stmt)) is not None
