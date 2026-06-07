from dataclasses import dataclass
from .user import Sources


@dataclass
class ActiveUser:
    user_id: int
    user_source: Sources
