import logging
from datetime import date
from src.domain.entities.user import Sources, UserGrade
from src.domain.entities.task import OnlineTask, AcceptedOnlineTask, TaskStatus, TaskType
from src.domain.interfaces import (IUnitOfWork, IOnlineTaskRepository, IAcceptedTaskRepository,
                                   IVKTaskVerificationRepository)
from src.services.interfaces import (IOnlineTaskService, IBalanceService, IUserService, 
                                     INotificationService)
from src.domain.exceptions import DomainError, TaskNotCompletedError

logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 4


class OnlineTaskService(IOnlineTaskService):
    def __init__(self, uow: IUnitOfWork, task_repo: IOnlineTaskRepository,
                 accepted_repo: IAcceptedTaskRepository, balance_svc: IBalanceService,
                 user_svc: IUserService, notification_svc: INotificationService,
                 vk_verify_repo: IVKTaskVerificationRepository):
        self.__uow = uow
        self.__task_repo = task_repo
        self.__accepted_repo = accepted_repo
        self.__balance_svc = balance_svc
        self.__user_svc = user_svc
        self.__notification_svc = notification_svc
        self.__vk_verify_repo = vk_verify_repo

    async def search_tasks(self, user_id: int, user_source: Sources, page: int = 1, is_member: bool | None = None) -> tuple[list[OnlineTask], int]:
        if page < 1: raise DomainError("Страница должна быть >= 1")
        today = date.today()
        async with self.__uow.atomic():
            tasks, total = await self.__task_repo.get_active_tasks_for_user(
                user_id, user_source, today,
                skip=(page - 1) * ITEMS_PER_PAGE,
                limit=ITEMS_PER_PAGE,
                is_member=is_member
            )
            pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
            return tasks, pages

    async def check_task(self, user_id: int, user_source: Sources, task_id: int) -> None:
        async with self.__uow.atomic():
            task = await self.__task_repo.get_task_by_id(task_id)
            if not task: raise DomainError("Поручение не найдено")

            if await self.__task_repo.is_task_accepted_by_user(user_id, user_source, task_id):
                raise DomainError("Вы уже взяли это поручение или оно в процессе")
            try:
                group_id, post_id = self.__task_repo._parse_vk_url(task.url)
            except ValueError as e:
                raise DomainError(f"Ошибка парсинга ссылки поручения: {e}")

            is_completed = await self.__vk_verify_repo.verify_task(
                task.type, user_id, group_id, post_id
            )
            if not is_completed:
                raise TaskNotCompletedError("Поручение не выполнено. Пожалуйста, выполните "
                                            "поручение в ВК и попробуйте снова.")

            accepted = AcceptedOnlineTask(user_id=user_id, user_source=user_source, task=task,
                                          status=TaskStatus.ACCEPTED)
            await self.__accepted_repo.accept_online_task(accepted)

            # Начисляем награду
            await self.__balance_svc.add_balance(user_id, user_source, task.reward,
                                                 f"Выполнение онлайн-поручения #{task_id}")
            logger.info(f"Task {task_id} checked and accepted for user {user_id}")

    async def get_task(self, task_id: int) -> OnlineTask | None:
        async with self.__uow.atomic():
            return await self.__task_repo.get_task_by_id(task_id)

    async def create_task(self, date: date, duration: int, type: TaskType, reward: int, url: str | None, title: str, description: str, is_for_members: bool) -> OnlineTask:
        if reward <= 0: raise DomainError("Награда должна быть больше нуля")
        if duration <= 0: raise DomainError("Длительность должна быть больше нуля")
        if type != TaskType.OTHER and url and not url.startswith("https://vk.com/"):
            raise DomainError("Ссылка должна быть валидным URL ВКонтакте")
        async with self.__uow.atomic():
            task = OnlineTask(
                id=0, date=date, duration=duration, type=type, reward=reward, url=url,
                title=title, description=description, is_for_members=is_for_members
            )
            return await self.__task_repo.create_task(task)

    async def submit_tg_online_task(self, user_id: int, user_source: Sources, task_id: int) -> None:
        async with self.__uow.atomic():
            task = await self.__task_repo.get_task_by_id(task_id)
            if not task: raise DomainError("Поручение не найдено")
            if await self.__task_repo.is_task_accepted_by_user(user_id, user_source, task_id):
                raise DomainError("Вы уже взяли это поручение или оно в процессе")

            accepted = AcceptedOnlineTask(
                user_id=user_id, user_source=user_source, task=task, status=TaskStatus.IN_PROGRESS
            )
            await self.__accepted_repo.accept_online_task(accepted)
            logger.info(f"TG Online task {task_id} submitted for verification by user {user_id}")

    async def accept_tg_online_task(self, user_id: int, user_source: Sources, task_id: int) -> None:
        async with self.__uow.atomic():
            task = await self.__task_repo.get_task_by_id(task_id)
            if not task: raise DomainError("Поручение не найдено")
            await self.__accepted_repo.update_online_task_status(user_id, user_source, task_id,
                                                                 TaskStatus.ACCEPTED)
            await self.__balance_svc.add_balance(user_id, user_source, task.reward,
                                                 f"Выполнение онлайн-поручения #{task_id} (ТГ)")

    async def decline_tg_online_task(self, user_id: int, user_source: Sources,
                                     task_id: int) -> None:
        async with self.__uow.atomic():
            await self.__accepted_repo.update_online_task_status(user_id, user_source, task_id,
                                                                 TaskStatus.DECLINED)
