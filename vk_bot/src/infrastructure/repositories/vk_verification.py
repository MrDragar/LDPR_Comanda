import logging
from typing import Any
from vkbottle import API, Bot
from src.domain.interfaces import IVKTaskVerificationRepository
from src.domain.entities.task import TaskType
from src.domain.exceptions import VKApiError

logger = logging.getLogger(__name__)


class VKTaskVerificationRepository(IVKTaskVerificationRepository):
    def __init__(self, bot: Bot):
        self.api = bot.api

    async def verify_task(self, task_type: TaskType, user_id: int, group_id: int,
                          post_id: int) -> bool:
        """
        Проверяет выполнение действия пользователя в ВК через официальное API.
        Для постов сообществ VK API требует отрицательный owner_id.
        """
        owner_id = -abs(group_id)

        try:
            if task_type == TaskType.LIKE:
                # Используем предоставленную сигнатуру likes.is_liked
                response = await self.api.likes.is_liked(
                    item_id=post_id,
                    type="post",
                    owner_id=owner_id,
                    user_id=user_id
                )
                # response.liked == 1 означает, что лайк стоит
                return response.liked == 1

            elif task_type == TaskType.COMMENT:
                # Используем wall.get_comments с extended=False для получения списка комментариев
                response = await self.api.wall.get_comments(
                    extended=False,
                    owner_id=owner_id,
                    post_id=post_id,
                    count=100  # Лимит для оптимизации запроса
                )
                return any(comment.from_id == user_id for comment in response.items)

            elif task_type == TaskType.REPOST:
                response = await self.api.wall.get_reposts(
                    owner_id=owner_id,
                    post_id=post_id,
                    count=100
                )
                return any(repost.from_id == user_id for repost in response.items)

            return False

        except Exception as e:
            logger.error(
                f"VK API verification failed | user={user_id} | post={post_id} | type={task_type.value} | error={e}",
                exc_info=True
            )
            raise VKApiError(f"Ошибка проверки задания через VK API: {str(e)}")