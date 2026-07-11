from dataclasses import dataclass, field
from datetime import datetime
from .user import Sources

@dataclass
class HillVote:
    id: int
    user_id: int
    user_source: Sources
    petition_left_id: int
    petition_right_id: int
    winner_id: int
    created_at: datetime = field(default_factory=lambda: datetime.now())