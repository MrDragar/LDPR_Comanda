import logging
from datetime import date, time
from src.domain.entities import ClosedEvent, EventRegistration, Sources
from src.domain.interfaces import IUnitOfWork, IClosedEventRepository, IEventRegistrationRepository, IUserRepository
from src.services.interfaces import IClosedEventService
from src.domain.exceptions import DomainError

logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 5


class ClosedEventService(IClosedEventService):
    def __init__(self, uow: IUnitOfWork, event_repo: IClosedEventRepository, 
                 reg_repo: IEventRegistrationRepository, user_repo: IUserRepository):
        self.__uow = uow
        self.__event_repo = event_repo
        self.__reg_repo = reg_repo
        self.__user_repo = user_repo

    async def create_event(self, title: str, desc: str, loc: str, d: date, t: time, region: str) -> ClosedEvent:
        if not region: raise DomainError("Регион обязателен")
        async with self.__uow.atomic():
            ev = ClosedEvent(id=0, region=region, title=title, description=desc, location=loc, date=d, time=t)
            return await self.__event_repo.create(ev)

    async def list_events(self, region: str | None, page: int) -> tuple[list[ClosedEvent], int]:
        if page < 1: raise DomainError("Страница >= 1")
        async with self.__uow.atomic():
            return await self.__event_repo.get_active_by_region(region, (page-1)*ITEMS_PER_PAGE, ITEMS_PER_PAGE)

    async def register(self, user_id: int, source: Sources, event_id: int) -> None:
        async with self.__uow.atomic():
            ev = await self.__event_repo.get_by_id(event_id)
            if not ev: raise DomainError("Мероприятие не найдено")
            if await self.__reg_repo.is_registered(user_id, source, event_id):
                raise DomainError("Вы уже записаны на это мероприятие")
            await self.__reg_repo.register_user(user_id, source, event_id)

    async def list_participants(self, event_id: int, page: int) -> tuple[list[EventRegistration], int]:
        if page < 1: raise DomainError("Страница >= 1")
        async with self.__uow.atomic():
            return await self.__reg_repo.get_participants(event_id, (page-1)*ITEMS_PER_PAGE, ITEMS_PER_PAGE)
    
    async def get_event(self, event_id: int) -> ClosedEvent | None:
        async with self.__uow.atomic():
            return await self.__event_repo.get_by_id(event_id)
    
    async def get_user_events(self, user_id: int, source: Sources) -> list[ClosedEvent]:
        async with self.__uow.atomic():
            return await self.__event_repo.get_user_events(user_id, source)
    