from datetime import date, time as py_time, UTC
from sqlalchemy import Date, Time, ForeignKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class ClosedEventORM(Base):
    __tablename__ = "closed_events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    location: Mapped[str] = mapped_column(nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[py_time] = mapped_column(Time, nullable=False)


class EventRegistrationORM(Base):
    __tablename__ = "event_registrations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    user_source: Mapped[Sources] = mapped_column(nullable=False)
    event_id: Mapped[int] = mapped_column(nullable=False)
    __table_args__ = (
        Index('idx_event_reg_unique', 'user_id', 'user_source', 'event_id', unique=True),
        ForeignKeyConstraint(['event_id'], ['closed_events.id'], ondelete="CASCADE")
    )
