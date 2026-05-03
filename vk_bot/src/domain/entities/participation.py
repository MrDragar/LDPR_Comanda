from dataclasses import dataclass
from .user import Sources


@dataclass
class Participation:
    id: int
    user_id: int
    user_source: Sources
