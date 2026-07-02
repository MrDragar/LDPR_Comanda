from datetime import datetime, UTC
from sqlalchemy import DateTime, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class LearningTestAttemptORM(Base):
    __tablename__ = "learning_attempts"
    user_id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), primary_key=True)
    score: Mapped[int] = mapped_column(nullable=False)
    passed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    is_passed: Mapped[bool] = mapped_column(nullable=False, default=False)
