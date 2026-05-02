from abc import ABC, abstractmethod
from contextlib import _AsyncGeneratorContextManager

from .entities import User, Sources


class IUnitOfWork(ABC):
    @abstractmethod
    def atomic(self) -> _AsyncGeneratorContextManager[None, None]:
        ...


class IUserRepository(ABC):
    @abstractmethod
    async def create_user(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_user(self, user_id: int, source: Sources) -> User:
        ...

    @abstractmethod
    async def is_phone_number_existing(self, phone_number: str) -> bool:
        ...
    
    @abstractmethod
    async def is_email_existing(self, email: str) -> bool:
        ...

    @abstractmethod
    async def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> list[User]:
        ...

    @abstractmethod
    async def update_user_news_subscription(
            self, user_id: int, source: Sources, news_subscription: bool
    ) -> User:
        ...


class IStringSorterRepository(ABC):
    @abstractmethod
    async def sort_by_similarity(self, target: str, string_list: list[str]) -> list[str]:
        ...


class IParticipationRepository(ABC):
    @abstractmethod
    async def add(self, user_id: int, user_source: Sources) -> int:
        ...

    @abstractmethod
    async def is_participant(self, user_id: int, user_source: Sources) -> bool:
        ...

    @abstractmethod
    async def get_all_participation_ids(self, user_id: int, user_source: Sources) -> list[int]:
        ...


class IReferralRepository(ABC):
    @abstractmethod
    async def add(self, inviter_id: int, inviter_source: Sources, invitee_id: int, invitee_source: Sources) -> None:
        ...

    @abstractmethod
    async def is_invitee_exists(self, invitee_id: int, invitee_source: Sources) -> bool:
        ...

    @abstractmethod
    async def get_count_invitees(self, inviter_id: int, inviter_source: Sources) -> int:
        ...
