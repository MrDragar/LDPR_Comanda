from sqlalchemy import ForeignKeyConstraint, Index, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class ParticipationORM(Base):
    __tablename__ = "participations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id', 'user_source'],
            ['users.id', 'users.source'],
            ondelete="CASCADE"
        ),
        Index('idx_participation_user', 'user_id', 'user_source')
    )
