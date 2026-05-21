import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import UserTaskStates
from src.domain.exceptions import DomainError
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService
from src.domain.entities.user import Sources
from src.application.filters import CMDRule

logger = logging.getLogger(__name__)
router = BotLabeler()


def _build_task_keyboard(tasks, current_page: int, total_pages: int, prefix: str) -> str:
    """Вспомогательная функция для генерации клавиатуры с пагинацией."""
    kb = Keyboard(inline=True)
    for t in tasks:
        title = f"#{t.id} {t.type.value}" if hasattr(t, "type") else f"#{t.id} {t.title[:15]}"
        kb.add(Callback(title, {"cmd": f"view_{prefix}", "tid": t.id}))
        kb.row()

    if total_pages > 1:
        kb.row()
        if current_page > 1:
            kb.add(Callback("⬅️ Назад", {"cmd": f"prev_{prefix}"}))
        if current_page < total_pages:
            kb.add(Callback("Вперёд ➡️", {"cmd": f"next_{prefix}"}))
        kb.row()

    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))
    return kb.get_json()


# ==================== ОНЛАЙН ЗАДАНИЯ ====================

@router.message(state=UserTaskStates.SELECT_TYPE, text=["Онлайн"])
async def online_list(message: Message, online_task_service: IOnlineTaskService,
                      state_dispenser: BuiltinStateDispenser):
    tasks, total_pages = await online_task_service.search_tasks(message.from_id, Sources.VK, page=1)
    if not tasks:
        return await message.answer("Нет доступных онлайн заданий.")

    kb = _build_task_keyboard(tasks, 1, total_pages, "online")
    await state_dispenser.set(message.from_id, UserTaskStates.ONLINE_LIST, page=1,
                              total_pages=total_pages)
    await message.answer(f"Доступные задания (стр. 1/{total_pages}):", keyboard=kb)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_online"))
async def next_online(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService,
                      state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.ONLINE_LIST):
        return

    new_page = state.payload.get("page", 1) + 1
    tasks, total_pages = await online_task_service.search_tasks(event.object.user_id, Sources.VK,
                                                                page=new_page)

    if not tasks:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message="На этой странице заданий нет.", random_id=0)
        return await event.ctx_api.messages.send_message_event_answer(
            event_id=event.object.event_id, user_id=event.object.user_id,
            peer_id=event.object.peer_id)

    kb = _build_task_keyboard(tasks, new_page, total_pages, "online")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_LIST, page=new_page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Доступные задания (стр. {new_page}/{total_pages}):",
                                      keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_online"))
async def prev_online(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService,
                      state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.ONLINE_LIST):
        return

    new_page = max(1, state.payload.get("page", 1) - 1)
    tasks, total_pages = await online_task_service.search_tasks(event.object.user_id, Sources.VK,
                                                                page=new_page)

    kb = _build_task_keyboard(tasks, new_page, total_pages, "online")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_LIST, page=new_page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Доступные задания (стр. {new_page}/{total_pages}):",
                                      keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


# ==================== ОФЛАЙН ЗАДАНИЯ ====================

@router.message(state=UserTaskStates.SELECT_TYPE, text=["Офлайн"])
async def offline_list(message: Message, offline_task_service: IOfflineTaskService,
                       user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1)
    tasks = [t for t in all_tasks if t.region == u.region]

    if not tasks:
        return await message.answer("Нет заданий в вашем регионе.")

    # Примечание: фильтрация по региону на клиенте может делать total_pages неточным.
    # Для production рекомендуется добавить фильтр по region прямо в SQL-запрос репозитория.
    kb = _build_task_keyboard(tasks, 1, total_pages, "offline")
    await state_dispenser.set(message.from_id, UserTaskStates.OFFLINE_LIST, page=1,
                              total_pages=total_pages)
    await message.answer(f"Задания в вашем регионе (стр. 1/{total_pages}):", keyboard=kb)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_offline"))
async def next_offline(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                       user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.OFFLINE_LIST):
        return

    new_page = state.payload.get("page", 1) + 1
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=new_page)
    tasks = [t for t in all_tasks if t.region == u.region]

    if not tasks:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message="Больше заданий в вашем регионе нет.",
                                          random_id=0)
        return await event.ctx_api.messages.send_message_event_answer(
            event_id=event.object.event_id, user_id=event.object.user_id,
            peer_id=event.object.peer_id)

    kb = _build_task_keyboard(tasks, new_page, total_pages, "offline")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_LIST, page=new_page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Задания в вашем регионе (стр. {new_page}/{total_pages}):",
                                      keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_offline"))
async def prev_offline(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                       user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(UserTaskStates.OFFLINE_LIST):
        return

    new_page = max(1, state.payload.get("page", 1) - 1)
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=new_page)
    tasks = [t for t in all_tasks if t.region == u.region]

    kb = _build_task_keyboard(tasks, new_page, total_pages, "offline")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_LIST, page=new_page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Задания в вашем регионе (стр. {new_page}/{total_pages}):",
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
                                                 message="Ошибка: задание не найдено", random_id=0)

    kb = Keyboard(inline=True)
    kb.add(Callback("Проверить", {"cmd": "check_online", "tid": tid}))
    kb.row().add(Callback("Назад к списку", {"cmd": "back_online_list"}))

    text = f"📋 Задание #{task.id}\n📌 Тип: {task.type.value}\n💰 Награда: {task.reward}\n⏱ Длительность: {task.duration} дн."
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_VIEW, tid=tid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text,
                                      keyboard=kb.get_json(), random_id=0)
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

    if len(active_tasks) >= 2:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message="❌ Нельзя взять более 2 активных офлайн задач одновременно.",
                                          random_id=0)
        return await event.ctx_api.messages.send_message_event_answer(
            event_id=event.object.event_id, user_id=event.object.user_id,
            peer_id=event.object.peer_id)

    text = f"📋 {task.title}\n📝 {task.description}\n📍 {task.location}\n📞 {task.contacts}\n💰 {task.reward} баллов"
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
        await notification_service.notify_user_vk(event.object.peer_id,
                                                  f"✅ Задание #{tid} принято. Начислено {task.reward} баллов.")
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message=f"Вы успешно выполнили задание! +{task.reward} баллов",
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
                                          message="✅ Задача принята. Свяжитесь с местным отделением по контактам в описании.",
                                          random_id=0)
        await notification_service.notify_user_vk(event.object.peer_id,
                                                  f"Вы взяли офлайн задачу #{tid}. Ожидает проверки.")
    except DomainError as e:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=str(e), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("back_online_list"))
async def back_online_list(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService,
                           state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    page = state.payload.get("page", 1) if state else 1
    tasks, total_pages = await online_task_service.search_tasks(event.object.user_id, Sources.VK,
                                                                page=page)

    if not tasks and total_pages > 0:
        tasks, total_pages = await online_task_service.search_tasks(event.object.user_id,
                                                                    Sources.VK, page=1)
        page = 1

    kb = _build_task_keyboard(tasks, page, total_pages, "online")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_LIST, page=page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Доступные задания (стр. {page}/{total_pages}):",
                                      keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("back_offline_list"))
async def back_offline_list(event: GroupTypes.MessageEvent,
                            offline_task_service: IOfflineTaskService,
                            user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    page = state.payload.get("page", 1) if state else 1
    u = await user_service.get_user(event.object.user_id, Sources.VK)

    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=page)
    tasks = [t for t in all_tasks if t.region == u.region]

    if not tasks and total_pages > 1:
        all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1)
        tasks = [t for t in all_tasks if t.region == u.region]
        page = 1

    kb = _build_task_keyboard(tasks, page, total_pages, "offline")
    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_LIST, page=page,
                              total_pages=total_pages)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Задания в регионе (стр. {page}/{total_pages}):",
                                      keyboard=kb, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_to_menu"))
async def back_to_menu(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(event.object.peer_id)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Главное меню",
                                      random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)