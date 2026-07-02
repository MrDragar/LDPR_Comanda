from sqlalchemy import ForeignKeyConstraint, Index, Enum as SQLEnum, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class ReferralORM(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    inviter_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)

    # Не FK, но уникально (в связке с source)
    invitee_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    invitee_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['inviter_id', 'inviter_source'],
            ['users.id', 'users.source'],
            ondelete="CASCADE"
        ),
        Index('idx_referral_invitee_unique', 'invitee_id', 'invitee_source', unique=True),
        Index('idx_referral_inviter', 'inviter_id', 'inviter_source')
    )
