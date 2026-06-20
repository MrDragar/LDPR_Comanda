from maxapi import F, Router
from maxapi.context import MemoryContext
from maxapi.types import CallbackButton, MessageButton, MessageCallback, MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.states import ShopStates
from src.domain.entities.user import Sources
from src.domain.exceptions import DomainError
from src.services.interfaces import IBalanceService, INotificationService, IOrderService, IProductService, IUserService

router = Router()


def _uid(event) -> int:
    if hasattr(event, "from_user") and event.from_user:
        return event.from_user.user_id
    return event.callback.user.user_id


def _callback_keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*[CallbackButton(text=text, payload=payload) for text, payload in row])
    return builder


def _text_keyboard(buttons: list[str]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for button in buttons:
        builder.row(MessageButton(text=button))
    return builder


async def _main_menu(event, user_service: IUserService, user_id: int):
    role = await user_service.get_user_role(user_id, Sources.MAX)
    await event.message.answer("Главное меню", attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(F.message.body.text == "Магазин")
async def open_shop(event: MessageCreated, context: MemoryContext,
                    product_service: IProductService, balance_service: IBalanceService):
    balance = await balance_service.get_balance(_uid(event), Sources.MAX)
    products, total_pages = await product_service.list_products(1)
    if not products:
        return await event.message.answer("Магазин временно пуст.")
    await context.set_state(ShopStates.BROWSE)
    await context.update_data(page=1, total=total_pages)
    await render_shop(event, products, 1, total_pages, balance)


async def render_shop(event, products, page: int, total_pages: int, balance: int):
    rows = []
    for product in products:
        rows.append([(f"{product.name[:28]} - {product.price}б", f"max_shop_view:{product.id}")])
    nav = []
    if page > 1:
        nav.append(("Назад", f"max_shop_page:{page - 1}"))
    if page < total_pages:
        nav.append(("Вперёд", f"max_shop_page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("В меню", "max_shop_menu")])
    await event.message.answer(
        f"Ваш баланс: {balance} баллов.\n"
        f"Список доступных товаров (стр. {page}/{total_pages}):",
        attachments=[_callback_keyboard(rows).as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_shop_page:"))
async def shop_page(event: MessageCallback, context: MemoryContext,
                    product_service: IProductService, balance_service: IBalanceService):
    page = int(event.callback.payload.split(":", 1)[1])
    products, total_pages = await product_service.list_products(page)
    balance = await balance_service.get_balance(_uid(event), Sources.MAX)
    await context.update_data(page=page, total=total_pages)
    await event.ack()
    await render_shop(event, products, page, total_pages, balance)


@router.message_callback(F.callback.payload.startswith("max_shop_view:"))
async def view_product(event: MessageCallback, product_service: IProductService):
    product_id = int(event.callback.payload.split(":", 1)[1])
    product = await product_service.get_product(product_id)
    await event.ack()
    if not product:
        return await event.message.answer("Товар не найден.")
    keyboard = _callback_keyboard([
        [("Купить", f"max_shop_buy:{product.id}")],
        [("К списку", "max_shop_back")]
    ])
    text = (
        f"{product.name}\n"
        f"Цена: {product.price} баллов\n"
        f"Остаток: {product.quantity}\n"
        f"{product.description}"
    )
    if product.image_url:
        text += f"\n\nФото: {product.image_url}"
    await event.message.answer(text, attachments=[keyboard.as_markup()])


@router.message_callback(F.callback.payload == "max_shop_back")
async def back_shop_list(event: MessageCallback, context: MemoryContext,
                         product_service: IProductService, balance_service: IBalanceService):
    data = await context.get_data()
    page = data.get("page", 1)
    products, total_pages = await product_service.list_products(page)
    balance = await balance_service.get_balance(_uid(event), Sources.MAX)
    await event.ack()
    await render_shop(event, products, page, total_pages, balance)


@router.message_callback(F.callback.payload.startswith("max_shop_buy:"))
async def start_buy(event: MessageCallback, context: MemoryContext,
                    product_service: IProductService, balance_service: IBalanceService):
    product_id = int(event.callback.payload.split(":", 1)[1])
    product = await product_service.get_product(product_id)
    await event.ack()
    if not product:
        return await event.message.answer("Товар не найден.")
    balance = await balance_service.get_balance(_uid(event), Sources.MAX)
    if balance < product.price:
        return await event.message.answer("Вам не хватает баллов для покупки этого товара.")
    await context.update_data(product_id=product_id)
    await context.set_state(ShopStates.DELIVERY_CHOICE)
    await event.message.answer(
        "Как вы хотите получить товар?",
        attachments=[_text_keyboard(["По почте", "Заберу лично", "Отмена"]).as_markup()]
    )


@router.message_created(ShopStates.DELIVERY_CHOICE)
async def choose_delivery(event: MessageCreated, context: MemoryContext,
                          user_service: IUserService, order_service: IOrderService,
                          notification_service: INotificationService):
    text = (event.message.body.text or "").strip()
    if text == "Отмена":
        await context.clear()
        return await _main_menu(event, user_service, _uid(event))
    if text == "По почте":
        await context.set_state(ShopStates.MAIL_ADDR)
        return await event.message.answer(
            "Укажите адрес и индекс почтового отделения:",
            attachments=[_text_keyboard(["Отмена"]).as_markup()]
        )
    if text == "Заберу лично":
        data = await context.get_data()
        user = await user_service.get_user(_uid(event), Sources.MAX)
        address = await user_service.get_region_address(user.region)
        try:
            order = await order_service.create_order(
                _uid(event), Sources.MAX, data["product_id"], "pickup", address, None
            )
            await notification_service.notify_user(
                _uid(event), Sources.MAX,
                f"Заказ #{order.id} оформлен. Заберите товар по адресу: {address}"
            )
            await event.message.answer(f"Заказ #{order.id} оформлен. Адрес: {address}")
            await context.clear()
            return await _main_menu(event, user_service, _uid(event))
        except DomainError as e:
            return await event.message.answer(f"Ошибка: {e}")
    await event.message.answer("Выберите способ получения кнопкой.")


@router.message_created(ShopStates.MAIL_ADDR)
async def mail_addr(event: MessageCreated, context: MemoryContext):
    text = (event.message.body.text or "").strip()
    if text == "Отмена":
        await context.clear()
        return await event.message.answer("Оформление отменено.")
    await context.update_data(address=text)
    await context.set_state(ShopStates.MAIL_FIO)
    await event.message.answer(
        "Укажите ваше ФИО как в паспорте:",
        attachments=[_text_keyboard(["Отмена"]).as_markup()]
    )


@router.message_created(ShopStates.MAIL_FIO)
async def finalize_mail(event: MessageCreated, context: MemoryContext,
                        user_service: IUserService, order_service: IOrderService,
                        notification_service: INotificationService):
    text = (event.message.body.text or "").strip()
    if text == "Отмена":
        await context.clear()
        return await _main_menu(event, user_service, _uid(event))
    data = await context.get_data()
    try:
        order = await order_service.create_order(
            _uid(event),
            Sources.MAX,
            data["product_id"],
            "mail",
            data["address"],
            text
        )
        await notification_service.notify_user(
            _uid(event),
            Sources.MAX,
            f"Заказ #{order.id} оформлен."
        )
        await event.message.answer(f"Заказ #{order.id} оформлен.")
        await context.clear()
        await _main_menu(event, user_service, _uid(event))
    except DomainError as e:
        await event.message.answer(f"Ошибка: {e}")


@router.message_callback(F.callback.payload == "max_shop_menu")
async def shop_menu(event: MessageCallback, context: MemoryContext, user_service: IUserService):
    await event.ack()
    await context.clear()
    await _main_menu(event, user_service, _uid(event))
