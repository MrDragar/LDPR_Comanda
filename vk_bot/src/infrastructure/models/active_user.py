from sqlalchemy import Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SQLEnum
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class ActiveUserORM(Base):
    __tablename__ = "active_users"
    user_id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), primary_key=True)

    __table_args__ = (
        Index('idx_active_users_pk', 'user_id', 'user_source', unique=True),
    )
