from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from src.domain.entities.user import Sources


class OrderStatus(Enum):
    PENDING = "ожидание"
    COMPLETED = "завершено"
    CANCELLED = "отклонено"


@dataclass
class Product:
    id: int
    name: str
    description: str
    price: int
    quantity: int
    image_url: str
    is_active: bool = True


@dataclass
class Order:
    id: int
    user_id: int
    user_source: Sources
    product_id: int
    product_name: str
    price: int
    delivery_type: str  # "mail" или "pickup"
    delivery_address: str | None
    delivery_fio: str | None
    cancel_reason: str | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now())
