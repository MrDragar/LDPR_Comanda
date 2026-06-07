from datetime import datetime, UTC
from sqlalchemy import DateTime, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column
from src.domain.entities.shop import OrderStatus
from src.domain.entities.user import Sources
from src.infrastructure.database import Base


class ProductORM(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    image_url: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class OrderORM(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    user_source: Mapped[Sources] = mapped_column(SQLEnum(Sources), nullable=False)
    product_id: Mapped[int] = mapped_column(nullable=False)
    product_name: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)
    delivery_type: Mapped[str] = mapped_column(nullable=False)
    delivery_address: Mapped[str] = mapped_column(nullable=True)
    delivery_fio: Mapped[str] = mapped_column(nullable=True)
    cancel_reason: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    __table_args__ = (Index("idx_orders_status", "status"),)
