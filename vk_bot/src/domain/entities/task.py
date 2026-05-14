import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from .user import Sources


class TaskType(enum.Enum):
    REPOST = "repost"
    COMMENT = "comment"
    LIKE = "like"


class TaskStatus(enum.Enum):
    IN_PROGRESS = "in_progress"
    DECLINED = "declined"
    ACCEPTED = "accepted"


@dataclass
class OnlineTask:
    id: int
    date: date
    duration: int
    type: TaskType
    reward: int
    post_id: int
    group_id: int


@dataclass
class OfflineTask:
    id: int
    region: str
    date: date
    reward: int
    title: str
    description: str
    location: str
    contacts: str


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
    task: OfflineTask
    status: TaskStatus


@dataclass
class Transaction:
    id: int
    user_id: int
    user_source: Sources
    amount: int
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now())
