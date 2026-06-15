from dataclasses import dataclass
from datetime import date, time
from .user import Sources


@dataclass
class ClosedEvent:
    id: int
    region: str
    title: str
    description: str
    location: str
    date: date
    time: time


@dataclass
class EventRegistration:
    id: int
    user_id: int
    user_source: Sources
    event_id: int
