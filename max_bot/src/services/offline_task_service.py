import logging
from datetime import date, timedelta
from src.domain.entities.user import Sources
from src.domain.entities.task import OfflineTask, AcceptedOfflineTask, TaskStatus
from src.domain.interfaces import IUnitOfWork, IOfflineTaskRepository, IAcceptedTaskRepository, \
    IUserRepository
from src.services.interfaces import IOfflineTaskService, IBalanceService, IUserService, \
    INotificationService
from src.domain.exceptions import DomainError

logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 5


class OfflineTaskService(IOfflineTaskService):
    def __init__(self, uow: IUnitOfWork, task_repo: IOfflineTaskRepository,
                 accepted_repo: IAcceptedTaskRepository,
                 user_repo: IUserRepository, balance_svc: IBalanceService, user_svc: IUserService,
                 notification_svc: INotificationService):
        self.__uow = uow
        self.__task_repo = task_repo
        self.__accepted_repo = accepted_repo
        self.__user_repo = user_repo
        self.__balance_svc = balance_svc
        self.__user_svc = user_svc
        self.__notification_svc = notification_svc

    async def search_tasks(self, user_id: int, user_source: Sources, page: int = 1, is_member: bool | None = None) -> tuple[list[OfflineTask], int]:
        if page < 1: raise DomainError("Страница должна быть >= 1")
        today = date.today()
        async with self.__uow.atomic():
            tasks, total = await self.__task_repo.get_active_tasks_for_user(
                user_id, user_source, today, 
                skip=(page - 1) * ITEMS_PER_PAGE, 
                limit=ITEMS_PER_PAGE,
                is_member=is_member
            )
            return tasks, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    async def check_task(self, user_id: int, user_source: Sources, task_id: int,
                         new_status: TaskStatus) -> None:
        async with self.__uow.atomic():
            task = await self.__task_repo.get_task_by_id(task_id)
            if not task: raise DomainError("Оффлайн порчение не найдено")

            if new_status not in [TaskStatus.ACCEPTED, TaskStatus.DECLINED]:
                raise DomainError("Неподдерживаемый статус для проверки")

            # Меняем статус принятой задачи
            await self.__accepted_repo.update_offline_task_status(user_id, user_source, task_id,
                                                                  new_status)

            if new_status == TaskStatus.ACCEPTED:
                await self.__balance_svc.add_balance(user_id, user_source, task.reward,
                                                     f"Подтверждение офлайн-поручения #{task_id}")
                logger.info(f"Offline task {task_id} status set to ACCEPTED for user {user_id}")

            elif new_status == TaskStatus.DECLINED:
                logger.info(f"Offline task {task_id} status set to DECLINED for user {user_id}")

    async def get_task(self, task_id: int) -> OfflineTask | None:
        async with self.__uow.atomic():
            return await self.__task_repo.get_task_by_id(task_id)

    async def get_user_tasks(self, user_id: int, user_source: Sources, page: int = 1) -> tuple[
        list[AcceptedOfflineTask], int]:
        if page < 1: raise DomainError("Страница должна быть >= 1")
        async with self.__uow.atomic():
            tasks, total = await self.__accepted_repo.get_user_accepted_offline_tasks(user_id,
                                                                                      user_source,
                                                                                      skip=(
                                                                                                       page - 1) * ITEMS_PER_PAGE,
                                                                                      limit=ITEMS_PER_PAGE)
            return tasks, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    async def cancel_task(self, user_id: int, user_source: Sources, task_id: int) -> None:
        async with self.__uow.atomic():
            await self.__accepted_repo.cancel_accepted_task(user_id, user_source, task_id,
                                                            is_online=False)
            logger.info(f"User {user_id} cancelled offline task {task_id}")

    async def create_task_by_admin(self, region: str, start_date: date, duration: int, reward: int, title: str, description: str, location: str, contacts: str, is_for_members: bool) -> OfflineTask:
        if reward <= 0: raise DomainError("Награда должна быть больше нуля")
        if duration <= 0: raise DomainError("Продолжительность должна быть больше нуля")
        end_date = start_date + timedelta(days=duration - 1)
        async with self.__uow.atomic():
            task = OfflineTask(id=0, region=region, start_date=start_date, end_date=end_date, reward=reward, title=title, description=description, location=location, contacts=contacts, is_for_members=is_for_members)
            return await self.__task_repo.create_task(task)

    async def create_task_by_personal(self, user_id: int, user_source: Sources, start_date: date, duration: int, reward: int, title: str, description: str, location: str, contacts: str, is_for_members: bool) -> OfflineTask:
        if reward <= 0: raise DomainError("Награда должна быть больше нуля")
        if duration <= 0: raise DomainError("Продолжительность должна быть больше нуля")
        end_date = start_date + timedelta(days=duration - 1)
        async with self.__uow.atomic():
            user = await self.__user_repo.get_user(user_id, user_source)
            region = user.region
            task = OfflineTask(id=0, region=region, start_date=start_date, end_date=end_date, reward=reward, title=title, description=description, location=location, contacts=contacts, is_for_members=is_for_members)
            return await self.__task_repo.create_task(task)

    async def get_in_progress_users(self, task_id: int, page: int, limit: int) -> tuple[
        list[AcceptedOfflineTask], int]:
        if page < 1: raise DomainError("Страница >= 1")
        async with self.__uow.atomic():
            return await self.__accepted_repo.get_in_progress_for_task(task_id, (page - 1) * limit,
                                                                       limit)
    
    async def get_users_for_task(self, task_id: int, page: int = 1, limit: int = 10) -> tuple[list[AcceptedOfflineTask], int]:
        if page < 1:
            raise DomainError("Страница должна быть >= 1")
        async with self.__uow.atomic():
            return await self.__accepted_repo.get_in_progress_users_for_task(task_id, (page - 1) * limit, limit)

    async def accept_offline_task(self, user_id: int, user_source: Sources, task_id: int) -> None:
        """
        Принимает офлайн задачу пользователем.
        Вся валидация и проверка ограничений вынесена сюда, в слой сервисов.
        """
        async with self.__uow.atomic():
            # 1. Проверка существования задачи
            task = await self.__task_repo.get_task_by_id(task_id)
            if not task:
                raise DomainError("Оффлайн поручение не найдено")

            # 2. Проверка на дубликат (уже принята/в процессе)
            if await self.__task_repo.is_task_accepted_by_user(user_id, user_source, task_id):
                raise DomainError("Вы уже приняли это поручение или оно находится в процессе "
                                  "выполнения")

            # 3. Проверка лимита активных задач (максимум 2)
            # Получаем все задачи пользователя и считаем только IN_PROGRESS
            all_user_tasks, _ = await self.__accepted_repo.get_user_accepted_offline_tasks(user_id, user_source, skip=0, limit=100)
            active_count = sum(1 for t in all_user_tasks if t.status == TaskStatus.IN_PROGRESS)
            if active_count >= 2:
                raise DomainError("Нельзя взять более 2 активных офлайн поручений одновременно")

            # 4. Создание записи со статусом IN_PROGRESS
            accepted = AcceptedOfflineTask(
                user_id=user_id,
                user_source=user_source,
                task=task,
                status=TaskStatus.IN_PROGRESS
            )
            await self.__accepted_repo.add_accepted_offline_task(accepted)
            logger.info(f"User {user_id} successfully accepted offline task {task_id}")
