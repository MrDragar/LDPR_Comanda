import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.application.states import AdminCAStates
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IUserService, INotificationService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)

PAGE_LIMIT = 5
ROLE_HIERARCHY = {
    UserRole.STAFF_CA: 3,
    UserRole.COORDINATOR_RO: 2,
    UserRole.STAFF_RO: 1,
    UserRole.USER: 0
}


@router.message(F.text == "Управление пользователями")
async def start_search(message: types.Message, state: FSMContext, user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    if role != UserRole.STAFF_CA: return await message.answer("Недостаточно прав.")
    await message.answer("Введите фамилию пользователя для поиска:",
                         reply_markup=get_cancel_keyboard())
    await state.set_state(AdminCAStates.search_fio)


@router.message(AdminCAStates.search_fio)
async def process_fio(message: types.Message, state: FSMContext, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]:
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        return await message.answer("Поиск отменен.", reply_markup=get_role_menu_keyboard(role))

    query_fio = message.text.strip()
    if len(query_fio) < 2: return await message.answer("Введите минимум 2 символа.",
                                                       reply_markup=get_cancel_keyboard())

    parts = query_fio.split()
    surname, name = parts[0], parts[1] if len(parts) > 1 else ""
    users = await user_service.search_users_by_fio(surname, name, None, skip=0, limit=PAGE_LIMIT)
    await state.update_data(query=query_fio, page=1)
    await state.set_state(AdminCAStates.search_results)
    await _render_search(message, users, 1, user_service)


async def _render_search(event: types.Message | types.CallbackQuery, users: list, page: int,
                         user_service: IUserService, is_callback=False):
    builder = InlineKeyboardBuilder()
    if not users:
        text = "Пользователи не найдены."
    else:
        text = "Выберите пользователя:"
        for u in users:
            builder.button(text=f"{u.surname} {u.name} ({u.role.value})",
                           callback_data=f"ca_sel_{u.id}")
        builder.adjust(1)

    builder.button(text="🔙 В меню", callback_data="ca_cancel")

    if is_callback:
        await event.message.answer(text, reply_markup=builder.as_markup())
    else:
        await event.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("ca_cancel"))
async def cancel_search(query: types.CallbackQuery, state: FSMContext, user_service: IUserService):
    role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    await query.message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
    await state.clear()
    await query.answer()


@router.callback_query(F.data.startswith("ca_sel_"))
async def select_user(query: types.CallbackQuery, user_service: IUserService):
    uid = int(query.data.split("_")[-1])
    admin_role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    try:
        target_user = await user_service.get_user(uid, Sources.TG)
    except Exception:
        return await query.answer("Пользователь не найден", show_alert=True)

    target_level = ROLE_HIERARCHY.get(target_user.role, 0)

    text = (f"👤 {target_user.surname} {target_user.name} {target_user.patronymic or ''}\n"
            f"🌍 {target_user.region}\n"
            f"🎯 Текущая роль: {target_user.role.value}")

    builder = InlineKeyboardBuilder()
    if admin_level > target_level:
        builder.button(text="🔄 Поменять роль", callback_data=f"ca_chg_{uid}")
    else:
        builder.button(text="🔄 Поменять роль (недоступно)", callback_data="ca_no_perm")
    builder.button(text="🔙 Назад", callback_data="ca_cancel")
    builder.adjust(1)

    await query.message.answer(text, reply_markup=builder.as_markup())
    await query.answer()


@router.callback_query(F.data == "ca_no_perm")
async def no_perm(query: types.CallbackQuery):
    await query.answer("❌ Вы можете менять роль только пользователям с более низким рангом.",
                       show_alert=True)


@router.callback_query(F.data.startswith("ca_chg_"))
async def change_role_menu(query: types.CallbackQuery, user_service: IUserService):
    uid = int(query.data.split("_")[-1])
    admin_role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    builder = InlineKeyboardBuilder()
    for r in UserRole:
        if ROLE_HIERARCHY.get(r, 0) < admin_level:
            builder.button(text=r.value, callback_data=f"ca_set_{uid}_{r.value}")
    builder.button(text="❌ Отмена", callback_data=f"ca_sel_{uid}")
    builder.adjust(1)

    await query.message.answer("Выберите новую роль:", reply_markup=builder.as_markup())
    await query.answer()


@router.callback_query(F.data.startswith("ca_set_"))
async def set_role(query: types.CallbackQuery, user_service: IUserService,
                   notification_service: INotificationService):
    parts = query.data.split("_")
    uid = int(parts[2])
    role_name = parts[3]

    admin_role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    try:
        new_role = UserRole(role_name)
    except KeyError:
        return await query.answer("Ошибка роли", show_alert=True)

    if ROLE_HIERARCHY.get(new_role, 0) >= admin_level:
        return await query.answer("❌ Нельзя установить роль равную или выше вашей.",
                                  show_alert=True)

    await user_service.update_user_role(uid, Sources.TG, new_role)
    await notification_service.notify_user(uid, Sources.TG,
                                           f"Ваша роль изменена на: {new_role.value}")

    await query.message.answer(f"✅ Роль пользователя изменена на {new_role.value}")
    await query.answer()
