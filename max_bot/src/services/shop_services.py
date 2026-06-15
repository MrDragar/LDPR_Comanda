import logging
import uuid

from src.domain.entities import Product, Order, Sources, OrderStatus
from src.domain.interfaces import IUnitOfWork, IProductRepository, IOrderRepository, IS3Storage
from src.services.interfaces import IProductService, IOrderService, IBalanceService, IUserService, \
    INotificationService
from src.domain.exceptions import DomainError

logger = logging.getLogger(__name__)
ITEMS_PER_PAGE = 4


class ProductService(IProductService):
    def __init__(self, uow: IUnitOfWork, repo: IProductRepository, s3_storage: IS3Storage):
        self.__uow = uow
        self.__repo = repo
        self.__s3_storage = s3_storage

    async def list_products(self, page: int) -> tuple[list[Product], int]:
        if page < 1: raise DomainError("Страница >= 1")
        async with self.__uow.atomic():
            prods, total = await self.__repo.get_active_products((page - 1) * ITEMS_PER_PAGE,
                                                                 ITEMS_PER_PAGE)
            return prods, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    async def create_product(self, name: str, desc: str, price: int, qty: int,
                             photo_bytes: bytes) -> Product:
        if price <= 0 or qty <= 0: raise DomainError("Цена и количество должны быть > 0")

        # Логика загрузки в S3 внутри сервиса
        filename = f"products/{uuid.uuid4().hex}.jpg"
        try:
            image_url = await self.__s3_storage.upload_photo(photo_bytes, filename)
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise DomainError("Ошибка загрузки изображения")

        async with self.__uow.atomic():
            p = Product(id=0, name=name, description=desc, price=price, quantity=qty,
                        image_url=image_url)
            return await self.__repo.create(p)

    async def hide_product(self, product_id: int) -> None:
        async with self.__uow.atomic():
            await self.__repo.toggle_active(product_id, False)

    async def get_product(self, product_id: int) -> Product | None:
        async with self.__uow.atomic():
            return await self.__repo.get_by_id(product_id)


class OrderService(IOrderService):
    def __init__(self, uow: IUnitOfWork, repo: IOrderRepository, prod_repo: IProductRepository,
                 balance_svc: IBalanceService, user_svc: IUserService,
                 notif_svc: INotificationService):
        self.__uow = uow;
        self.__repo = repo;
        self.__prod_repo = prod_repo
        self.__balance = balance_svc;
        self.__user_svc = user_svc;
        self.__notif = notif_svc

    async def create_order(self, user_id: int, source: Sources, product_id: int, delivery_type: str,
                           address: str | None, fio: str | None) -> Order:
        async with self.__uow.atomic():
            p = await self.__prod_repo.get_by_id(product_id)
            if not p or not p.is_active: raise DomainError("Товар недоступен")
            if p.quantity < 1: raise DomainError("Товар закончился")
            
            if await self.__repo.has_user_ordered_product(user_id, source, product_id):
                raise DomainError("Вы уже заказывали этот товар. Повторный заказ каждого товара возможен только 1 раз.")
            
            balance = await self.__balance.get_balance(user_id, source)
            if balance < p.price: raise DomainError("Недостаточно баллов")

            await self.__balance.deduct_balance(user_id, source, p.price, f"Покупка {p.name}")
            await self.__prod_repo.update_quantity(product_id, p.quantity - 1)

            order = Order(id=0, user_id=user_id, user_source=source, product_id=product_id,
                          product_name=p.name, price=p.price, delivery_type=delivery_type,
                          delivery_address=address, delivery_fio=fio)
            order = await self.__repo.create(order)
            logger.info(f"Order {order.id} created for user {user_id}")
            return order

    async def get_user_orders(self, user_id: int, source: Sources, page: int) -> tuple[
        list[Order], int]:
        if page < 1: raise DomainError("Страница >= 1")
        async with self.__uow.atomic():
            return await self.__repo.get_pending_by_user(user_id, source,
                                                         (page - 1) * ITEMS_PER_PAGE,
                                                         ITEMS_PER_PAGE)

    async def get_admin_orders(self, admin_region: str | None, page: int) -> tuple[
        list[Order], int]:
        if page < 1: raise DomainError("Страница >= 1")
        async with self.__uow.atomic():
            orders, total = await self.__repo.get_pending_by_admin(admin_region,
                                                                   (page - 1) * ITEMS_PER_PAGE,
                                                                   ITEMS_PER_PAGE)
            return orders, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    async def update_order_status(self, order_id: int, new_status: OrderStatus,
                                  reason: str | None = None) -> Order:
        async with self.__uow.atomic():
            order = await self.__repo.get_by_id(order_id)
            if not order or order.status != OrderStatus.PENDING: raise DomainError(
                "Заказ не в статусе ожидания")

            order = await self.__repo.update_status(order_id, new_status, reason)
            if new_status == OrderStatus.CANCELLED:
                await self.__balance.add_balance(order.user_id, order.user_source, order.price,
                                                 f"Возврат за отмену заказа #{order_id}")
                msg = f"Заказ #{order_id} отменен. Причина: {reason or 'Не указана'}\nБаллы ({order.price}) возвращены на баланс."
                await self.__notif.notify_user(order.user_id, order.user_source, msg)
            else:
                msg = f"Заказ #{order_id} подтвержден!"
                if order.delivery_type == "mail":
                    msg += f"\nПосылка отправлена. Адрес: {order.delivery_address or ''}, ФИО: {order.delivery_fio or ''}"
                await self.__notif.notify_user(order.user_id, order.user_source, msg)
            return order
    
    async def get_user_orders_history(self, user_id: int, source: Sources) -> list[Order]:
        async with self.__uow.atomic():
            return await self.__repo.get_all_by_user(user_id, source)
