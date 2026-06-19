import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.application.states import OrderStates
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.domain.entities.user import UserRole, Sources
from src.domain.entities.shop import OrderStatus
from src.domain.exceptions import DomainError
from src.services.interfaces import IOrderService, IUserService, INotificationService, \
    IBalanceService
from src.application.filters import AdminFilter
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)

ITEMS_PER_PAGE = 5


async def _render_orders(event: types.Message | types.CallbackQuery, orders, page, total, region,
                         is_callback=False):
    builder = InlineKeyboardBuilder()
    for o in orders:
        builder.button(text=f"#{o.id} - {o.product_name} ({o.delivery_type})",
                       callback_data=f"ord_view_{o.id}")
    builder.adjust(1)

    if total > 1:
        if page > 1: builder.button(text="⬅️", callback_data=f"ord_prev_{page}")
        if page < total: builder.button(text="➡️", callback_data=f"ord_next_{page}")

    text = f"📦 Ожидающие заказы (стр. {page}/{total}):"
    if is_callback:
        await event.message.answer(text, reply_markup=builder.as_markup())
    else:
        await event.answer(text, reply_markup=builder.as_markup())


@router.message(F.text == "Управление заказами")
async def start_orders(message: types.Message, order_service: IOrderService,
                       user_service: IUserService, state: FSMContext):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await message.answer("Недостаточно прав")

    region = u.region if u.role != UserRole.STAFF_CA else None
    orders, total = await order_service.get_admin_orders(region, 1)
    if not orders:
        return await message.answer("Нет ожидающих заказов.")

    await state.update_data(region=region, page=1, total=total)
    await state.set_state(OrderStates.browse)
    await _render_orders(message, orders, 1, total, region)


@router.callback_query(F.data.startswith("ord_next_"), OrderStates.browse)
async def next_order(query: types.CallbackQuery, state: FSMContext, order_service: IOrderService):
    page = int(query.data.split("_")[-1])
    data = await state.get_data()
    orders, total = await order_service.get_admin_orders(data.get("region"), page)
    await state.update_data(page=page, total=total)
    await _render_orders(query, orders, page, total, data.get("region"), is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("ord_prev_"), OrderStates.browse)
async def prev_order(query: types.CallbackQuery, state: FSMContext, order_service: IOrderService):
    page = int(query.data.split("_")[-1])
    data = await state.get_data()
    orders, total = await order_service.get_admin_orders(data.get("region"), page)
    await state.update_data(page=page, total=total)
    await _render_orders(query, orders, page, total, data.get("region"), is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("ord_view_"), OrderStates.browse)
async def view_order(query: types.CallbackQuery, order_service: IOrderService, state: FSMContext):
    oid = int(query.data.split("_")[-1])
    # Получаем заказ (в реальности нужен метод get_by_id, но используем существующий get_admin_orders для поиска)
    orders, _ = await order_service.get_admin_orders(None, 1)
    order = next((o for o in orders if o.id == oid), None)
    if not order:
        return await query.answer("Заказ не найден", show_alert=True)

    info = (f"🆔 Заказ #{order.id}\n"
            f"👤 Пользователь: {order.user_id} (Source: {order.user_source.value})\n"
            f"📦 Товар: {order.product_name}\n"
            f"💰 Цена: {order.price}\n"
            f"🚚 Доставка: {order.delivery_type}")
    if order.delivery_address: info += f"\n📍 Адрес: {order.delivery_address}"
    if order.delivery_fio: info += f"\n👤 ФИО: {order.delivery_fio}"

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"ord_accept_{oid}")
    builder.button(text="❌ Отклонить", callback_data=f"ord_decline_{oid}")
    builder.button(text="⬅️ Назад", callback_data="ord_back_list")
    builder.adjust(2, 1)

    await state.update_data(view_oid=oid)
    await query.message.answer(info, reply_markup=builder.as_markup())
    await query.answer()


@router.callback_query(F.data.startswith("ord_accept_"))
async def accept_order(query: types.CallbackQuery, order_service: IOrderService,
                       state: FSMContext):
    oid = int(query.data.split("_")[-1])
    await order_service.update_order_status(oid, OrderStatus.COMPLETED)
    await query.message.answer("✅ Заказ принят и передан в обработку.")

    data = await state.get_data()
    orders, total = await order_service.get_admin_orders(data.get("region"), 1)
    await state.update_data(page=1, total=total)
    await _render_orders(query, orders, 1, total, data.get("region"), is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("ord_decline_"))
async def ask_reason(query: types.CallbackQuery, state: FSMContext):
    oid = int(query.data.split("_")[-1])
    await state.update_data(decline_oid=oid)
    await query.message.answer("⚠️ Укажите причину отклонения заказа:", reply_markup=get_cancel_keyboard())
    await state.set_state(OrderStates.cancel_reason)
    await query.answer()


@router.message(OrderStates.cancel_reason)
async def process_decline(message: types.Message, state: FSMContext, order_service: IOrderService, notification_service: INotificationService, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]:
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        return await message.answer("Отклонение отменено.", reply_markup=get_role_menu_keyboard(role))

    data = await state.get_data()
    oid = data.get("decline_oid")
    reason = message.text.strip()
    try:
        order = await order_service.update_order_status(oid, OrderStatus.CANCELLED, reason)
        await notification_service.notify_user(order.user_id, order.user_source, f"❌ Заказ #{oid} отклонен. Причина: {reason}. Баллы возвращены.")
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        await message.answer(f"✅ Заказ #{oid} отклонен.", reply_markup=get_role_menu_keyboard(role))
        await state.clear()
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=get_cancel_keyboard())


@router.callback_query(F.data == "ord_back_list", OrderStates.browse)
async def back_orders(query: types.CallbackQuery, state: FSMContext, order_service: IOrderService):
    data = await state.get_data()
    page = data.get("page", 1)
    orders, total = await order_service.get_admin_orders(data.get("region"), page)
    await _render_orders(query, orders, page, total, data.get("region"), is_callback=True)
    await query.answer()
