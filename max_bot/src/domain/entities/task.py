import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from .user import Sources


class TaskType(enum.Enum):
    REPOST = "репост"
    COMMENT = "комментарий"
    LIKE = "лайк"
    OTHER = "другое"


class TaskStatus(enum.Enum):
    IN_PROGRESS = "в процессе"
    DECLINED = "отклонено"
    ACCEPTED = "принято"


@dataclass
class OnlineTask:
    id: int
    date: date
    duration: int
    type: TaskType
    reward: int
    url: str | None
    title: str
    description: str 
    is_for_members: bool = False


@dataclass
class OfflineTask:
    id: int
    region: str
    start_date: date
    end_date: date
    reward: int
    title: str
    description: str
    location: str
    contacts: str
    is_for_members: bool = False


@dataclass
class AcceptedOnlineTask:
    user_id: int
    user_source: Sources
    task: OnlineTask
    status: TaskStatus


@dataclass
class AcceptedOfflineTask:
    user_id: int
    user_source: Sources
    task: OfflineTask | None
    status: TaskStatus


@dataclass
class Transaction:
    id: int
    user_id: int
    user_source: Sources
    amount: int
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now())
