import logging
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func
from src.domain.entities.user import Sources
from src.domain.entities.task import TaskStatus
from src.domain.interfaces import IStatsRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.user import UserORM
from src.infrastructure.models.petition import PetitionORM, PetitionSupportORM
from src.infrastructure.models.task import AcceptedOnlineTaskORM, AcceptedOfflineTaskORM, TransactionORM

logger = logging.getLogger(__name__)


class StatsRepository(IStatsRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_region_user_count(self, region: str) -> int:
        session = self.__uow.get_session()
        count = await session.scalar(
            select(func.count()).select_from(UserORM).where(UserORM.region == region)
        )
        return count or 0

    async def get_user_weekly_stats(self, user_id: int, source: Sources) -> dict:
        session = self.__uow.get_session()
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)

        pets_created = await session.scalar(
            select(func.count()).select_from(PetitionORM).where(
                PetitionORM.author_id == user_id,
                PetitionORM.author_source == source,
                PetitionORM.created_at >= week_ago
            )
        ) or 0

        pets_supported = await session.scalar(
            select(func.count()).select_from(PetitionSupportORM).where(
                PetitionSupportORM.user_id == user_id,
                PetitionSupportORM.user_source == source,
                PetitionSupportORM.created_at >= week_ago
            )
        ) or 0

        tasks_online = await session.scalar(
            select(func.count()).select_from(AcceptedOnlineTaskORM).where(
                AcceptedOnlineTaskORM.user_id == user_id,
                AcceptedOnlineTaskORM.user_source == source,
                AcceptedOnlineTaskORM.status == TaskStatus.ACCEPTED
            )
        ) or 0

        tasks_offline = await session.scalar(
            select(func.count()).select_from(AcceptedOfflineTaskORM).where(
                AcceptedOfflineTaskORM.user_id == user_id,
                AcceptedOfflineTaskORM.user_source == source,
                AcceptedOfflineTaskORM.status == TaskStatus.ACCEPTED
            )
        ) or 0

        balance_earned = await session.scalar(
            select(func.coalesce(func.sum(TransactionORM.amount), 0)).where(
                TransactionORM.user_id == user_id,
                TransactionORM.user_source == source,
                TransactionORM.amount > 0,
                TransactionORM.created_at >= week_ago
            )
        ) or 0

        return {
            "petitions_created": pets_created,
            "petitions_supported": pets_supported,
            "tasks_completed": tasks_online + tasks_offline,
            "balance_earned": int(balance_earned)
        }
