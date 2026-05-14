import logging
from datetime import date, timedelta
from sqlalchemy import select, func, or_, and_
from src.domain.entities.task import OnlineTask, OfflineTask, AcceptedOnlineTask, \
    AcceptedOfflineTask, TaskStatus
from src.domain.entities.user import Sources
from src.domain.interfaces import IOnlineTaskRepository, IOfflineTaskRepository, \
    IAcceptedTaskRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.task import (
    OnlineTaskORM, OfflineTaskORM, AcceptedOnlineTaskORM, AcceptedOfflineTaskORM
)

logger = logging.getLogger(__name__)


class OnlineTaskRepository(IOnlineTaskRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date,
                                        skip: int, limit: int) -> tuple[list[OnlineTask], int]:
        session = self.__uow.get_session()
        end_date = today + timedelta(days=1)  # tasks available until end of duration

        # Базовый запрос на активные задачи
        base_stmt = select(OnlineTaskORM).where(
            and_(
                OnlineTaskORM.date <= today,
                OnlineTaskORM.date + OnlineTaskORM.duration >= today
            )
        )

        # Исключаем уже принятые/в процессе
        subquery = (
            select(AcceptedOnlineTaskORM.task_id)
            .where(
                AcceptedOnlineTaskORM.user_id == user_id,
                AcceptedOnlineTaskORM.user_source == user_source,
                AcceptedOnlineTaskORM.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.ACCEPTED])
            )
        )
        final_stmt = base_stmt.where(OnlineTaskORM.id.notin_(subquery)).order_by(OnlineTaskORM.date)

        # Пагинация и подсчёт
        count_stmt = select(func.count()).select_from(final_stmt.subquery())
        total = await session.scalar(count_stmt) or 0

        paginated_stmt = final_stmt.offset(skip).limit(limit)
        result = await session.execute(paginated_stmt)
        tasks_orm = result.scalars().all()

        tasks = [
            OnlineTask(
                id=t.id, date=t.date, duration=t.duration,
                type=t.type, reward=t.reward, post_id=t.post_id, group_id=t.group_id
            ) for t in tasks_orm
        ]
        logger.debug(f"Found {len(tasks)} active online tasks for user {user_id}")
        return tasks, total

    async def get_task_by_id(self, task_id: int) -> OnlineTask | None:
        session = self.__uow.get_session()
        stmt = select(OnlineTaskORM).where(OnlineTaskORM.id == task_id)
        orm = await session.scalar(stmt)
        if not orm: return None
        return OnlineTask(id=orm.id, date=orm.date, duration=orm.duration, type=orm.type,
                          reward=orm.reward, post_id=orm.post_id, group_id=orm.group_id)

    async def create_task(self, task: OnlineTask) -> OnlineTask:
        session = self.__uow.get_session()
        orm = OnlineTaskORM(**{k: v for k, v in vars(task).items() if k != 'id'})
        session.add(orm)
        await session.flush()
        task.id = orm.id
        logger.info(f"Created online task {task.id}")
        return task

    async def is_task_accepted_by_user(self, user_id: int, user_source: Sources,
                                       task_id: int) -> bool:
        session = self.__uow.get_session()
        stmt = select(AcceptedOnlineTaskORM).where(
            AcceptedOnlineTaskORM.user_id == user_id,
            AcceptedOnlineTaskORM.user_source == user_source,
            AcceptedOnlineTaskORM.task_id == task_id,
            AcceptedOnlineTaskORM.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.ACCEPTED])
        )
        return (await session.scalar(stmt)) is not None


class OfflineTaskRepository(IOfflineTaskRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date,
                                        skip: int, limit: int) -> tuple[list[OfflineTask], int]:
        session = self.__uow.get_session()
        base_stmt = select(OfflineTaskORM).where(
            and_(
                OfflineTaskORM.date <= today,
                OfflineTaskORM.date >= today - timedelta(days=30)
                # Пример: доступность в течение месяца
            )
        )
        subquery = (
            select(AcceptedOfflineTaskORM.task_id)
            .where(
                AcceptedOfflineTaskORM.user_id == user_id,
                AcceptedOfflineTaskORM.user_source == user_source,
                AcceptedOfflineTaskORM.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.ACCEPTED])
            )
        )
        final_stmt = base_stmt.where(OfflineTaskORM.id.notin_(subquery)).order_by(
            OfflineTaskORM.date)
        count_stmt = select(func.count()).select_from(final_stmt.subquery())
        total = await session.scalar(count_stmt) or 0

        paginated_stmt = final_stmt.offset(skip).limit(limit)
        result = await session.execute(paginated_stmt)
        tasks_orm = result.scalars().all()

        tasks = [
            OfflineTask(id=t.id, region=t.region, date=t.date, reward=t.reward, title=t.title,
                        description=t.description, location=t.location, contacts=t.contacts)
            for t in tasks_orm
        ]
        logger.debug(f"Found {len(tasks)} active offline tasks for user {user_id}")
        return tasks, total

    async def get_task_by_id(self, task_id: int) -> OfflineTask | None:
        session = self.__uow.get_session()
        stmt = select(OfflineTaskORM).where(OfflineTaskORM.id == task_id)
        orm = await session.scalar(stmt)
        if not orm: return None
        return OfflineTask(id=orm.id, region=orm.region, date=orm.date, reward=orm.reward,
                           title=orm.title, description=orm.description, location=orm.location,
                           contacts=orm.contacts)

    async def create_task(self, task: OfflineTask) -> OfflineTask:
        session = self.__uow.get_session()
        orm = OfflineTaskORM(**{k: v for k, v in vars(task).items() if k != 'id'})
        session.add(orm)
        await session.flush()
        task.id = orm.id
        logger.info(f"Created offline task {task.id}")
        return task

    async def is_task_accepted_by_user(self, user_id: int, user_source: Sources,
                                       task_id: int) -> bool:
        session = self.__uow.get_session()
        stmt = select(AcceptedOfflineTaskORM).where(
            AcceptedOfflineTaskORM.user_id == user_id,
            AcceptedOfflineTaskORM.user_source == user_source,
            AcceptedOfflineTaskORM.task_id == task_id,
            AcceptedOfflineTaskORM.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.ACCEPTED])
        )
        return (await session.scalar(stmt)) is not None


class AcceptedTaskRepository(IAcceptedTaskRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def accept_online_task(self, accepted: AcceptedOnlineTask) -> AcceptedOnlineTask:
        session = self.__uow.get_session()
        orm = AcceptedOnlineTaskORM(
            user_id=accepted.user_id, user_source=accepted.user_source,
            task_id=accepted.task.id, status=accepted.status
        )
        session.add(orm)
        await session.flush()
        logger.info(f"Accepted online task {accepted.task.id} for user {accepted.user_id}")
        return accepted

    async def update_offline_task_status(self, user_id: int, user_source: Sources, task_id: int,
                                         status: TaskStatus) -> None:
        session = self.__uow.get_session()
        stmt = select(AcceptedOfflineTaskORM).where(
            AcceptedOfflineTaskORM.user_id == user_id,
            AcceptedOfflineTaskORM.user_source == user_source,
            AcceptedOfflineTaskORM.task_id == task_id
        )
        orm = await session.scalar(stmt)
        if orm:
            orm.status = status
            logger.info(f"Updated offline task {task_id} status to {status.value}")
        else:
            logger.warning(
                f"Tried to update status for non-existing offline accepted task {task_id}")

    async def get_user_accepted_offline_tasks(self, user_id: int, user_source: Sources, skip: int,
                                              limit: int) -> tuple[list[AcceptedOfflineTask], int]:
        session = self.__uow.get_session()
        base_stmt = select(AcceptedOfflineTaskORM).where(
            AcceptedOfflineTaskORM.user_id == user_id,
            AcceptedOfflineTaskORM.user_source == user_source
        )
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await session.scalar(count_stmt) or 0

        result = await session.execute(base_stmt.offset(skip).limit(limit))
        aorms = result.scalars().all()

        tasks_orm_map = {t.id: t for t in
                         await session.execute(select(OfflineTaskORM)).scalars().all()}
        tasks = []
        for aorm in aorms:
            task_orm = tasks_orm_map.get(aorm.task_id)
            if task_orm:
                tasks.append(AcceptedOfflineTask(
                    user_id=user_id, user_source=user_source,
                    task=OfflineTask(id=task_orm.id, region=task_orm.region, date=task_orm.date,
                                     reward=task_orm.reward, title=task_orm.title,
                                     description=task_orm.description, location=task_orm.location,
                                     contacts=task_orm.contacts),
                    status=aorm.status
                ))
        return tasks, total

    async def cancel_accepted_task(self, user_id: int, user_source: Sources, task_id: int,
                                   is_online: bool) -> None:
        session = self.__uow.get_session()
        model = AcceptedOnlineTaskORM if is_online else AcceptedOfflineTaskORM
        stmt = select(model).where(
            model.user_id == user_id, model.user_source == user_source, model.task_id == task_id
        )
        orm = await session.scalar(stmt)
        if orm:
            await session.delete(orm)
            logger.info(f"Cancelled accepted task {task_id} for user {user_id}")
