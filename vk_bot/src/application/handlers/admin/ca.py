import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback
from vkbottle.dispatch import BuiltinStateDispenser
from vkbottle_types import GroupTypes
from vkbottle_types.events import GroupEventType

from src.application.states import AdminCAStates
from src.domain.entities.user import UserRole, Sources
from src.application.filters import check_role, CMDRule
from src.services.interfaces import IUserService

logger = logging.getLogger(__name__)
router = BotLabeler()
ALLOWED_ROLES = [UserRole.STAFF_CA]


@router.message(text=["Управление пользователями"])
async def start_search(message: Message, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    if not await check_role(user_service, message.from_id, ALLOWED_ROLES):
        return await message.answer("Недостаточно прав")
    await message.answer("Введите фамилию пользователя для поиска:")
    await state_dispenser.set(message.from_id, AdminCAStates.SEARCH_FIO, query_type="fio")


@router.message(state=AdminCAStates.SEARCH_FIO)
async def search_fio(message: Message, user_service: IUserService,
                     state_dispenser: BuiltinStateDispenser):
    parts = message.text.strip().split()
    surname = parts[0] if len(parts) > 0 else ""
    name = parts[1] if len(parts) > 1 else ""
    patronymic = parts[2] if len(parts) > 2 else None

    if len(surname) < 2:
        return await message.answer("Введите минимум 2 символа фамилии")

    users = await user_service.search_users_by_fio(surname, name, patronymic, skip=0, limit=5)
    if not users:
        return await message.answer("Пользователи не найдены. Попробуйте снова.")

    kb = Keyboard(inline=True)
    for u in users:
        kb.add(Callback(f"{u.surname} {u.name} - {u.role.value}",
                        {"cmd": "select_user", "uid": u.id, "page": 0}))
        kb.row()
    kb.add(Callback("Назад", {"cmd": "back_to_menu"}))

    await state_dispenser.set(message.from_id, AdminCAStates.SEARCH_RESULTS,
                              query=f"{surname} {name or ''} {patronymic or ''}")
    await message.answer("Выберите пользователя:", keyboard=kb.get_json())


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("select_user"))
async def select_user(event: GroupTypes.MessageEvent, user_service: IUserService,
                      state_dispenser: BuiltinStateDispenser):
    uid = event.object.payload.get("uid")
    u = await user_service.get_user(uid, Sources.VK)
    text = (f"ФИО: {u.surname} {u.name} {u.patronymic or ''}\n"
            f"Регион: {u.region}\nТекущая роль: {u.role.value}")
    kb = Keyboard(inline=True).add(Callback("Поменять роль", {"cmd": "change_role", "uid": uid}))
    kb.row().add(Callback("Назад", {"cmd": "back_to_menu"}))

    await state_dispenser.set(event.object.peer_id, AdminCAStates.SELECT_USER, uid=uid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("change_role"))
async def change_role_menu(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    uid = event.object.payload.get("uid")
    kb = Keyboard(inline=True)
    for r in UserRole:
        kb.add(Callback(r.value, {"cmd": "set_role", "uid": uid, "role": r.value}))
        kb.row()
    kb.add(Callback("Отмена", {"cmd": "cancel_role"}))

    await state_dispenser.set(event.object.peer_id, AdminCAStates.CHANGE_ROLE, uid=uid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Выберите новую роль:",
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("set_role"))
async def set_role(event: GroupTypes.MessageEvent, user_service: IUserService, notification_service,
                   state_dispenser: BuiltinStateDispenser):
    uid = event.object.payload.get("uid")
    new_role_str = event.object.payload.get("role")
    new_role = UserRole(new_role_str)
    await state_dispenser.delete(event.object.peer_id)
    await user_service.update_user_role(uid, Sources.VK, new_role)
    await notification_service.notify_user_vk(uid, f"Ваша роль изменена на: {new_role.value}")
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Роль пользователя {uid} успешно изменена на {new_role.value}",
                                      random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)