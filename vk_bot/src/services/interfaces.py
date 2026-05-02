from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities.user import User


class IUserService(ABC):
    @abstractmethod
    async def create_user(
            self, user_id: int, username: str | None,
            surname: str, name: str, is_member: bool,
            patronymic: str | None, birth_date: date,
            phone_number: str, region: str, email: str,
            gender: str, city: str, wish_to_join: bool, home_address: str | None,
            news_subscription: bool
    ) -> User:
        ...

    @abstractmethod
    async def is_user_exists(self, user_id: int) -> bool:
        ...

    @abstractmethod
    async def validate_phone(self, phone_number: str) -> str:
        ...

    @abstractmethod
    async def validate_email(self, email: str) -> str:
        ...

    @abstractmethod
    async def validate_fio_part(self, part: str, part_name: str) -> str:
        ...
    
    @abstractmethod
    async def get_similar_regions(self, region: str) -> list[str]:
        ...

    @abstractmethod
    async def get_region_address(self, region: str) -> str:
        ...

    @abstractmethod
    async def get_user_region(self, user_id: int) -> str:
        ...

    @abstractmethod
    async def get_all_users(self) -> list[User]:
        ...

    @abstractmethod
    async def update_news_subscription(
            self, user_id: int, news_subscription: bool
    ) -> User:
        ...

    @abstractmethod
    async def get_region_by_prefix(self, region_prefix: str) -> str:
        ...
