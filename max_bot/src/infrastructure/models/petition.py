from datetime import datetime, UTC
from sqlalchemy import DateTime, Enum as SQLEnum, Index, String, Text, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.petition import PetitionStatus, PetitionScope
from src.domain.entities.user import Sources
from src.infrastructure.database import Base

class PetitionORM(Base):
    __tablename__ = "petitions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[PetitionScope] = mapped_column(SQLEnum(PetitionScope), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    author_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    author_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    support_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[PetitionStatus] = mapped_column(SQLEnum(PetitionStatus), default=PetitionStatus.MODERATION)
    candidate_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_progress: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_result_image: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class PetitionSupportORM(Base):
    __tablename__ = "petition_supports"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    petition_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    __table_args__ = (
        Index('idx_petition_support_unique', 'petition_id', 'user_id', 'user_source', unique=True),
    )

class PetitionSkipORM(Base):
    __tablename__ = "petition_skips"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    petition_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    __table_args__ = (
        Index('idx_petition_skip_unique', 'petition_id', 'user_id', 'user_source', unique=True),
    )