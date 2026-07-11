from datetime import datetime, UTC
from sqlalchemy import DateTime, Enum as SQLEnum, String, Text, BigInteger, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class CandidateORM(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    fio: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    social_links: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class CandidateQuestionORM(Base):
    __tablename__ = "candidate_questions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    author_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_voice_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    answer_video_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
