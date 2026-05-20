import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, Text, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import UserTaskStates
from src.domain.exceptions import DomainError
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService
from src.domain.entities.user import Sources
from src.application.filters import CMDRule

logger = logging.getLogger(__name__)
router = BotLabeler()


@router.message(state=UserTaskStates.SELECT_TYPE, text=["Онлайн"])
async def online_list(message: Message, online_task_service: IOnlineTaskService,
                      state_dispenser: BuiltinStateDispenser):
    tasks, pages = await online_task_service.search_tasks(message.from_id, Sources.VK, page=1)
    if not tasks: return await message.answer("Нет доступных онлайн заданий.")
    kb = Keyboard(inline=True)
    for t in tasks:
        kb.add(Callback(f"#{t.id} {t.type.value}", {"cmd": "view_online", "tid": t.id}))
        kb.row()
    await state_dispenser.set(message.from_id, UserTaskStates.ONLINE_LIST)
    await message.answer("Доступные задания:", keyboard=kb.get_json())


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_online"))
async def view_online(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService,
                      state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    task = await online_task_service.get_task(tid)
    if not task: return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                          message="Ошибка", random_id=0)

    kb = Keyboard(inline=True)
    kb.add(Callback("Проверить", {"cmd": "check_online", "tid": tid}))
    kb.row().add(Callback("Назад", {"cmd": "back_online"}))

    text = f"Задание #{task.id}\nТип: {task.type.value}\nНаграда: {task.reward}\nДлительность: {task.duration} дн."
    await state_dispenser.set(event.object.peer_id, UserTaskStates.ONLINE_VIEW, tid=tid)
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


@router.message(state=UserTaskStates.SELECT_TYPE, text=["Офлайн"])
async def offline_list(message: Message, offline_task_service: IOfflineTaskService,
                       user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    tasks, _ = await offline_task_service.search_tasks(u.id, u.source, page=1)
    tasks = [t for t in tasks if t.region == u.region]
    if not tasks: return await message.answer("Нет заданий в вашем регионе.")
    kb = Keyboard(inline=True)
    for t in tasks:
        kb.add(Callback(f"#{t.id} {t.title[:15]}", {"cmd": "view_offline", "tid": t.id}))
        kb.row()
    await state_dispenser.set(message.from_id, UserTaskStates.OFFLINE_LIST)
    await message.answer("Задания в регионе:", keyboard=kb.get_json())


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
        await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                               user_id=event.object.user_id,
                                                               peer_id=event.object.peer_id)
        return

    text = f"📋 {task.title}\n📝 {task.description}\n📍 {task.location}\n📞 {task.contacts}\n💰 {task.reward} баллов"
    kb = Keyboard(inline=True)
    kb.add(Callback("Принять", {"cmd": "accept_offline", "tid": tid}))
    kb.row().add(Callback("Назад", {"cmd": "back_offline"}))  # ИСПРАВЛЕНО: добавлен payload

    await state_dispenser.set(event.object.peer_id, UserTaskStates.OFFLINE_VIEW, tid=tid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("accept_offline"))
async def accept_offline(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService):
    tid = event.object.payload["tid"]
    try:
        # Вся логика проверок (существование, лимит 2 задач, дубликаты) уже внутри сервиса
        await offline_task_service.accept_offline_task(event.object.user_id, Sources.VK, tid)

        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="✅ Задача принята. Свяжитесь с местным отделением по контактам в описании.",
            random_id=0
        )
        await notification_service.notify_user_vk(event.object.peer_id,
                                                  f"Вы взяли офлайн задачу #{tid}. Ожидает проверки.")
    except DomainError as e:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=str(e), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_online"))
async def back_online(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(event.object.peer_id)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Меню", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_offline"))
async def back_offline(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(event.object.peer_id)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Меню", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)
