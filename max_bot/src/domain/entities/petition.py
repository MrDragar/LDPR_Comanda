from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum

from src.domain.entities import Sources


class PetitionStatus(str, Enum):
    MODERATION = "moderation"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"

class PetitionScope(str, Enum):
    REGION = "region"
    FEDERAL = "federal"

@dataclass
class Petition:
    id: int
    title: str
    description: str
    region: str
    scope: PetitionScope
    image_url: str | None
    author_id: int
    author_source: Sources
    author_name: str
    support_count: int = 0
    share_count: int = 0
    view_count: int = 0
    status: PetitionStatus = PetitionStatus.MODERATION
    candidate_id: int | None = None
    candidate_name: str | None = None
    candidate_progress: str | None = None
    candidate_result: str | None = None
    candidate_result_image: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))