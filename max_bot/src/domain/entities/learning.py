from dataclasses import dataclass
from datetime import datetime
from .user import Sources


@dataclass
class LearningTestAttempt:
    user_id: int
    user_source: Sources
    score: int
    passed_at: datetime
    is_passed: bool
