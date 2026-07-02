from datetime import datetime, UTC
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKeyConstraint, Index, String, Text, \
    BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.headliner import Headliner, HeadlinerFollower
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class HeadlinerORM(Base):
    __tablename__ = "headliners"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    fio: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    group_link: Mapped[str] = mapped_column(String(512), nullable=False)
    photo: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC)
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id', 'user_source'],
            ['users.id', 'users.source'],
            ondelete="CASCADE"
        ),
        Index('idx_headliner_user_unique', 'user_id', 'user_source', unique=True),
    )

    async def to_domain(self) -> Headliner:
        return Headliner(
            id=self.id,
            user_id=self.user_id,
            user_source=self.user_source,
            fio=self.fio,
            position=self.position,
            topic=self.topic,
            group_link=self.group_link,
            photo=self.photo,
            welcome_message=self.welcome_message,
            created_at=self.created_at
        )

    @classmethod
    async def from_domain(cls, headliner: Headliner) -> 'HeadlinerORM':
        return cls(
            id=headliner.id,
            user_id=headliner.user_id,
            user_source=headliner.user_source,
            fio=headliner.fio,
            position=headliner.position,
            topic=headliner.topic,
            group_link=headliner.group_link,
            photo=headliner.photo,
            welcome_message=headliner.welcome_message,
            created_at=headliner.created_at
        )


class HeadlinerFollowerORM(Base):
    __tablename__ = "headliner_followers"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    headliner_id: Mapped[int] = mapped_column(nullable=False)
    follower_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    follower_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC)
    )
    __table_args__ = (
        ForeignKeyConstraint(['headliner_id'], ['headliners.id'], ondelete="CASCADE"),
        Index('idx_headliner_follower_unique', 'follower_id', 'follower_source', unique=True),
        Index('idx_headliner_followers_headliner', 'headliner_id'),
    )

    async def to_domain(self) -> HeadlinerFollower:
        return HeadlinerFollower(
            id=self.id,
            headliner_id=self.headliner_id,
            follower_id=self.follower_id,
            follower_source=self.follower_source,
            created_at=self.created_at
        )
