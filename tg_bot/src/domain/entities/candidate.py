from dataclasses import dataclass, field
from datetime import datetime
from .user import Sources


@dataclass
class Candidate:
    id: int
    user_id: int
    source: Sources
    fio: str
    region: str
    photo_url: str | None = None
    bio: str | None = None
    topics: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class CandidateQuestion:
    id: int
    candidate_id: int
    author_id: int
    author_source: Sources
    text: str
    is_anonymous: bool = False
    answer_text: str | None = None
    answer_voice_url: str | None = None
    answer_video_url: str | None = None
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now())
