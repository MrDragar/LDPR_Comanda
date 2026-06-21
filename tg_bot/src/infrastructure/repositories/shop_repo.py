import logging
from sqlalchemy import select, func
from src.domain.entities import Product, Order, Sources, OrderStatus
from src.domain.interfaces import IProductRepository, IOrderRepository
from src.infrastructure.interfaces import IDatabaseUnitOfWork
from src.infrastructure.models.shop import ProductORM, OrderORM
from src.infrastructure.models.user import UserORM

logger = logging.getLogger(__name__)


class ProductRepository(IProductRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def get_active_products(self, skip: int, limit: int) -> tuple[list[Product], int]:
        session = self.__uow.get_session()
        base = select(ProductORM).where(ProductORM.is_active == True, ProductORM.quantity > 0)
        total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await session.execute(base.offset(skip).limit(limit))
        return [Product(id=p.id, name=p.name, description=p.description, price=p.price,
                        quantity=p.quantity, image_url=p.image_url, is_active=p.is_active) for p in
                result.scalars().all()], total

    async def get_by_id(self, product_id: int) -> Product | None:
        session = self.__uow.get_session()
        p = await session.get(ProductORM, product_id)
        if not p: return None
        return Product(id=p.id, name=p.name, description=p.description, price=p.price,
                       quantity=p.quantity, image_url=p.image_url, is_active=p.is_active)

    async def create(self, product: Product) -> Product:
        session = self.__uow.get_session()
        orm = ProductORM(**{k: v for k, v in vars(product).items() if k != 'id'})
        session.add(orm)
        await session.flush()
        product.id = orm.id
        return product

    async def update_quantity(self, product_id: int, new_quantity: int) -> None:
        session = self.__uow.get_session()
        p = await session.get(ProductORM, product_id)
        if p: p.quantity = new_quantity

    async def toggle_active(self, product_id: int, is_active: bool) -> None:
        session = self.__uow.get_session()
        p = await session.get(ProductORM, product_id)
        if p: p.is_active = is_active


class OrderRepository(IOrderRepository):
    def __init__(self, uow: IDatabaseUnitOfWork):
        self.__uow = uow

    async def create(self, order: Order) -> Order:
        session = self.__uow.get_session()
        orm = OrderORM(**{k: v for k, v in vars(order).items() if k not in ('id', 'created_at')})
        session.add(orm)
        await session.flush()
        order.id = orm.id
        return order

    async def get_pending_by_user(self, user_id: int, user_source: Sources, skip: int,
                                  limit: int) -> tuple[list[Order], int]:
        session = self.__uow.get_session()
        base = select(OrderORM).where(OrderORM.user_id == user_id,
                                      OrderORM.user_source == user_source,
                                      OrderORM.status == OrderStatus.PENDING)
        total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
        result = await session.execute(base.offset(skip).limit(limit))
        return [self._orm_to_domain(o) for o in result.scalars().all()], total

    async def get_pending_by_admin(self, admin_region: str | None, skip: int, limit: int) -> tuple[
        list[Order], int]:
        session = self.__uow.get_session()
        stmt = select(OrderORM, UserORM).join(UserORM, (OrderORM.user_id == UserORM.id) & (
                    OrderORM.user_source == UserORM.source)).where(
            OrderORM.status == OrderStatus.PENDING)
        if admin_region:
            stmt = stmt.where(UserORM.region == admin_region)

        # Подсчет с фильтрацией
        subq = stmt.subquery()
        total = await session.scalar(select(func.count()).select_from(subq)) or 0

        paginated = stmt.offset(skip).limit(limit)
        result = await session.execute(paginated)
        orders = []
        for o_row, u_row in result.all():
            order = self._orm_to_domain(o_row)
            order.user_region = u_row.region  # Временно для админки, если нужно
            orders.append(order)
        return orders, total

    async def update_status(self, order_id: int, status: OrderStatus,
                            reason: str | None = None) -> Order:
        session = self.__uow.get_session()
        o = await session.get(OrderORM, order_id)
        if o:
            o.status = status
            o.cancel_reason = reason
            await session.flush()
            return self._orm_to_domain(o)
        raise ValueError("Order not found")

    async def get_by_id(self, order_id: int) -> Order | None:
        session = self.__uow.get_session()
        o = await session.get(OrderORM, order_id)
        return self._orm_to_domain(o) if o else None
    
    async def has_user_ordered_product(self, user_id: int, user_source: Sources, product_id: int) -> bool:
        session = self.__uow.get_session()
        stmt = select(func.count()).select_from(OrderORM).where(
            OrderORM.user_id == user_id,
            OrderORM.user_source == user_source,
            OrderORM.product_id == product_id, OrderORM.status != OrderStatus.CANCELLED
        )
        return (await session.scalar(stmt) or 0) > 0

    async def get_all_by_user(self, user_id: int, user_source: Sources) -> list[Order]:
        session = self.__uow.get_session()
        stmt = select(OrderORM).where(
            OrderORM.user_id == user_id,
            OrderORM.user_source == user_source
        ).order_by(OrderORM.created_at.desc())
        result = await session.execute(stmt)
        return [self._orm_to_domain(o) for o in result.scalars().all()]
    
    @staticmethod
    def _orm_to_domain(orm: OrderORM) -> Order:
        return Order(id=orm.id, user_id=orm.user_id, user_source=orm.user_source,
                     product_id=orm.product_id,
                     product_name=orm.product_name, price=orm.price,
                     delivery_type=orm.delivery_type,
                     delivery_address=orm.delivery_address, delivery_fio=orm.delivery_fio,
                     cancel_reason=orm.cancel_reason, status=orm.status, created_at=orm.created_at)
