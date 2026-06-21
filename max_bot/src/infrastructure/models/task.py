from datetime import date, datetime, UTC
from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.domain.entities.task import TaskType, TaskStatus
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class OnlineTaskORM(Base):
    __tablename__ = "online_tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration: Mapped[int] = mapped_column(nullable=False)
    type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType), nullable=False)
    reward: Mapped[int] = mapped_column(nullable=False)
    url: Mapped[str | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)


class OfflineTaskORM(Base):
    __tablename__ = "offline_tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reward: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    location: Mapped[str] = mapped_column(nullable=False)
    contacts: Mapped[str] = mapped_column(nullable=False)


class AcceptedOnlineTaskORM(Base):
    __tablename__ = "accepted_online_tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    task_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'user_source'], ['users.id', 'users.source'],
                             ondelete="CASCADE"),
        ForeignKeyConstraint(['task_id'], ['online_tasks.id'], ondelete="CASCADE"),
        Index('idx_accepted_online_pk', 'user_id', 'user_source', 'task_id', unique=False)
    )


class AcceptedOfflineTaskORM(Base):
    __tablename__ = "accepted_offline_tasks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    task_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'user_source'], ['users.id', 'users.source'],
                             ondelete="CASCADE"),
        ForeignKeyConstraint(['task_id'], ['offline_tasks.id'], ondelete="CASCADE"),
        Index('idx_accepted_offline_pk', 'user_id', 'user_source', 'task_id', unique=False)
    )


class TransactionORM(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,
                                                 default=lambda: datetime.now(UTC))

    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'user_source'], ['users.id', 'users.source'],
                             ondelete="CASCADE"),
    )
