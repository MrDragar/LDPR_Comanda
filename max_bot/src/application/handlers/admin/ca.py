import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.application.states import AdminCAStates
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IUserService, INotificationService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()
PAGE_LIMIT = 5

ROLE_HIERARCHY = {
    UserRole.STAFF_CA: 3,
    UserRole.COORDINATOR_RO: 2,
    UserRole.STAFF_RO: 1,
    UserRole.USER: 0
}


@router.message_created(F.message.body.text == "Управление пользователями")
async def start_search(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    # Админ всегда находится в том источнике, откуда он пишет (в данном случае MAX)
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    if role != UserRole.STAFF_CA and role != UserRole.COORDINATOR_RO:
        return await event.message.answer("Недостаточно прав.")

    await event.message.answer("Введите фамилию пользователя для поиска:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(AdminCAStates.SEARCH_FIO)


@router.message_created(AdminCAStates.SEARCH_FIO)
async def process_fio(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        return await event.message.answer("Поиск отменен.",
                                          attachments=[get_role_menu_keyboard(role).as_markup()])

    query_fio = event.message.body.text.strip()
    if len(query_fio) < 2:
        return await event.message.answer("Введите минимум 2 символа.",
                                          attachments=[get_cancel_keyboard().as_markup()])

    parts = query_fio.split()
    surname, name = parts[0], parts[1] if len(parts) > 1 else ""
    users = await user_service.search_users_by_fio(surname, name, None, skip=0, limit=PAGE_LIMIT)

    await context.update_data(query=query_fio, page=1)
    await context.set_state(AdminCAStates.SEARCH_RESULTS)
    await _render_search(event, users, 1, user_service)


async def _render_search(event, users: list, page: int, user_service: IUserService):
    builder = InlineKeyboardBuilder()
    if not users:
        text = "Пользователи не найдены."
    else:
        text = "Выберите пользователя:"
        for u in users:
            # Передаем source пользователя в payload
            builder.row(CallbackButton(text=f"{u.surname} {u.name} ({u.role.value})",
                                       payload=f"ca_sel_{u.id}_{u.source.value}"))
    builder.row(CallbackButton(text="🔙 В меню", payload="ca_cancel"))

    await event.message.answer(text, attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload == "ca_cancel")
async def cancel_search(event: MessageCallback, context: MemoryContext, user_service: IUserService):
    await event.answer()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Главное меню",
                               attachments=[get_role_menu_keyboard(role).as_markup()])
    await context.clear()


@router.message_callback(F.callback.payload.startswith("ca_sel_"))
async def select_user(event: MessageCallback, user_service: IUserService):
    await event.answer()
    parts = event.callback.payload.split("_")
    uid = int(parts[2])
    source_str = parts[3]
    source = Sources(source_str)

    admin_role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    try:
        # Используем извлеченный source для получения пользователя
        target_user = await user_service.get_user(uid, source)
    except Exception:
        return await event.message.answer("Пользователь не найден")

    target_level = ROLE_HIERARCHY.get(target_user.role, 0)
    text = (f"👤 {target_user.surname} {target_user.name} {target_user.patronymic or ''}\n"
            f"🌍 {target_user.region}\n"
            f"🎯 Текущая роль: {target_user.role.value}\n"
            f"📱 Источник: {source.value.upper()}")

    builder = InlineKeyboardBuilder()
    if admin_level > target_level:
        # Передаем source в кнопку смены роли
        builder.row(CallbackButton(text="🔄 Поменять роль", payload=f"ca_chg_{uid}_{source_str}"))
    else:
        builder.row(CallbackButton(text="🔄 Поменять роль (недоступно)", payload="ca_no_perm"))
    builder.row(CallbackButton(text="🔙 Назад", payload="ca_cancel"))

    await event.message.answer(text, attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload == "ca_no_perm")
async def no_perm(event: MessageCallback):
    await event.answer()
    await event.message.answer(
        "❌ Вы можете менять роль только пользователям с более низким рангом.")


@router.message_callback(F.callback.payload.startswith("ca_chg_"))
async def change_role_menu(event: MessageCallback, user_service: IUserService):
    await event.answer()
    parts = event.callback.payload.split("_")
    uid = int(parts[2])
    source_str = parts[3]

    admin_role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    builder = InlineKeyboardBuilder()
    for r in UserRole:
        if ROLE_HIERARCHY.get(r, 0) < admin_level:
            # Передаем source и название роли в payload
            builder.row(CallbackButton(text=r.value, payload=f"ca_set_{uid}_{source_str}_{r.value}"))
    # Кнопка отмены возвращает к просмотру пользователя
    builder.row(CallbackButton(text="❌ Отмена", payload=f"ca_sel_{uid}_{source_str}"))

    await event.message.answer("Выберите новую роль:", attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("ca_set_"))
async def set_role(event: MessageCallback, user_service: IUserService,
                   notification_service: INotificationService):
    await event.answer()
    parts = event.callback.payload.split("_")
    uid = int(parts[2])
    source_str = parts[3]
    source = Sources(source_str)
    role_name = "_".join(parts[4:])

    admin_role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    try:
        new_role = UserRole(role_name)
    except ValueError:
        return await event.message.answer("Ошибка роли")

    if ROLE_HIERARCHY.get(new_role, 0) >= admin_level:
        return await event.message.answer("❌ Нельзя установить роль равную или выше вашей.")

    # Обновляем роль и отправляем уведомление с учетом правильного source
    await user_service.update_user_role(uid, source, new_role)
    await notification_service.notify_user(uid, source,
                                           f"Ваша роль изменена на: {new_role.value}")
    await event.message.answer(f"✅ Роль пользователя изменена на {new_role.value}")