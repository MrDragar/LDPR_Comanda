import logging
from datetime import date

from sqlalchemy import select, func
from src.domain.entities import ClosedEvent, EventRegistration, Sources
from src.domain.interfaces import IClosedEventRepository, IEventRegistrationRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.closed_event import ClosedEventORM, EventRegistrationORM

logger = logging.getLogger(__name__)


class ClosedEventRepository(IClosedEventRepository):
    async def get_user_events(self, user_id: int, user_source: Sources) -> list[ClosedEvent]:
        session = self.__uow.get_session()
        stmt = select(ClosedEventORM).join(
            EventRegistrationORM, EventRegistrationORM.event_id == ClosedEventORM.id
        ).where(
            EventRegistrationORM.user_id == user_id,
            EventRegistrationORM.user_source == user_source
        ).order_by(ClosedEventORM.date, ClosedEventORM.time)
        result = await session.execute(stmt)
        return [
            ClosedEvent(id=o.id, region=o.region, title=o.title, description=o.description,
                        location=o.location, date=o.date, time=o.time)
            for o in result.scalars().all()
        ]

    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def create(self, event: ClosedEvent) -> ClosedEvent:
        session = self.__uow.get_session()
        orm = ClosedEventORM(**{k: v for k, v in vars(event).items() if k != 'id'})
        session.add(orm)
        await session.flush()
        event.id = orm.id
        return event

    async def get_by_id(self, event_id: int) -> ClosedEvent | None:
        session = self.__uow.get_session()
        o = await session.get(ClosedEventORM, event_id)
        return ClosedEvent(id=o.id, region=o.region, title=o.title, description=o.description,
                           location=o.location, date=o.date, time=o.time) if o else None

    async def get_active_by_region(self, region: str | None, skip: int, limit: int) -> tuple[
        list[ClosedEvent], int]:
        session = self.__uow.get_session()
        current_date = date.today()
        stmt = select(ClosedEventORM).where(
            ClosedEventORM.date >= current_date
        ).order_by(ClosedEventORM.date, ClosedEventORM.time)
        if region:
            stmt = stmt.where(ClosedEventORM.region == region)

        count = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        result = await session.execute(stmt.offset(skip).limit(limit))
        return [
            ClosedEvent(id=o.id, region=o.region, title=o.title, description=o.description,
                        location=o.location, date=o.date, time=o.time) for o in
            result.scalars().all()
        ], count


class EventRegistrationRepository(IEventRegistrationRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def register_user(self, user_id: int, user_source: Sources,
                            event_id: int) -> EventRegistration:
        session = self.__uow.get_session()
        orm = EventRegistrationORM(user_id=user_id, user_source=user_source, event_id=event_id)
        session.add(orm)
        await session.flush()
        reg = EventRegistration(id=orm.id, user_id=user_id, user_source=user_source,
                                event_id=event_id)
        logger.info(f"User {user_id} registered for event {event_id}")
        return reg

    async def is_registered(self, user_id: int, user_source: Sources, event_id: int) -> bool:
        session = self.__uow.get_session()
        stmt = select(func.count()).select_from(EventRegistrationORM).where(
            EventRegistrationORM.user_id == user_id,
            EventRegistrationORM.user_source == user_source,
            EventRegistrationORM.event_id == event_id
        )
        return (await session.scalar(stmt) or 0) > 0

    async def get_participants(self, event_id: int, skip: int, limit: int) -> tuple[
        list[EventRegistration], int]:
        session = self.__uow.get_session()
        stmt = select(EventRegistrationORM).where(EventRegistrationORM.event_id == event_id)
        total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        result = await session.execute(stmt.offset(skip).limit(limit))
        return [
            EventRegistration(id=o.id, user_id=o.user_id, user_source=o.user_source,
                              event_id=o.event_id)
            for o in result.scalars().all()
        ], total
    
