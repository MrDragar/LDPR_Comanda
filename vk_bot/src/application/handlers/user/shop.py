import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, Text, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import ShopStates
from src.domain.entities import Sources
from src.services.interfaces import IProductService, IOrderService, IBalanceService, IUserService, INotificationService
from src.application.filters import CMDRule
from src.domain.exceptions import DomainError

logger = logging.getLogger(__name__)
router = BotLabeler()
ITEMS_PER_PAGE = 5


def _shop_kb(prods, page, total, prefix="shop"):
    kb = Keyboard(inline=True)
    for p in prods:
        kb.add(Callback(f"- {p.name} - {p.price}б", {"cmd": f"view_{prefix}", "pid": p.id}))
        kb.row()
    kb.row()
    if total > 1:
        if page > 1: kb.add(Callback("⬅️", {"cmd": f"prev_{prefix}"}))
        if page < total: kb.add(Callback("➡️", {"cmd": f"next_{prefix}"}))
    kb.add(Callback("🔙 На главную", {"cmd": "back_to_menu"}))
    return kb.get_json()


@router.message(text=["Магазин"])
async def open_shop(message: Message, product_service: IProductService, balance_service: IBalanceService, state_dispenser: BuiltinStateDispenser):
    bal = await balance_service.get_balance(message.from_id, Sources.VK)
    prods, total = await product_service.list_products(1)
    if not prods: return await message.answer("Магазин временно пуст.")
    await state_dispenser.set(message.from_id, ShopStates.BROWSE, page=1, total=total)
    await message.answer(f"💳 Ваш баланс: {bal} баллов.\n📦 Список доступных товаров:", keyboard=_shop_kb(prods, 1, total))


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_shop"))
async def next_shop(event: GroupTypes.MessageEvent, product_service: IProductService, balance_service: IBalanceService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    np = state.payload.get("page", 1) + 1
    prods, total = await product_service.list_products(np)
    bal = await balance_service.get_balance(event.object.user_id, Sources.VK)
    await state_dispenser.set(event.object.peer_id, ShopStates.BROWSE, page=np, total=total)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"💳 Ваш баланс: {bal} баллов.\n📦 Список доступных товаров:", keyboard=_shop_kb(prods, np, total), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_shop"))
async def prev_shop(event: GroupTypes.MessageEvent, product_service: IProductService, balance_service: IBalanceService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    np = max(1, state.payload.get("page", 1) - 1)
    prods, total = await product_service.list_products(np)
    bal = await balance_service.get_balance(event.object.user_id, Sources.VK)
    await state_dispenser.set(event.object.peer_id, ShopStates.BROWSE, page=np, total=total)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"💳 Ваш баланс: {bal} баллов.\n📦 Список доступных товаров:", keyboard=_shop_kb(prods, np, total), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_shop"))
async def view_prod(event: GroupTypes.MessageEvent, product_service: IProductService, state_dispenser: BuiltinStateDispenser):
    p = await product_service.get_product(event.object.payload["pid"])
    if not p: return await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Товар не найден", random_id=0)
    kb = Keyboard(inline=True).add(Callback("🛒 Купить", {"cmd": "buy_prod", "pid": p.id})).row().add(Callback("Назад", {"cmd": "back_shop"}))
    await state_dispenser.set(event.object.peer_id, ShopStates.BROWSE, pid=p.id) # сохраняем для возврата
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"{p.image_url}\n📌 {p.name}\n💰 {p.price} баллов\n📝 {p.description}", keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("buy_prod"))
async def start_buy(event: GroupTypes.MessageEvent, balance_service: IBalanceService, product_service: IProductService, state_dispenser: BuiltinStateDispenser):
    pid = event.object.payload["pid"]
    p = await product_service.get_product(pid)
    bal = await balance_service.get_balance(event.object.user_id, Sources.VK)
    if bal < p.price:
        kb = Keyboard(one_time=True).add(Text("Назад")).row().add(Text("На главную"))
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="⚠️ Вам не хватает средств для покупки этого товара", keyboard=kb.get_json(), random_id=0)
        return await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)
    kb = Keyboard(one_time=True).add(Text("По почте")).add(Text("Заберу лично")).row().add(Text("Назад"))
    await state_dispenser.set(event.object.peer_id, ShopStates.DELIVERY_CHOICE, pid=pid, price=p.price)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="🚚 Как вы хотите получить товар?", keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.message(text=["По почте"])
async def mail_addr(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if state.state != str(ShopStates.DELIVERY_CHOICE): return
    await state_dispenser.set(message.from_id, ShopStates.MAIL_ADDR, **state.payload)
    await message.answer("📍 Укажите адрес и индекс почтового отделения:")


@router.message(state=ShopStates.MAIL_ADDR)
async def mail_fio(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(message.from_id, ShopStates.MAIL_FIO, **state.payload, addr=message.text.strip())
    await message.answer("👤 Укажите ваше ФИО как в паспорте:")


@router.message(state=ShopStates.MAIL_FIO)
async def finalize_mail(message: Message, order_service: IOrderService, notification_service: INotificationService, balance_service: IBalanceService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    try:
        await balance_service.deduct_balance(message.from_id, Sources.VK, state.payload["price"], f"Покупка товара #{state.payload['pid']}")
        order = await order_service.create_order(message.from_id, Sources.VK, state.payload["pid"], "mail", state.payload["addr"], message.text.strip())
        await state_dispenser.delete(message.from_id)
        await notification_service.notify_user_vk(message.from_id, f"✅ Заказ #{order.id} оформлен. Посылка будет отправлена по адресу: {state.payload['addr']}")
        kb = Keyboard(one_time=True).add(Text("На главную"))
        await message.answer("📦 Отлично, начинаем оформлять посылку!", keyboard=kb.get_json())
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(text=["Заберу лично"])
async def pickup(message: Message, user_service: IUserService, order_service: IOrderService, notification_service: INotificationService, balance_service: IBalanceService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if state.state != str(ShopStates.DELIVERY_CHOICE): return
    u = await user_service.get_user(message.from_id, Sources.VK)
    addr = await user_service.get_region_address(u.region)
    try:
        await balance_service.deduct_balance(message.from_id, Sources.VK, state.payload["price"], f"Покупка товара #{state.payload['pid']}")
        order = await order_service.create_order(message.from_id, Sources.VK, state.payload["pid"], "pickup", addr, None)
        await state_dispenser.delete(message.from_id)
        await notification_service.notify_user_vk(message.from_id, f"✅ Заказ #{order.id} оформлен. Заберите товар по адресу: {addr}")
        kb = Keyboard(one_time=True).add(Text("На главную"))
        await message.answer(f"📍 Отлично, забрать товар можете на {addr} (Заказ #{order.id}).", keyboard=kb.get_json())
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}")