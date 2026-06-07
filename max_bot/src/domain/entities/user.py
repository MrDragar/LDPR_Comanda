import enum
from dataclasses import dataclass, field
from datetime import date, datetime


class Sources(enum.Enum):
    VK = 'vk'
    TG = 'tg'
    MAX = 'max'


class UserRole(enum.Enum):
    STAFF_CA = "сотрудник ЦА"
    COORDINATOR_RO = "координатор РО"
    STAFF_RO = "сотрудник РО"
    # STAFF_MO = "сотрудник МО"
    # STAFF_PO = "сотрудник ПО"
    USER = "пользователь"


class UserGrade(enum.Enum):
    SYMPATHIZER = "Сторонник"
    BIG_TEAM_MEMBER = "Участник большой команды"
    AGITATOR = "Агитатор"
    RESERVE = "Кадровый резерв ЛДПР"


@dataclass
class User:
    id: int
    source: Sources
    username: str | None
    surname: str
    phone_number: str
    name: str | None = None  # nullable
    is_member: bool | None = None
    patronymic: str | None = None  # nullable
    birth_date: date | None = None  # nullable
    region: str | None = None  # nullable
    email: str | None = None  # nullable
    gender: str | None = None  # nullable
    city: str | None = None  # nullable
    wish_to_join: bool | None = None  # nullable
    home_address: str | None = None
    news_subscription: bool = field(default=False)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    balance: int = field(default=0)
    role: UserRole = field(default=UserRole.USER)
    grade: UserGrade = field(default=UserGrade.SYMPATHIZER)
