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
    is_member: bool
    username: str | None
    surname: str
    name: str
    patronymic: str
    birth_date: date
    phone_number: str
    region: str
    email: str
    gender: str
    city: str
    wish_to_join: bool
    home_address: str | None
    news_subscription: bool = field(default=False)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    balance: int = field(default=0)
    role: UserRole = field(default=UserRole.USER)
    grade: UserGrade = field(default=UserGrade.SYMPATHIZER)
