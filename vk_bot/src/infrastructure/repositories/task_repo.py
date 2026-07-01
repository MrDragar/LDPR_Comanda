import logging
import re
from datetime import date, timedelta
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.sql import expression

from src.domain.entities.task import OnlineTask, OfflineTask, AcceptedOnlineTask, \
    AcceptedOfflineTask, TaskStatus
from src.domain.entities.user import Sources
from src.domain.interfaces import IOnlineTaskRepository, IOfflineTaskRepository, \
    IAcceptedTaskRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models import UserORM
from src.infrastructure.models.task import (
    OnlineTaskORM, OfflineTaskORM, AcceptedOnlineTaskORM, AcceptedOfflineTaskORM
)

logger = logging.getLogger(__name__)


class OnlineTaskRepository(IOnlineTaskRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date,
                                        skip: int, limit: int, is_member: bool | None = None) -> \
    tuple[list[OnlineTask], int]:
        session = self.__uow.get_session()
        base_stmt = select(OnlineTaskORM).where(
            and_(
                OnlineTaskORM.date <= today,
                text("DATE_ADD(date, INTERVAL duration DAY) >= :today").bindparams(today=today)            )
        )

        # Фильтрация по членству в партии
        if is_member is not None:
            base_stmt = base_stmt.where(OnlineTaskORM.is_for_members == is_member)

        subquery = (
            select(AcceptedOnlineTaskORM.task_id)
            .where(
                AcceptedOnlineTaskORM.user_id == user_id,
                AcceptedOnlineTaskORM.user_source == user_source,
                AcceptedOnlineTaskORM.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.ACCEPTED])
            )
        )
        final_stmt = base_stmt.where(OnlineTaskORM.id.notin_(subquery)).order_by(OnlineTaskORM.date)
        count_stmt = select(func.count()).select_from(final_stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        paginated_stmt = final_stmt.offset(skip).limit(limit)
        result = await session.execute(paginated_stmt)
        tasks_orm = result.scalars().all()

        tasks = [
            OnlineTask(
                id=t.id, date=t.date, duration=t.duration,
                type=t.type, reward=t.reward, url=t.url,
                title=t.title, description=t.description,
                is_for_members=t.is_for_members
            ) for t in tasks_orm
        ]
        return tasks, total

    async def get_task_by_id(self, task_id: int) -> OnlineTask | None:
        session = self.__uow.get_session()
        stmt = select(OnlineTaskORM).where(OnlineTaskORM.id == task_id)
        orm = await session.scalar(stmt)
        if not orm: return None
        return OnlineTask(id=orm.id, date=orm.date, duration=orm.duration, type=orm.type,
                          reward=orm.reward, url=orm.url, title=orm.title,
                          description=orm.description,
                          is_for_members=orm.is_for_members)

    async def create_task(self, task: OnlineTask) -> OnlineTask:
        session = self.__uow.get_session()
        orm = OnlineTaskORM(**{k: v for k, v in vars(task).items() if k != 'id'})
        session.add(orm)
        await session.flush()
        task.id = orm.id
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

    @staticmethod
    def _parse_vk_url(url: str) -> tuple[int, int]:
        pattern = r'vk\.com/wall-?(\d+)_(\d+)'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Не удалось распарсить VK URL: {url}")
        owner_id = int(match.group(1))
        post_id = int(match.group(2))
        group_id = abs(owner_id)
        return group_id, post_id


class OfflineTaskRepository(IOfflineTaskRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_active_tasks_for_user(self, user_id: int, user_source: Sources, today: date,
                                        skip: int, limit: int, is_member: bool | None = None) -> \
    tuple[list[OfflineTask], int]:
        session = self.__uow.get_session()
        base_stmt = select(OfflineTaskORM).where(
            and_(
                OfflineTaskORM.start_date <= today,
                OfflineTaskORM.end_date >= today
            )
        )
        if is_member is not None:
            base_stmt = base_stmt.where(OfflineTaskORM.is_for_members == is_member)
        subquery = (
            select(AcceptedOfflineTaskORM.task_id)
            .where(
                AcceptedOfflineTaskORM.user_id == user_id,
                AcceptedOfflineTaskORM.user_source == user_source,
                AcceptedOfflineTaskORM.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.ACCEPTED])
            )
        )
        final_stmt = base_stmt.where(OfflineTaskORM.id.notin_(subquery)).order_by(
            OfflineTaskORM.start_date)
        count_stmt = select(func.count()).select_from(final_stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        paginated_stmt = final_stmt.offset(skip).limit(limit)
        result = await session.execute(paginated_stmt)
        tasks_orm = result.scalars().all()

        tasks = [
            OfflineTask(id=t.id, region=t.region, start_date=t.start_date, end_date=t.end_date,
                        reward=t.reward, title=t.title,
                        description=t.description, location=t.location, contacts=t.contacts,
                        is_for_members=t.is_for_members)
            for t in tasks_orm
        ]
        return tasks, total

    async def get_task_by_id(self, task_id: int) -> OfflineTask | None:
        session = self.__uow.get_session()
        stmt = select(OfflineTaskORM).where(OfflineTaskORM.id == task_id)
        orm = await session.scalar(stmt)
        if not orm: return None
        return OfflineTask(id=orm.id, region=orm.region, start_date=orm.start_date,
                           end_date=orm.end_date, reward=orm.reward,
                           title=orm.title, description=orm.description, location=orm.location,
                           contacts=orm.contacts,
                           is_for_members=orm.is_for_members)

    async def create_task(self, task: OfflineTask) -> OfflineTask:
        session = self.__uow.get_session()
        orm = OfflineTaskORM(**{k: v for k, v in vars(task).items() if k != 'id'})
        session.add(orm)
        await session.flush()
        task.id = orm.id
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
                         (await session.execute(select(OfflineTaskORM))).scalars().all()}
        tasks = []
        for aorm in aorms:
            task_orm = tasks_orm_map.get(aorm.task_id)
            if task_orm:
                tasks.append(AcceptedOfflineTask(
                    user_id=user_id, user_source=user_source,
                    task=OfflineTask(id=task_orm.id, region=task_orm.region,
                                     start_date=task_orm.start_date, end_date=task_orm.end_date,
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

    async def get_in_progress_for_task(self, task_id: int, skip: int, limit: int) -> tuple[
        list[AcceptedOfflineTask], int]:
        session = self.__uow.get_session()
        base_stmt = select(AcceptedOfflineTaskORM).where(
            AcceptedOfflineTaskORM.task_id == task_id,
            AcceptedOfflineTaskORM.status == TaskStatus.IN_PROGRESS
        )
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        result = await session.execute(base_stmt.offset(skip).limit(limit))
        aorms = result.scalars().all()
        tasks = []
        for a in aorms:
            user_orm = await session.scalar(
                select(UserORM).where(UserORM.id == a.user_id, UserORM.source == a.user_source))
            if user_orm:
                u = await user_orm.to_domain()
                tasks.append(AcceptedOfflineTask(user_id=u.id, user_source=u.source, task=None,
                                                 status=a.status))
        return tasks, total

    async def create_accepted_offline_task(self, accepted: AcceptedOfflineTask) -> None:
        session = self.__uow.get_session()
        orm = AcceptedOfflineTaskORM(
            user_id=accepted.user_id, user_source=accepted.user_source,
            task_id=accepted.task.id, status=accepted.status
        )
        session.add(orm)
        await session.flush()
        logger.info(f"Created accepted offline task {accepted.task.id} for user {accepted.user_id}")

    async def get_in_progress_users_for_task(self, task_id: int, skip: int, limit: int) -> tuple[
        list[AcceptedOfflineTask], int]:
        session = self.__uow.get_session()
        # Подсчёт
        count_stmt = select(func.count()).select_from(AcceptedOfflineTaskORM).where(
            AcceptedOfflineTaskORM.task_id == task_id,
            AcceptedOfflineTaskORM.status == TaskStatus.IN_PROGRESS
        )
        total = await session.scalar(count_stmt) or 0

        # Выборка записей
        stmt = select(AcceptedOfflineTaskORM).where(
            AcceptedOfflineTaskORM.task_id == task_id,
            AcceptedOfflineTaskORM.status == TaskStatus.IN_PROGRESS
        ).offset(skip).limit(limit)
        result = await session.execute(stmt)
        aorms = result.scalars().all()

        if not aorms:
            return [], total

        # Оптимизированная загрузка задач и пользователей (избегаем N+1)
        task_orms = {t.id: t for t in
                     (await session.execute(select(OfflineTaskORM))).scalars().all()}

        user_keys = {(a.user_id, a.user_source) for a in aorms}
        users_map = {}
        for uid, usrc in user_keys:
            u_orm = await session.scalar(
                select(UserORM).where(UserORM.id == uid, UserORM.source == usrc))
            if u_orm:
                users_map[(uid, usrc)] = await u_orm.to_domain()

        accepted_tasks = []
        for aorm in aorms:
            task_orm = task_orms.get(aorm.task_id)
            user = users_map.get((aorm.user_id, aorm.user_source))
            if task_orm and user:
                accepted_tasks.append(AcceptedOfflineTask(
                    user_id=user.id, user_source=user.source,
                    task=OfflineTask(
                        id=task_orm.id, region=task_orm.region, start_date=task_orm.start_date,
                        end_date=task_orm.end_date,
                        reward=task_orm.reward, title=task_orm.title,
                        description=task_orm.description, location=task_orm.location,
                        contacts=task_orm.contacts
                    ),
                    status=aorm.status
                ))
        return accepted_tasks, total

    async def add_accepted_offline_task(self, accepted: AcceptedOfflineTask) -> None:
        session = self.__uow.get_session()
        orm = AcceptedOfflineTaskORM(
            user_id=accepted.user_id, user_source=accepted.user_source,
            task_id=accepted.task.id, status=accepted.status
        )
        session.add(orm)
        await session.flush()
    
    async def update_online_task_status(self, user_id: int, user_source: Sources, task_id: int, status: TaskStatus) -> None:
        session = self.__uow.get_session()
        stmt = select(AcceptedOnlineTaskORM).where(
            AcceptedOnlineTaskORM.user_id == user_id,
            AcceptedOnlineTaskORM.user_source == user_source,
            AcceptedOnlineTaskORM.task_id == task_id
        ).order_by(AcceptedOnlineTaskORM.id.desc()).limit(1)
        orm = await session.scalar(stmt)
        if orm:
            orm.status = status
            logger.info(f"Updated online task {task_id} status to {status.value}")
        else:
            logger.warning(f"Tried to update status for non-existing online accepted task {task_id}")
