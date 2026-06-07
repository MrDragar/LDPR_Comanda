import logging
from typing import Any
from vkbottle import API, Bot
from src.domain.interfaces import IVKTaskVerificationRepository
from src.domain.entities.task import TaskType
from src.domain.exceptions import VKApiError

logger = logging.getLogger(__name__)


class VKTaskVerificationRepository(IVKTaskVerificationRepository):
    def __init__(self, service_token: str):
        self.api = API(token=service_token)

    async def verify_task(self, task_type: TaskType, user_id: int, group_id: int,
                          post_id: int) -> bool:
        """
        Проверяет выполнение действия пользователя в ВК через официальное API.
        Для постов сообществ VK API требует отрицательный owner_id.
        """
        owner_id = -abs(group_id)

        try:
            if task_type == TaskType.LIKE:
                response = await self.api.likes.get_list(
                    type="post",
                    filter="likes",
                    owner_id=owner_id,
                    item_id=post_id,
                    count=100
                )
                return user_id in response.items

            elif task_type == TaskType.COMMENT:
                # Используем wall.get_comments с extended=False для получения списка комментариев
                response = await self.api.wall.get_comments(
                    extended=False,
                    owner_id=owner_id,
                    post_id=post_id,
                    count=100  # Лимит для оптимизации запроса
                )
                logger.debug(response)
                return any(comment.from_id == user_id for comment in response.items)
            elif task_type == TaskType.REPOST:
                try:
                    # Шаг 1. Запрашиваем последние 20 записей со стены КОНКРЕТНОГО пользователя
                    # Параметр owner_id для пользователя должен быть положительным (его user_id)
                    user_wall = await self.api.wall.get(
                        owner_id=user_id,
                        count=20,          # 20 постов обычно хватает, чтобы найти свежий репост
                        filter="owner"     # Смотрим только посты, которые опубликовал сам владелец страницы
                    )

                    # Шаг 2. Бежим перебором по массиву "items" (записям на стене)
                    for post in user_wall.items:

                        # Шаг 3. Ищем объект copy_history (историю репоста)
                        if getattr(post, "copy_history", None):

                            # Шаг 4. Внутри copy_history проверяем оригинальный пост
                            for history_item in post.copy_history:
                                # Проверяем, совпадает ли ID группы и ID оригинального поста
                                if history_item.owner_id == owner_id and history_item.id == post_id:
                                    return True  # Репост найден!

                    return False  # Обошли все 20 постов и не нашли нужный репост

                except Exception as e:
                    # Защита от закрытых профилей: если у пользователя "замок",
                    # метод wall.get вернет ошибку Access Denied (код 15)
                    logger.warning(
                        f"Профиль пользователя {user_id} закрыт, wall.get недоступен. Ошибка: {e}"
                    )
                    raise VKApiError(
                        "Не удалось проверить репост: ваш профиль или стена закрыты приватностью. "
                        "Пожалуйста, откройте профиль на время проверки."
                    )

        except Exception as e:
            logger.error(
                f"VK API verification failed | user={user_id} | post={post_id} | type={task_type.value} | error={e}",
                exc_info=True
            )
            raise VKApiError(f"Ошибка проверки задания через VK API: {str(e)}")