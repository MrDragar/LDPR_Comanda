import enum
from dataclasses import dataclass, field
from datetime import date, datetime


class Sources(enum.Enum):
    VK = 'vk'
    TG = 'tg'
    MAX = 'max'


class UserRole(enum.Enum):
    STAFF_CA = "Сотрудник ЦА"
    COORDINATOR_RO = "Координатор РО"
    STAFF_RO = "Сотрудник РО"
    HEADLINER = "Хедлайнер"
    CANDIDATE = "Кандидат"
    USER = "Пользователь"


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
    name: str | None = None
    is_member: bool | None = None
    patronymic: str | None = None
    birth_date: date | None = None
    region: str | None = None
    email: str | None = None
    gender: str | None = None
    city: str | None = None
    wish_to_join: bool | None = None
    home_address: str | None = None
    news_subscription: bool = field(default=False)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    balance: int = field(default=0)
    role: UserRole = field(default=UserRole.USER)
    grade: UserGrade = field(default=UserGrade.SYMPATHIZER)