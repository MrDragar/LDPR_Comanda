from datetime import datetime, UTC
from sqlalchemy import DateTime, Enum as SQLEnum, BigInteger, Index
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class HillVoteORM(Base):
    __tablename__ = "hill_votes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    petition_left_id: Mapped[int] = mapped_column(nullable=False)
    petition_right_id: Mapped[int] = mapped_column(nullable=False)
    winner_id: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index('idx_hill_user', 'user_id', 'user_source'),
    )
