import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import OrderStates
from src.domain.entities import Sources
from src.domain.entities.user import UserRole
from src.domain.entities.shop import OrderStatus
from src.services.interfaces import IOrderService, IUserService, INotificationService, \
    IBalanceService
from src.application.filters import check_role, CMDRule
from src.domain.exceptions import DomainError

logger = logging.getLogger(__name__)
router = BotLabeler()
ITEMS_PER_PAGE = 5


def _order_kb(orders, page, total, admin_region=None):
    kb = Keyboard(inline=True)
    for o in orders:
        kb.add(Callback(f"#{o.id} - {o.product_name} ({o.delivery_type})",
                        {"cmd": "view_order", "oid": o.id}))
        kb.row()

    kb.row()
    if total > 1:
        if page > 1: kb.add(Callback("⬅️", {"cmd": "prev_order"}))
        if page < total: kb.add(Callback("➡️", {"cmd": "next_order"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))
    return kb.get_json()


@router.message(text=["Управление заказами"])
async def start_orders(message: Message, order_service: IOrderService, user_service: IUserService,
                       state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    allowed = [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]
    if u.role not in allowed: return await message.answer("Недостаточно прав")

    region = u.region if u.role != UserRole.STAFF_CA else None
    orders, total = await order_service.get_admin_orders(region, 1)

    if not orders: return await message.answer("Нет ожидающих заказов.")

    await state_dispenser.set(message.from_id, OrderStates.BROWSE, page=1, total=total,
                              region=region)
    await message.answer(f"📦 Ожидающие заказы (стр. 1/{total}):",
                         keyboard=_order_kb(orders, 1, total, region))


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_order"))
async def next_order(event: GroupTypes.MessageEvent, order_service: IOrderService,
                     state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    np = state.payload.get("page", 1) + 1
    orders, total = await order_service.get_admin_orders(state.payload.get("region"), np)

    await state_dispenser.set(event.object.peer_id, OrderStates.BROWSE, page=np, total=total,
                              region=state.payload.get("region"))
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"📦 Ожидающие заказы (стр. {np}/{total}):",
                                      keyboard=_order_kb(orders, np, total,
                                                         state.payload.get("region")), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_order"))
async def prev_order(event: GroupTypes.MessageEvent, order_service: IOrderService,
                     state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    np = max(1, state.payload.get("page", 1) - 1)
    orders, total = await order_service.get_admin_orders(state.payload.get("region"), np)

    await state_dispenser.set(event.object.peer_id, OrderStates.BROWSE, page=np, total=total,
                              region=state.payload.get("region"))
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"📦 Ожидающие заказы (стр. {np}/{total}):",
                                      keyboard=_order_kb(orders, np, total,
                                                         state.payload.get("region")), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_order"))
async def view_order(event: GroupTypes.MessageEvent, order_service: IOrderService,
                     state_dispenser: BuiltinStateDispenser):
    oid = event.object.payload["oid"]
    orders, _ = await order_service.get_admin_orders(None, 1)  # быстрый поиск
    order = next((o for o in orders if o.id == oid), None)

    if not order: return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                           message="Заказ не найден", random_id=0)

    info = f"🆔 Заказ #{order.id}\n" \
           f"👤 Пользователь: {order.user_id}\n" \
           f"📦 Товар: {order.product_name}\n" \
           f"💰 Цена: {order.price}\n" \
           f"🚚 Доставка: {order.delivery_type}"

    if order.delivery_address: info += f"\n📍 Адрес: {order.delivery_address}"
    if order.delivery_fio: info += f"\n👤 ФИО: {order.delivery_fio}"

    kb = Keyboard(inline=True).add(Callback("✅ Принять", {"cmd": "accept_order", "oid": oid})).add(
        Callback("❌ Отклонить", {"cmd": "decline_order", "oid": oid})).row().add(
        Callback("⬅️ Назад", {"cmd": "back_orders"}))

    await state_dispenser.set(event.object.peer_id, OrderStates.BROWSE, view_oid=oid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=info,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("accept_order"))
async def accept_order(event: GroupTypes.MessageEvent, order_service: IOrderService,
                       notification_service: INotificationService,
                       state_dispenser: BuiltinStateDispenser):
    oid = event.object.payload["oid"]

    # update_order_status возвращает объект Order, из которого мы берем реальные данные пользователя
    order = await order_service.update_order_status(oid, OrderStatus.COMPLETED)

    msg = f"✅ Заказ #{oid} подтвержден!"
    # ✅ ИСПРАВЛЕНО: Уведомление уходит реальному пользователю с учетом его источника
    await notification_service.notify_user(order.user_id, order.user_source, msg)

    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message="✅ Заказ принят и передан в обработку.", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)
    await start_orders(event, order_service, None, state_dispenser)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("decline_order"))
async def ask_reason(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(event.object.peer_id, OrderStates.CANCEL_REASON,
                              oid=event.object.payload["oid"])
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message="⚠️ Укажите причину отклонения заказа:", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.message(state=OrderStates.CANCEL_REASON)
async def process_decline(message: Message, order_service: IOrderService,
                          notification_service: INotificationService,
                          state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    oid = state.payload.get("oid")
    reason = message.text.strip()

    try:
        order = await order_service.update_order_status(oid, OrderStatus.CANCELLED, reason)
        await notification_service.notify_user(order.user_id, order.user_source,
                                               f"❌ Заказ #{oid} отклонен. Причина: {reason}. Баллы возвращены на баланс.")
        await state_dispenser.delete(message.from_id)
        await message.answer(
            f"✅ Заказ #{oid} отклонен. Причина сохранена. Баллы возвращены пользователю.")
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}")