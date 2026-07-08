import json
import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, GroupEventType, GroupTypes, Text
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.states import UserTaskStates
from src.application.utils import handle_cancel
from src.domain.entities.task import TaskType
from src.domain.exceptions import DomainError
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService
from src.domain.entities.user import Sources, UserGrade
from src.application.filters import CMDRule

logger = logging.getLogger(__name__)
router = BotLabeler()


def _build_task_keyboard(tasks, current_page: int, total_pages: int, prefix: str) -> str:
    """Генерирует клавиатуру с задачами и однострочной навигацией."""
    kb = Keyboard(inline=True)
    for t in tasks:
        title = f"#{t.id} {t.title[:30]}"
        kb.add(Callback(title, {"cmd": f"view_{prefix}", "tid": t.id}))
        kb.row()

    kb.row()  # Навигация всегда на последней строке
    if total_pages > 1:
        if current_page > 1:
            kb.add(Callback("⬅️ Назад", {"cmd": f"prev_{prefix}"}))
        if current_page < total_pages:
            kb.add(Callback("Вперёд ➡️", {"cmd": f"next_{prefix}"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))
    return kb.get_json()


async def _get_task_filter(user_service: IUserService, user_id: int) -> bool | None:
    u = await user_service.get_user(user_id, Sources.VK)
    return bool(u.is_member)


# ==================== ОНЛАЙН ЗАДАНИЯ ====================
@router.message(state=UserTaskStates.SELECT_TYPE, text=["Онлайн"])
async def online_list(message: Message, online_task_service: IOnlineTaskService, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    is_member_filter = await _get_task_filter(user_service, message.from_id)
    tasks, total_pages = await online_task_service.search_tasks(message.from_id, Sources.VK, page=1, is_member=is_member_filter)
    if not tasks:
        return await message.answer("Нет доступных онлайн действий. Загляните к нам снова — скоро "
                                    "будут новые.")
    kb = _build_task_keyboard(tasks, 1, total_pages, "online")
    await state_dispenser.set(message.from_id, UserTaskStates.ONLINE_LIST, page=1, total_pages=total_pages)
    await message.answer(f"Доступные действия (стр. 1/{total_pages}):", keyboard=kb)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_online"))
async def next_online(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.ONLINE_LIST): return
    new_page = state.payload.get("page", 1) + 1
    is_member_filter = await _get_task_filter(user_service, event.object.user_id)
    tasks, total_pages = await online_task_service.search_tasks(event.object.user_id, Sources.VK, page=new_page, is_member=is_member_filter)
    if not tasks:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="На этой странице действий нет.", random_id=0)
        return await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)
    kb = _build_task_keyboard(tasks, new_page, total_pages, "online")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_LIST, page=new_page, total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"Доступные действия ("
                                                                            f"стр. {new_page}/{total_pages}):", keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_online"))
async def prev_online(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.ONLINE_LIST): return
    new_page = max(1, state.payload.get("page", 1) - 1)
    is_member_filter = await _get_task_filter(user_service, event.object.user_id)
    tasks, total_pages = await online_task_service.search_tasks(event.object.user_id, Sources.VK, page=new_page, is_member=is_member_filter)
    kb = _build_task_keyboard(tasks, new_page, total_pages, "online")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_LIST, page=new_page, total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"Доступные действия ("
                                                                            f"стр. {new_page}/{total_pages}):", keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


# ==================== ОФЛАЙН ЗАДАНИЯ ====================
@router.message(state=UserTaskStates.SELECT_TYPE, text=["Офлайн"])
async def offline_list(message: Message, offline_task_service: IOfflineTaskService,
                       user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    if u.grade not in (UserGrade.AGITATOR, UserGrade.RESERVE):
        kb = Keyboard(one_time=True).add(Text("На главную"))
        return await message.answer(
            "Этот тип действий открывается при достижении ранга 'Агитатор'. Для его прохождения "
            "необходимо пройти обучене",
            keyboard=kb.get_json())

    is_member_filter = await _get_task_filter(user_service, message.from_id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1,
                                                                     is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]

    if not tasks:
        return await message.answer("Нет действий в вашем регионе. Загляните к нам снова — скоро "
                                    "будут новые.")
    kb = _build_task_keyboard(tasks, 1, total_pages, "offline")
    await state_dispenser.set(message.from_id, UserTaskStates.OFFLINE_LIST, page=1,
                              total_pages=total_pages)
    await message.answer(f"Действий в вашем регионе (стр. 1/{total_pages}):", keyboard=kb)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_offline"))
async def next_offline(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                       user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.OFFLINE_LIST): return
    new_page = state.payload.get("page", 1) + 1
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    is_member_filter = await _get_task_filter(user_service, event.object.user_id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=new_page,
                                                                     is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]
    if not tasks:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message="Больше действий в вашем регионе нет.",
                                          random_id=0)
        return await event.ctx_api.messages.send_message_event_answer(
            event_id=event.object.event_id, user_id=event.object.user_id,
            peer_id=event.object.peer_id)
    kb = _build_task_keyboard(tasks, new_page, total_pages, "offline")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_LIST, page=new_page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Действия в вашем регионе (стр. {new_page}"
                                              f"/{total_pages}):",
                                      keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_offline"))
async def prev_offline(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                       user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.OFFLINE_LIST): return
    new_page = max(1, state.payload.get("page", 1) - 1)
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    is_member_filter = await _get_task_filter(user_service, event.object.user_id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=new_page,
                                                                     is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]
    kb = _build_task_keyboard(tasks, new_page, total_pages, "offline")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_LIST, page=new_page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Действия в вашем регионе (стр. {new_page}"
                                              f"/{total_pages}):",
                                      keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)

# ==================== ОБЩИЕ ХЕНДЛЕРЫ ====================
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_online"))
async def view_online(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService,
                      state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    task = await online_task_service.get_task(tid)
    if not task:
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                 message="Ошибка: действие не найдено", random_id=0)
    kb = Keyboard(inline=True)
    if task.type == TaskType.OTHER:
        kb.add(Callback("📤 Отправить подтверждение", {"cmd": "submit_proof_online", "tid": tid}))
    else:
        kb.add(Callback("✅ Проверить", {"cmd": "check_online", "tid": tid}))
    kb.row().add(Callback("Назад к списку", {"cmd": "back_online_list"}))

    text = (f"📋 {task.title}\n"
            f"📝 {task.description}\n"
            f"📌 Тип: {task.type.value}\n"
            f"🏆 Вознаграждение: {task.reward} очков\n")
    if task.url:
        text += f"🔗 Ссылка: {task.url}"

    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_VIEW, tid=tid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("submit_proof_online"))
async def submit_proof_online(event: GroupTypes.MessageEvent,
                              state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_AWAIT_PROOF, tid=tid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message="Отправьте текст или ссылку, подтверждающую "
                                              "выполнение действия:",
                                      random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.message(state=UserTaskStates.ONLINE_AWAIT_PROOF)
async def receive_proof(message: Message, state_dispenser: BuiltinStateDispenser,
                        user_service: IUserService):
    if await handle_cancel(message, state_dispenser, user_service): return

    state = await state_dispenser.get(message.from_id)
    tid = state.payload.get("tid")

    cm_id = message.conversation_message_id

    await state_dispenser.set(message.from_id, UserTaskStates.ONLINE_CONFIRM_PROOF,
                              tid=tid, cm_id=cm_id)

    kb = Keyboard(inline=True)
    kb.add(Callback("✅ Да, отправить", {"cmd": "confirm_submit_online"})).row()
    kb.add(Callback("❌ Нет, отмена", {"cmd": "cancel_submit_online"}))

    await message.answer("Вы уверены, что хотите отправить это сообщение на проверку?",
                         keyboard=kb.get_json())


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("cancel_submit_online"))
async def cancel_submit_online(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser, user_service: IUserService):
    await state_dispenser.delete(event.object.peer_id)
    role = await user_service.get_user_role(event.object.user_id, Sources.VK)
    from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
    kb = get_role_menu_keyboard(role)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Главное меню", keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("confirm_submit_online"))
async def confirm_submit_online(event: GroupTypes.MessageEvent,
                                state_dispenser: BuiltinStateDispenser,
                                online_task_service: IOnlineTaskService, user_service: IUserService,
                                verify_chat_id: int):
    state = await state_dispenser.get(event.object.peer_id)
    tid = state.payload.get("tid")
    uid = event.object.user_id
    source = Sources.VK
    cm_id = state.payload.get("cm_id")

    try:
        await online_task_service.submit_tg_online_task(uid, source, tid)
        task = await online_task_service.get_task(tid)
        user = await user_service.get_user(uid, source)

        # 1. ПЕРЕСЫЛАЕМ сообщение пользователя в чат проверки (сохраняет текст, фото, документы и т.д.)
        forward_data = json.dumps({
            "peer_id": event.object.peer_id,
            "conversation_message_ids": [cm_id]
        })

        await event.ctx_api.messages.send(
            peer_id=verify_chat_id,
            message=f"📋 Онлайн действие #{task.id} на проверку",
            forward=forward_data,
            random_id=0
        )

        # 2. Отправляем информацию о задании с кнопками "ПОД НИМ" (следующим сообщением в чате)
        info_text = (
            f"#in_progress\n"
            f"👤 Пользователь: {user.surname} {user.name} (ID: {uid}, VK)\n"
            f"📌 Тип: {task.type.value}\n"
            f"🏆 Вознаграждение: {task.reward} очков\n"
        )
        if task.url:
            info_text += f"🔗 Ссылка: {task.url}\n"

        kb = Keyboard(inline=True)
        kb.add(Callback("✅ Принять", {"cmd": "vk_verify_accept", "uid": uid, "tid": tid})).row()
        kb.add(Callback("❌ Отклонить", {"cmd": "vk_verify_decline", "uid": uid, "tid": tid}))

        await event.ctx_api.messages.send(
            peer_id=verify_chat_id,
            message=info_text,
            keyboard=kb.get_json(),
            random_id=0
        )

        # Уведомляем пользователя и очищаем стейт
        await state_dispenser.delete(event.object.peer_id)
        role = await user_service.get_user_role(uid, source)
        from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="✅ Действие отправлено на проверку. Ожидайте решения администратора.",
            keyboard=get_role_menu_keyboard(role),
            random_id=0
        )
    except Exception as e:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"Ошибка: {e}",
                                          random_id=0)

    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_offline"))
async def view_offline(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                       state_dispenser: BuiltinStateDispenser, user_service: IUserService):
    tid = event.object.payload["tid"]
    task = await offline_task_service.get_task(tid)
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    active_tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, 1)

    period_str = f"{task.start_date.strftime('%d.%m.%Y')} - {task.end_date.strftime('%d.%m.%Y')}"
    text = (f"📋 {task.title}\n"
            f"📅 Период: {period_str}\n"
            f"📝 {task.description}\n"
            f"📍 {task.location}\n"
            f"📞 {task.contacts}\n"
            f"🏆 {task.reward} очков")
    kb = Keyboard(inline=True)
    kb.add(Callback("Принять", {"cmd": "accept_offline", "tid": tid}))
    kb.row().add(Callback("Назад к списку", {"cmd": "back_offline_list"}))

    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_VIEW, tid=tid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("check_online"))
async def check_online(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService,
                       notification_service: INotificationService):
    tid = event.object.payload["tid"]
    try:
        await online_task_service.check_task(event.object.user_id, Sources.VK, tid)
        task = await online_task_service.get_task(tid)
        await notification_service.notify_user(event.object.peer_id, Sources.VK,
                                                  f"✅ Действие #{tid} принято. Начислено"
                                                  f" {task.reward} очков.")
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message=f"Вы успешно выполнили действие! +{task.reward} "
                                                  f"очков",
                                          random_id=0)
    except Exception as e:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=str(e), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("accept_offline"))
async def accept_offline(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService):
    tid = event.object.payload["tid"]
    try:
        await offline_task_service.accept_offline_task(event.object.user_id, Sources.VK, tid)
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message="✅ Действие принято. Свяжитесь с местным "
                                                  "отделением по контактам в описании.",
                                          random_id=0)
        await notification_service.notify_user(event.object.peer_id, Sources.VK,
                                                  f"Вы взяли офлайн действие #{tid}. Ожидает "
                                                  f"проверки.")
    except DomainError as e:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=str(e), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_online_list"))
async def back_online_list(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    page = state.payload.get("page", 1) if state else 1
    is_member_filter = await _get_task_filter(user_service, event.object.user_id)
    tasks, total_pages = await online_task_service.search_tasks(event.object.user_id, Sources.VK, page=page, is_member=is_member_filter)
    if not tasks and total_pages > 0:
        tasks, total_pages = await online_task_service.search_tasks(event.object.user_id, Sources.VK, page=1, is_member=is_member_filter)
        page = 1
    kb = _build_task_keyboard(tasks, page, total_pages, "online")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_LIST, page=page, total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"Доступные действия ("
                                                                            f"стр."
                                                                            f" {page}/{total_pages}):", keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_offline_list"))
async def back_offline_list(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    page = state.payload.get("page", 1) if state else 1
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    is_member_filter = await _get_task_filter(user_service, event.object.user_id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=page, is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]
    if not tasks and total_pages > 1:
        all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1, is_member=is_member_filter)
        tasks = [t for t in all_tasks if t.region == u.region]
        page = 1
    kb = _build_task_keyboard(tasks, page, total_pages, "offline")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_LIST, page=page, total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"Действия в регионе ("
                                                                            f"стр. {page}/{total_pages}):", keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_to_menu"))
async def back_to_menu(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(event.object.peer_id)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Главное меню",
                                      random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)