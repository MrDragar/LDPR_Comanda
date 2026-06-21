import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.application.states import OrderStates
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.domain.entities.user import UserRole, Sources
from src.domain.entities.shop import OrderStatus
from src.domain.exceptions import DomainError
from src.services.interfaces import IOrderService, IUserService, INotificationService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def _render_orders(event, orders, page, total, region):
    builder = InlineKeyboardBuilder()
    for o in orders:
        builder.row(CallbackButton(text=f"#{o.id} - {o.product_name} ({o.delivery_type})",
                                   payload=f"ord_view_{o.id}"))
    if total > 1:
        if page > 1: builder.row(CallbackButton(text="⬅️", payload=f"ord_prev_{page}"))
        if page < total: builder.row(CallbackButton(text="➡️", payload=f"ord_next_{page}"))
    text = f"📦 Ожидающие заказы (стр. {page}/{total}):"
    await event.message.answer(text, attachments=[builder.as_markup()])


@router.message_created(F.message.body.text == "Управление заказами")
async def start_orders(event: MessageCreated, order_service: IOrderService,
                       user_service: IUserService, context: MemoryContext):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await event.message.answer("Недостаточно прав")
    region = u.region if u.role != UserRole.STAFF_CA else None
    orders, total = await order_service.get_admin_orders(region, 1)
    if not orders:
        return await event.message.answer("Нет ожидающих заказов.")
    await context.update_data(region=region, page=1, total=total)
    await context.set_state(OrderStates.BROWSE)
    await _render_orders(event, orders, 1, total, region)


@router.message_callback(F.callback.payload.startswith("ord_next_"))
async def next_order(event: MessageCallback, context: MemoryContext, order_service: IOrderService):
    page = int(event.callback.payload.split("_")[-1])
    data = await context.get_data()
    orders, total = await order_service.get_admin_orders(data.get("region"), page)
    await context.update_data(page=page, total=total)
    await _render_orders(event, orders, page, total, data.get("region"))


@router.message_callback(F.callback.payload.startswith("ord_prev_"))
async def prev_order(event: MessageCallback, context: MemoryContext, order_service: IOrderService):
    page = int(event.callback.payload.split("_")[-1])
    data = await context.get_data()
    orders, total = await order_service.get_admin_orders(data.get("region"), page)
    await context.update_data(page=page, total=total)
    await _render_orders(event, orders, page, total, data.get("region"))


@router.message_callback(F.callback.payload.startswith("ord_view_"))
async def view_order(event: MessageCallback, order_service: IOrderService, context: MemoryContext):
    oid = int(event.callback.payload.split("_")[-1])
    orders, _ = await order_service.get_admin_orders(None, 1)
    order = next((o for o in orders if o.id == oid), None)
    if not order:
        return await event.message.answer("Заказ не найден")

    info = (f"🆔 Заказ #{order.id}\n"
            f"👤 Пользователь: {order.user_id} (Source: {order.user_source.value})\n"
            f"📦 Товар: {order.product_name}\n"
            f"💰 Цена: {order.price}\n"
            f"🚚 Доставка: {order.delivery_type}")
    if order.delivery_address: info += f"\n📍 Адрес: {order.delivery_address}"
    if order.delivery_fio: info += f"\n👤 ФИО: {order.delivery_fio}"

    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="✅ Принять", payload=f"ord_accept_{oid}"))
    builder.row(CallbackButton(text="❌ Отклонить", payload=f"ord_decline_{oid}"))
    builder.row(CallbackButton(text="⬅️ Назад", payload="ord_back_list"))

    await context.update_data(view_oid=oid)
    await event.message.answer(info, attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("ord_accept_"))
async def accept_order(event: MessageCallback, order_service: IOrderService,
                       context: MemoryContext):
    oid = int(event.callback.payload.split("_")[-1])
    await order_service.update_order_status(oid, OrderStatus.COMPLETED)
    await event.message.answer("✅ Заказ принят и передан в обработку.")
    data = await context.get_data()
    orders, total = await order_service.get_admin_orders(data.get("region"), 1)
    await context.update_data(page=1, total=total)
    await _render_orders(event, orders, 1, total, data.get("region"))


@router.message_callback(F.callback.payload.startswith("ord_decline_"))
async def ask_reason(event: MessageCallback, context: MemoryContext):
    oid = int(event.callback.payload.split("_")[-1])
    await context.update_data(decline_oid=oid)
    await event.message.answer("⚠️ Укажите причину отклонения заказа:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(OrderStates.CANCEL_REASON)


@router.message_created(OrderStates.CANCEL_REASON)
async def process_decline(event: MessageCreated, context: MemoryContext,
                          order_service: IOrderService, notification_service: INotificationService,
                          user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        return await event.message.answer("Отклонение отменено.",
                                          attachments=[get_role_menu_keyboard(role).as_markup()])
    data = await context.get_data()
    oid = data.get("decline_oid")
    reason = event.message.body.text.strip()
    try:
        order = await order_service.update_order_status(oid, OrderStatus.CANCELLED, reason)
        await notification_service.notify_user(order.user_id, order.user_source,
                                               f"❌ Заказ #{oid} отклонен. Причина: {reason}. Баллы возвращены.")
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer(f"✅ Заказ #{oid} отклонен.",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        await context.clear()
    except DomainError as e:
        await event.message.answer(f"❌ Ошибка: {e}",
                                   attachments=[get_cancel_keyboard().as_markup()])


@router.message_callback(F.callback.payload == "ord_back_list")
async def back_orders(event: MessageCallback, context: MemoryContext, order_service: IOrderService):
    data = await context.get_data()
    page = data.get("page", 1)
    orders, total = await order_service.get_admin_orders(data.get("region"), page)
    await _render_orders(event, orders, page, total, data.get("region"))