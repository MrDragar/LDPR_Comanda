import re
from datetime import date, datetime

from maxapi import F, Router
from maxapi.context import MemoryContext
from maxapi.types import CallbackButton, MessageCallback, MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.states import AdminCAStates, AdminShopStates, AdminTaskStates, ClosedEventStates
from src.domain.entities import OrderStatus, Sources
from src.domain.entities.task import TaskStatus, TaskType
from src.domain.entities.user import UserRole
from src.services.interfaces import (
    IClosedEventService,
    INotificationService,
    IOfflineTaskService,
    IOnlineTaskService,
    IOrderService,
    IProductService,
    IUserService,
)

router = Router()
PAGE_LIMIT = 5
EMPTY_IMAGE = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14"
    b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?"
    b"\x00\xd2\xcf \xff\xd9"
)


def _uid(event) -> int:
    if hasattr(event, "from_user") and event.from_user:
        return event.from_user.user_id
    return event.callback.user.user_id


def _keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*[CallbackButton(text=text, payload=payload) for text, payload in row])
    return builder


def _fio_key(user) -> str:
    parts = [user.surname, user.name, user.patronymic]
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


def _profile_key(user) -> str:
    return f"{_fio_key(user)}|{user.phone_number}"


def _profile_title(users: list) -> str:
    main = users[0]
    platforms = ", ".join(sorted({user.source.value for user in users}))
    return f"{main.surname} {main.name} ({platforms})"


async def _load_profile_users(user_service: IUserService, phone: str, key: str | None = None) -> list:
    users = await user_service.search_users_by_phone(phone)
    if key:
        users = [user for user in users if _profile_key(user) == key]
    users.sort(key=lambda user: user.source.value)
    return users


async def _role(event, user_service: IUserService) -> UserRole:
    return await user_service.get_user_role(_uid(event), Sources.MAX)


async def _main_menu(event, user_service: IUserService):
    role = await _role(event, user_service)
    await event.message.answer("Главное меню", attachments=[get_role_menu_keyboard(role).as_markup()])


async def _check_role(event, user_service: IUserService, roles: list[UserRole]) -> bool:
    try:
        role = await _role(event, user_service)
    except Exception:
        await event.message.answer("Пользователь не найден.")
        return False
    if role not in roles:
        await event.message.answer("Недостаточно прав.")
        return False
    return True


@router.message_created(F.message.body.text == "Добавить товар")
async def start_add_product(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA]):
        return
    await context.set_state(AdminShopStates.ADD_NAME)
    await event.message.answer("Введите название товара:")


@router.message_created(AdminShopStates.ADD_NAME)
async def product_name(event: MessageCreated, context: MemoryContext):
    await context.update_data(name=(event.message.body.text or "").strip())
    await context.set_state(AdminShopStates.ADD_DESC)
    await event.message.answer("Введите описание товара:")


@router.message_created(AdminShopStates.ADD_DESC)
async def product_desc(event: MessageCreated, context: MemoryContext):
    await context.update_data(desc=(event.message.body.text or "").strip())
    await context.set_state(AdminShopStates.ADD_QTY)
    await event.message.answer("Введите количество:")


@router.message_created(AdminShopStates.ADD_QTY)
async def product_qty(event: MessageCreated, context: MemoryContext):
    try:
        qty = int((event.message.body.text or "").strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await event.message.answer("Введите число больше 0.")
        return
    await context.update_data(qty=qty)
    await context.set_state(AdminShopStates.ADD_PRICE)
    await event.message.answer("Введите цену в баллах:")


@router.message_created(AdminShopStates.ADD_PRICE)
async def product_price(event: MessageCreated, context: MemoryContext,
                        product_service: IProductService, user_service: IUserService):
    try:
        price = int((event.message.body.text or "").strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await event.message.answer("Введите число больше 0.")
        return
    data = await context.get_data()
    try:
        await product_service.create_product(
            name=data["name"],
            desc=data["desc"],
            price=price,
            qty=data["qty"],
            photo_bytes=EMPTY_IMAGE,
        )
        await event.message.answer("Товар добавлен.")
    except Exception as e:
        await event.message.answer(f"Не удалось добавить товар: {e}")
    await context.clear()
    await _main_menu(event, user_service)


@router.message_created(F.message.body.text == "Скрыть товар")
async def start_hide_product(event: MessageCreated, context: MemoryContext,
                             product_service: IProductService, user_service: IUserService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA]):
        return
    products, total = await product_service.list_products(1)
    if not products:
        await event.message.answer("Нет активных товаров.")
        return
    await context.set_state(AdminShopStates.HIDE_BROWSE)
    await render_hide_products(event, products, 1, total)


async def render_hide_products(event, products, page: int, total_pages: int):
    rows = [[(f"{item.name[:30]} ({item.quantity})", f"max_admin_hide:{item.id}")] for item in products]
    nav = []
    if page > 1:
        nav.append(("Назад", f"max_admin_hide_page:{page - 1}"))
    if page < total_pages:
        nav.append(("Вперёд", f"max_admin_hide_page:{page + 1}"))
    if nav:
        rows.append(nav)
    await event.message.answer("Выберите товар для скрытия:", attachments=[_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_admin_hide_page:"))
async def hide_product_page(event: MessageCallback, product_service: IProductService):
    page = int(event.callback.payload.split(":", 1)[1])
    products, total = await product_service.list_products(page)
    await render_hide_products(event, products, page, total)


@router.message_callback(F.callback.payload.startswith("max_admin_hide:"))
async def hide_product(event: MessageCallback, context: MemoryContext,
                       product_service: IProductService, user_service: IUserService):
    product_id = int(event.callback.payload.split(":", 1)[1])
    await product_service.hide_product(product_id)
    await event.message.answer("Товар скрыт.")
    await context.clear()
    await _main_menu(event, user_service)


@router.message_created(F.message.body.text == "Управление заказами")
async def orders(event: MessageCreated, user_service: IUserService, order_service: IOrderService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]):
        return
    user = await user_service.get_user(_uid(event), Sources.MAX)
    region = None if user.role == UserRole.STAFF_CA else user.region
    items, total = await order_service.get_admin_orders(region, 1)
    if not items:
        await event.message.answer("Нет заказов в ожидании.")
        return
    await render_orders(event, items, 1, total)


async def render_orders(event, orders_list, page: int, total_pages: int):
    rows = [[(f"#{item.id} {item.product_name[:24]}", f"max_order:{item.id}")] for item in orders_list]
    nav = []
    if page > 1:
        nav.append(("Назад", f"max_order_page:{page - 1}"))
    if page < total_pages:
        nav.append(("Вперёд", f"max_order_page:{page + 1}"))
    if nav:
        rows.append(nav)
    await event.message.answer(f"Заказы (стр. {page}/{total_pages}):", attachments=[_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_order_page:"))
async def order_page(event: MessageCallback, user_service: IUserService, order_service: IOrderService):
    page = int(event.callback.payload.split(":", 1)[1])
    user = await user_service.get_user(_uid(event), Sources.MAX)
    region = None if user.role == UserRole.STAFF_CA else user.region
    items, total = await order_service.get_admin_orders(region, page)
    await render_orders(event, items, page, total)


@router.message_callback(F.callback.payload.startswith("max_order:"))
async def order_view(event: MessageCallback, order_service: IOrderService):
    order_id = int(event.callback.payload.split(":", 1)[1])
    rows = [[("Подтвердить", f"max_order_done:{order_id}")], [("Отклонить", f"max_order_cancel:{order_id}")]]
    await event.message.answer(f"Заказ #{order_id}. Выберите действие:", attachments=[_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_order_done:"))
async def order_done(event: MessageCallback, order_service: IOrderService):
    order_id = int(event.callback.payload.split(":", 1)[1])
    await order_service.update_order_status(order_id, OrderStatus.COMPLETED)
    await event.message.answer("Заказ подтвержден.")


@router.message_callback(F.callback.payload.startswith("max_order_cancel:"))
async def order_cancel(event: MessageCallback, order_service: IOrderService):
    order_id = int(event.callback.payload.split(":", 1)[1])
    await order_service.update_order_status(order_id, OrderStatus.CANCELLED, "Отклонено администратором")
    await event.message.answer("Заказ отклонен.")


@router.message_created(F.message.body.text == "Создать онлайн задачу")
async def start_online_task(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA]):
        return
    await context.set_state(AdminTaskStates.CREATE_ONLINE)
    await context.update_data(step="url")
    await event.message.answer("Введите ссылку на пост ВК:")


@router.message_created(AdminTaskStates.CREATE_ONLINE)
async def online_task_step(event: MessageCreated, context: MemoryContext,
                           online_task_service: IOnlineTaskService, user_service: IUserService):
    data = await context.get_data()
    step = data.get("step")
    text = (event.message.body.text or "").strip()
    try:
        if step == "url":
            if not re.match(r"^https?://(vk\.com|m\.vk\.com)/wall-?\d+_\d+.*$", text):
                await event.message.answer("Введите ссылку на пост ВК.")
                return
            await context.update_data(url=text, step="type")
            await event.message.answer("Введите тип: лайк, репост или комментарий")
            return
        if step == "type":
            task_type = TaskType(text.lower())
            await context.update_data(type=task_type.value, step="date")
            await event.message.answer("Введите дату начала (ДД.ММ.ГГГГ):")
            return
        if step == "date":
            start_date = datetime.strptime(text, "%d.%m.%Y").date()
            if start_date < date.today():
                await event.message.answer("Дата не может быть в прошлом.")
                return
            await context.update_data(date=start_date, step="duration")
            await event.message.answer("Введите длительность в днях:")
            return
        if step == "duration":
            await context.update_data(duration=int(text), step="reward")
            await event.message.answer("Введите награду в баллах:")
            return
        if step == "reward":
            await online_task_service.create_task(
                date=data["date"],
                duration=data["duration"],
                type=TaskType(data["type"]),
                reward=int(text),
                url=data["url"],
            )
            await event.message.answer("Онлайн задача создана.")
            await context.clear()
            await _main_menu(event, user_service)
    except Exception as e:
        await event.message.answer(f"Ошибка: {e}")


@router.message_created(F.message.body.text == "Создать офлайн задачу")
async def start_offline_task(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]):
        return
    role = await _role(event, user_service)
    await context.set_state(AdminTaskStates.CREATE_OFFLINE)
    await context.update_data(step="title", role=role.name)
    await event.message.answer("Введите название задачи:")


@router.message_created(AdminTaskStates.CREATE_OFFLINE)
async def offline_task_step(event: MessageCreated, context: MemoryContext,
                            offline_task_service: IOfflineTaskService, user_service: IUserService):
    data = await context.get_data()
    step = data.get("step")
    text = (event.message.body.text or "").strip()
    try:
        if step == "title":
            await context.update_data(title=text, step="description")
            await event.message.answer("Введите описание:")
            return
        if step == "description":
            await context.update_data(description=text, step="location")
            await event.message.answer("Введите место:")
            return
        if step == "location":
            await context.update_data(location=text, step="contacts")
            await event.message.answer("Введите контакты:")
            return
        if step == "contacts":
            await context.update_data(contacts=text, step="start_date")
            await event.message.answer("Введите дату начала (ДД.ММ.ГГГГ):")
            return
        if step == "start_date":
            start_date = datetime.strptime(text, "%d.%m.%Y").date()
            await context.update_data(start_date=start_date, step="duration")
            await event.message.answer("Введите длительность в днях:")
            return
        if step == "duration":
            await context.update_data(duration=int(text), step="reward")
            await event.message.answer("Введите награду в баллах:")
            return
        if step == "reward":
            role = UserRole[data["role"]]
            await context.update_data(reward=int(text))
            if role == UserRole.STAFF_CA:
                await context.update_data(step="region")
                await event.message.answer("Введите регион:")
                return
            user = await user_service.get_user(_uid(event), Sources.MAX)
            await create_offline_from_data(event, context, offline_task_service, user_service, user.region)
            return
        if step == "region":
            await create_offline_from_data(event, context, offline_task_service, user_service, text)
    except Exception as e:
        await event.message.answer(f"Ошибка: {e}")


async def create_offline_from_data(event, context, offline_task_service, user_service, region: str):
    data = await context.get_data()
    await offline_task_service.create_task_by_admin(
        region=region,
        start_date=data["start_date"],
        duration=data["duration"],
        reward=data["reward"],
        title=data["title"],
        description=data["description"],
        location=data["location"],
        contacts=data["contacts"],
    )
    await event.message.answer("Офлайн задача создана.")
    await context.clear()
    await _main_menu(event, user_service)


@router.message_created(F.message.body.text == "Проверить офлайн задачи")
async def verify_offline(event: MessageCreated, user_service: IUserService,
                         offline_task_service: IOfflineTaskService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]):
        return
    user = await user_service.get_user(_uid(event), Sources.MAX)
    tasks, total = await offline_task_service.search_tasks(user.id, user.source, 1)
    if user.role != UserRole.STAFF_CA:
        tasks = [item for item in tasks if item.region == user.region]
    if not tasks:
        await event.message.answer("Нет задач для проверки.")
        return
    rows = [[(f"#{item.id} {item.title[:25]}", f"max_verify_task:{item.id}")] for item in tasks]
    await event.message.answer("Выберите задачу:", attachments=[_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_verify_task:"))
async def verify_task(event: MessageCallback, offline_task_service: IOfflineTaskService):
    task_id = int(event.callback.payload.split(":", 1)[1])
    users, _ = await offline_task_service.get_users_for_task(task_id, 1, PAGE_LIMIT)
    if not users:
        await event.message.answer("Нет участников в процессе.")
        return
    rows = [[(f"{item.user_id} {item.user_source.value}", f"max_verify_user:{task_id}:{item.user_id}:{item.user_source.name}")] for item in users]
    await event.message.answer("Выберите участника:", attachments=[_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_verify_user:"))
async def verify_user(event: MessageCallback, user_service: IUserService):
    _, task_id, user_id, source = event.callback.payload.split(":")
    user = await user_service.get_user(int(user_id), Sources[source])
    rows = [
        [("Принять", f"max_verify_accept:{task_id}:{user_id}:{source}")],
        [("Отклонить", f"max_verify_decline:{task_id}:{user_id}:{source}")],
    ]
    await event.message.answer(
        f"{user.surname} {user.name} {user.patronymic or ''}\n{user.phone_number}",
        attachments=[_keyboard(rows).as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_verify_accept:"))
@router.message_callback(F.callback.payload.startswith("max_verify_decline:"))
async def verify_action(event: MessageCallback, offline_task_service: IOfflineTaskService,
                        notification_service: INotificationService):
    parts = event.callback.payload.split(":")
    action = parts[0]
    task_id = int(parts[1])
    user_id = int(parts[2])
    source = Sources[parts[3]]
    status = TaskStatus.ACCEPTED if action == "max_verify_accept" else TaskStatus.DECLINED
    await offline_task_service.check_task(user_id, source, task_id, status)
    await notification_service.notify_user(user_id, source, f"Ваша офлайн задача #{task_id}: {status.value}.")
    await event.message.answer("Статус обновлен.")


@router.message_created(F.message.body.text == "Управление пользователями")
async def search_users(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA]):
        return
    await context.set_state(AdminCAStates.SEARCH_FIO)
    await event.message.answer("Введите фамилию пользователя:")


@router.message_created(AdminCAStates.SEARCH_FIO)
async def search_users_result(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    text = (event.message.body.text or "").strip()
    parts = text.split()
    surname = parts[0] if parts else text
    name = parts[1] if len(parts) > 1 else ""
    users = await user_service.search_users_by_fio(surname, name, None, 0, PAGE_LIMIT)
    await context.clear()
    if not users:
        await event.message.answer("Пользователи не найдены.")
        return
    grouped = {}
    for user in users:
        grouped.setdefault(_profile_key(user), []).append(user)
    rows = []
    for key, profile_users in grouped.items():
        phone = profile_users[0].phone_number
        rows.append([(_profile_title(profile_users), f"max_ca_profile:{phone}")])
    await event.message.answer("Выберите пользователя:", attachments=[_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_ca_profile:"))
async def user_card(event: MessageCallback, user_service: IUserService):
    phone = event.callback.payload.split(":", 1)[1]
    users = await _load_profile_users(user_service, phone)
    if not users:
        await event.message.answer("Профиль не найден.")
        return
    user = users[0]
    key = _profile_key(user)
    rows = []
    for role in [UserRole.USER, UserRole.STAFF_RO, UserRole.COORDINATOR_RO, UserRole.HEADLINER]:
        rows.append([(role.value, f"max_ca_role_group:{phone}:{role.name}")])
    platforms = "\n".join(
        f"{item.source.value}: {item.role.value}, id {item.id}"
        for item in users
    )
    await event.message.answer(
        f"{user.surname} {user.name} {user.patronymic or ''}\n"
        f"Телефон: {user.phone_number}\n\n"
        f"Площадки:\n{platforms}",
        attachments=[_keyboard(rows).as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_ca_role_group:"))
async def set_user_role(event: MessageCallback, user_service: IUserService, notification_service: INotificationService):
    _, phone, role = event.callback.payload.split(":")
    new_role = UserRole[role]
    users = await _load_profile_users(user_service, phone)
    for user in users:
        await user_service.update_user_role(user.id, user.source, new_role)
        await notification_service.notify_user(user.id, user.source, f"Ваша роль изменена на: {new_role.value}")
    platforms = ", ".join(sorted({user.source.value for user in users}))
    await event.message.answer(f"Роль изменена на {new_role.value}: {platforms}.")


@router.message_created(F.message.body.text == "Создать закрытое мероприятие")
async def start_event(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]):
        return
    user = await user_service.get_user(_uid(event), Sources.MAX)
    region = user.region if user.role == UserRole.COORDINATOR_RO else None
    await context.set_state(ClosedEventStates.CREATE)
    await context.update_data(step="title", region=region)
    await event.message.answer("Введите название мероприятия:")


@router.message_created(ClosedEventStates.CREATE)
async def event_step(event: MessageCreated, context: MemoryContext,
                     closed_event_service: IClosedEventService, user_service: IUserService):
    data = await context.get_data()
    step = data.get("step")
    text = (event.message.body.text or "").strip()
    try:
        if step == "title":
            await context.update_data(title=text, step="desc")
            await event.message.answer("Введите описание:")
            return
        if step == "desc":
            await context.update_data(desc=text, step="loc")
            await event.message.answer("Введите место:")
            return
        if step == "loc":
            await context.update_data(loc=text, step="dt")
            await event.message.answer("Введите дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):")
            return
        if step == "dt":
            dt = datetime.strptime(text, "%d.%m.%Y %H:%M")
            await context.update_data(date=dt.date(), time=dt.time())
            data = await context.get_data()
            if data.get("region"):
                await finish_event(event, context, closed_event_service, user_service, data["region"])
                return
            await context.update_data(step="region")
            await event.message.answer("Введите регион:")
            return
        if step == "region":
            await finish_event(event, context, closed_event_service, user_service, text)
    except Exception as e:
        await event.message.answer(f"Ошибка: {e}")


async def finish_event(event, context, closed_event_service, user_service, region: str):
    data = await context.get_data()
    item = await closed_event_service.create_event(data["title"], data["desc"], data["loc"], data["date"], data["time"], region)
    await context.clear()
    await event.message.answer(f"Мероприятие создано: {item.title}.")
    await _main_menu(event, user_service)


@router.message_created(F.message.body.text == "Список участников мероприятия")
async def admin_events(event: MessageCreated, user_service: IUserService, closed_event_service: IClosedEventService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]):
        return
    user = await user_service.get_user(_uid(event), Sources.MAX)
    region = None if user.role == UserRole.STAFF_CA else user.region
    events, total_count = await closed_event_service.list_events(region, 1)
    if not events:
        await event.message.answer("Нет мероприятий.")
        return
    rows = [[(f"{item.title[:30]} ({item.region})", f"max_event_parts:{item.id}")] for item in events]
    await event.message.answer("Выберите мероприятие:", attachments=[_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_event_parts:"))
async def event_parts(event: MessageCallback, user_service: IUserService, closed_event_service: IClosedEventService):
    event_id = int(event.callback.payload.split(":", 1)[1])
    regs, _ = await closed_event_service.list_participants(event_id, 1)
    if not regs:
        await event.message.answer("Участников пока нет.")
        return
    lines = []
    for reg in regs:
        try:
            user = await user_service.get_user(reg.user_id, reg.user_source)
            lines.append(f"{user.surname} {user.name} {user.phone_number}")
        except Exception:
            lines.append(f"{reg.user_id} {reg.user_source.value}")
    await event.message.answer("Участники:\n" + "\n".join(lines))


@router.message_created(F.message.body.text == "Рассылка координаторам РО")
async def coordinator_mailing(event: MessageCreated, user_service: IUserService, notification_service: INotificationService):
    if not await _check_role(event, user_service, [UserRole.STAFF_CA]):
        return
    users = await user_service.get_users_by_role(UserRole.COORDINATOR_RO)
    for user in users:
        await notification_service.notify_user(user.id, user.source, "Сообщение от сотрудника ЦА.")
    await event.message.answer(f"Рассылка отправлена. Получателей: {len(users)}.")
