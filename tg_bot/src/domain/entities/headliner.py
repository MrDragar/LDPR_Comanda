from dataclasses import dataclass, field
from datetime import datetime

from .user import Sources


@dataclass
class Headliner:
    user_id: int
    user_source: Sources
    fio: str
    position: str
    topic: str
    group_link: str
    photo: str | None = None
    welcome_message: str | None = None
    id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class HeadlinerFollower:
    headliner_id: int
    follower_id: int
    follower_source: Sources
    id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now())
