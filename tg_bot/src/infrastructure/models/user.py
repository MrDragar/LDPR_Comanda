from datetime import date, datetime, UTC
from sqlalchemy import Date, DateTime, Enum as SQLEnum, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.user import User, Sources, UserRole, UserGrade
from src.infrastructure.database import Base


class UserORM(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column("id", BigInteger(), primary_key=True)
    source: Mapped[Sources] = mapped_column(SQLEnum(Sources), name="source", primary_key=True)
    is_member: Mapped[bool] = mapped_column("is_member", nullable=True)
    username: Mapped[str] = mapped_column("username", String(255), nullable=True)
    surname: Mapped[str] = mapped_column("surname", String(255), nullable=False)
    name: Mapped[str] = mapped_column("name", String(255), nullable=True)
    patronymic: Mapped[str] = mapped_column("patronymic", String(255), nullable=True)
    birth_date: Mapped[date] = mapped_column("birth_date", Date, nullable=True)
    phone_number: Mapped[str] = mapped_column("phone_number", String(50), nullable=False)
    region: Mapped[str] = mapped_column("region", String(255), nullable=True)
    email: Mapped[str] = mapped_column("email", String(255), nullable=True)
    gender: Mapped[str] = mapped_column("gender", String(50), nullable=True)
    city: Mapped[str] = mapped_column("city", String(255), nullable=True)
    wish_to_join: Mapped[bool] = mapped_column("wish_to_join", nullable=True)
    home_address: Mapped[str] = mapped_column("home_address", String(512), nullable=True)
    news_subscription: Mapped[bool] = mapped_column("news_subscription", nullable=False)
    balance: Mapped[int] = mapped_column("balance", nullable=False, default=0)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    grade: Mapped[UserGrade] = mapped_column(SQLEnum(UserGrade), nullable=False, default=UserGrade.SYMPATHIZER)
    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    async def to_domain(self) -> User:
        return User(
            id=self.id, source=self.source, is_member=self.is_member, username=self.username,
            surname=self.surname, name=self.name, patronymic=self.patronymic,
            birth_date=self.birth_date, phone_number=self.phone_number, region=self.region,
            email=self.email, gender=self.gender, city=self.city, wish_to_join=self.wish_to_join,
            home_address=self.home_address, news_subscription=self.news_subscription,
            balance=self.balance, role=self.role, grade=self.grade, created_at=self.created_at
        )

    @classmethod
    async def from_domain(cls, user: User) -> 'UserORM':
        return cls(
            id=user.id, source=user.source, is_member=user.is_member, username=user.username,
            surname=user.surname, name=user.name, patronymic=user.patronymic,
            birth_date=user.birth_date, phone_number=user.phone_number, region=user.region,
            email=user.email, gender=user.gender, city=user.city, wish_to_join=user.wish_to_join,
            home_address=user.home_address, news_subscription=user.news_subscription,
            balance=user.balance, role=user.role, grade=user.grade, created_at=user.created_at
        )