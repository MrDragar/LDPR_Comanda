import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.filters import CMDRule
from src.application.states import AdminCAStates
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IUserService

logger = logging.getLogger(__name__)
router = BotLabeler()

ROLE_HIERARCHY = {
    UserRole.STAFF_CA: 3,
    UserRole.COORDINATOR_RO: 2,
    UserRole.STAFF_RO: 1,
    UserRole.HEADLINER: 1,
    UserRole.USER: 0
}
PAGE_LIMIT = 5


def _send_search_results(peer_id, query_fio: str, page: int, state_dispenser: BuiltinStateDispenser,
                         user_service: IUserService, api, is_callback=False):
    users = user_service.search_users_by_fio(query_fio.split()[0], query_fio.split()[1] if len(
        query_fio.split()) > 1 else "", None, skip=(page - 1) * PAGE_LIMIT, limit=PAGE_LIMIT)


async def _render_search(state, page, user_service, api, peer_id, event_id=None, user_id=None,
                         is_callback=False):
    query = state.payload.get("query", "")
    parts = query.strip().split()
    surname = parts[0] if len(parts) > 0 else ""
    name = parts[1] if len(parts) > 1 else ""

    users = await user_service.search_users_by_fio(surname, name, None,
                                                   skip=(page - 1) * PAGE_LIMIT, limit=PAGE_LIMIT)
    if not users:
        msg = "Пользователи не найдены."
    else:
        msg = "Выберите пользователя:"

    kb = Keyboard(inline=True)
    for u in users:
        kb.add(
            Callback(f"{u.surname} {u.name} - {u.role.value}", {"cmd": "select_user", "uid": u.id}))
        kb.row()
    kb.row()
    total_est = len(users)  # Упрощённо, для реального пагинации нужно делать COUNT
    if page > 1: kb.add(Callback("⬅️ Назад", {"cmd": "prev_search"}))
    if total_est == PAGE_LIMIT: kb.add(Callback("Вперёд ➡️", {"cmd": "next_search"}))
    kb.add(Callback("Назад в меню", {"cmd": "back_to_menu"}))

    if is_callback:
        await api.messages.send(peer_id=peer_id, message=msg, keyboard=kb.get_json(), random_id=0)
        await api.messages.send_message_event_answer(event_id=event_id, user_id=user_id,
                                                     peer_id=peer_id)
    else:
        await api.messages.send(peer_id=peer_id, message=msg, keyboard=kb.get_json(), random_id=0)


@router.message(text=["Управление пользователями"])
async def start_search(message: Message, user_service: IUserService,
                       state_dispenser: BuiltinStateDispenser):
    if not (await user_service.get_user_role(message.from_id, Sources.VK)) in [UserRole.STAFF_CA]:
        return await message.answer("Недостаточно прав")
    await message.answer("Введите фамилию пользователя для поиска:")
    await state_dispenser.set(message.from_id, AdminCAStates.SEARCH_FIO, page=1)


@router.message(state=AdminCAStates.SEARCH_FIO)
async def search_fio(message: Message, user_service: IUserService,
                     state_dispenser: BuiltinStateDispenser):
    if len(message.text.strip()) < 2: return await message.answer(
        "Введите минимум 2 символа фамилии")
    await state_dispenser.set(message.from_id, AdminCAStates.SEARCH_RESULTS,
                              query=message.text.strip(), page=1)
    await _render_search(await state_dispenser.get(message.from_id), 1, user_service,
                         message.ctx_api, message.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_search"))
async def next_search(event: GroupTypes.MessageEvent, user_service: IUserService,
                      state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    new_page = state.payload.get("page", 1) + 1
    await state_dispenser.set(event.object.peer_id, AdminCAStates.SEARCH_RESULTS, **state.payload,
                              page=new_page)
    await _render_search(state, new_page, user_service, event.ctx_api, event.object.peer_id,
                         event.object.event_id, event.object.user_id, True)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_search"))
async def prev_search(event: GroupTypes.MessageEvent, user_service: IUserService,
                      state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    new_page = max(1, state.payload.get("page", 1) - 1)
    await state_dispenser.set(event.object.peer_id, AdminCAStates.SEARCH_RESULTS, **state.payload,
                              page=new_page)
    await _render_search(state, new_page, user_service, event.ctx_api, event.object.peer_id,
                         event.object.event_id, event.object.user_id, True)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("select_user"))
async def select_user(event: GroupTypes.MessageEvent, user_service: IUserService,
                      state_dispenser: BuiltinStateDispenser):
    admin_peer = event.object.peer_id
    admin_role = await user_service.get_user_role(event.object.user_id, Sources.VK)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    uid = event.object.payload.get("uid")
    target_user = await user_service.get_user(uid, Sources.VK)
    target_level = ROLE_HIERARCHY.get(target_user.role, 0)

    # 4.1 Проверка иерархии
    if admin_level <= target_level:
        return await event.ctx_api.messages.send(peer_id=admin_peer,
                                                 message="❌ Вы можете менять роль только пользователям с более низким рангом.",
                                                 random_id=0)

    text = f"ФИО: {target_user.surname} {target_user.name} {target_user.patronymic or ''}\nРегион: {target_user.region}\nТекущая роль: {target_user.role.value}"
    kb = Keyboard(inline=True).add(
        Callback("Поменять роль", {"cmd": "change_role", "uid": uid})).row().add(
        Callback("Назад", {"cmd": "back_to_menu"}))
    await state_dispenser.set(admin_peer, AdminCAStates.SELECT_USER, uid=uid)
    await event.ctx_api.messages.send(peer_id=admin_peer, message=text, keyboard=kb.get_json(),
                                      random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=admin_peer)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("change_role"))
async def change_role_menu(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser,
                           user_service: IUserService):
    uid = event.object.payload.get("uid")
    admin_role = await user_service.get_user_role(event.object.user_id, Sources.VK)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    kb = Keyboard(inline=True)
    # 4.1 Фильтрация доступных ролей (только ниже своей)
    for r in UserRole:
        if ROLE_HIERARCHY.get(r, 0) < admin_level:
            kb.add(Callback(r.value, {"cmd": "set_role", "uid": uid, "role": r.value}))
            kb.row()
    kb.add(Callback("Отмена", {"cmd": "cancel_role"}))
    await state_dispenser.set(event.object.peer_id, AdminCAStates.CHANGE_ROLE, uid=uid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message="Выберите новую роль (доступны только роли ниже вашей):",
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("set_role"))
async def set_role(event: GroupTypes.MessageEvent, user_service: IUserService, notification_service,
                   state_dispenser: BuiltinStateDispenser):
    admin_role = await user_service.get_user_role(event.object.user_id, Sources.VK)
    admin_level = ROLE_HIERARCHY.get(admin_role, 0)

    uid = event.object.payload.get("uid")
    new_role_str = event.object.payload.get("role")
    new_role = UserRole(new_role_str)

    if ROLE_HIERARCHY.get(new_role, 0) >= admin_level:
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                 message="❌ Ошибка: нельзя установить роль равную или выше вашей.",
                                                 random_id=0)

    await state_dispenser.delete(event.object.peer_id)
    await user_service.update_user_role(uid, Sources.VK, new_role)
    await notification_service.notify_user_vk(uid, f"Ваша роль изменена на: {new_role.value}")
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Роль пользователя {uid} успешно изменена на {new_role.value}",
                                      random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)
