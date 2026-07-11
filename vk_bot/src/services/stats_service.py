import logging
from datetime import datetime, timedelta, UTC
from src.domain.entities.user import Sources
from src.domain.exceptions import NotFoundRegionError
from src.domain.interfaces import IStatsRepository, IUnitOfWork
from src.services.interfaces import IStatsService

logger = logging.getLogger(__name__)


class StatsService(IStatsService):
    def __init__(self, stats_repo: IStatsRepository, uow: IUnitOfWork):
        self.__stats_repo = stats_repo
        self.__uow = uow

    async def get_region_counter(self, region: str) -> dict:
        async with self.__uow.atomic():
            count = await self.__stats_repo.get_region_user_count(region)
            if count == 0:
                raise NotFoundRegionError("Регион не найден или в нем нет пользователей")
            return {"region": region, "count": count, "is_real": True}

    async def get_weekly_report(self, user_id: int, source: str) -> dict:
        async with self.__uow.atomic():
            stats = await self.__stats_repo.get_user_weekly_stats(user_id, Sources(source))

            now = datetime.now(UTC)
            week_ago = now - timedelta(days=7)

            impact_messages = []
            if stats["petitions_supported"] > 0:
                impact_messages.append(
                    f"Благодаря тебе поддержано {stats['petitions_supported']} петиций")
            if stats["tasks_completed"] > 0:
                impact_messages.append(f"Ты выполнил {stats['tasks_completed']} заданий")
            if stats["petitions_created"] > 0:
                impact_messages.append(f"Ты создал {stats['petitions_created']} петиций")
            if not impact_messages:
                impact_messages.append(
                    "Ты еще не участвовал в активностях на этой неделе. Самое время начать!")

            return {
                "period": {
                    "from": week_ago.strftime("%Y-%m-%d"),
                    "to": now.strftime("%Y-%m-%d")
                },
                "petitions_created": stats["petitions_created"],
                "petitions_supported": stats["petitions_supported"],
                "tasks_completed": stats["tasks_completed"],
                "balance_earned": stats["balance_earned"],
                "impact_messages": impact_messages
            }
