from dataclasses import dataclass
from .user import Sources


@dataclass
class Referral:
    id: int
    inviter_id: int
    inviter_source: Sources
    invitee_id: int
    invitee_source: Sources
