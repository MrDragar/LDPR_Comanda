import logging
from src.domain.entities.user import Sources
from src.domain.interfaces import IUnitOfWork, IActiveUserRepository
from src.services.interfaces import IActiveUserService

logger = logging.getLogger(__name__)


class ActiveUserService(IActiveUserService):
    def __init__(self, uow: IUnitOfWork, repo: IActiveUserRepository):
        self.__uow = uow
        self.__repo = repo

    async def log_active_user(self, user_id: int, user_source: Sources) -> None:
        try:
            async with self.__uow.atomic():
                await self.__repo.save_if_not_exists(user_id, user_source)
        except Exception as e:
            logger.error(f"Failed to log active user {user_id}: {e}")
