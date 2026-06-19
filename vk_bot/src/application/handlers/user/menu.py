import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text, BuiltinStateDispenser, Callback
from vkbottle_types import GroupTypes
from vkbottle_types.events import GroupEventType

from src.application.filters import CMDRule
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.states import UserTaskStates
from src.domain.entities import Sources
from src.domain.entities.task import TaskStatus
from src.services.interfaces import IUserService

logger = logging.getLogger(__name__)
router = BotLabeler()


@router.message(text=["Меню", "На главную", "Вернуться на главную страницу"])
async def show_menu(message: Message, user_service: IUserService) -> None:
    try:
        role = await user_service.get_user_role(message.from_id, Sources.VK)
    except Exception as e:
        logger.error(f"Failed to get user role for menu display: {e}")
        role = None
    await message.answer("Главное меню:", keyboard=get_role_menu_keyboard(role))


@router.message(text=["Выполнить задание"])
async def select_task_type(message: Message, state_dispenser):
    kb = Keyboard(inline=True).add(Text("Онлайн")).add(Text("Офлайн"))
    await state_dispenser.set(message.from_id, UserTaskStates.SELECT_TYPE)
    await message.answer("Выберите тип задания:", keyboard=kb.get_json())


@router.message(text=["Мои задания"])
async def my_tasks(message: Message, offline_task_service, user_service,
                   state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        return await message.answer("У вас нет активных заданий.")

    kb = Keyboard(inline=True)
    for t in tasks:
        # Используем Callback для навигации к деталям задачи
        kb.add(Callback(f"#{t.task.id} {t.task.title} ({t.status.value})",
                        {"cmd": "view_my_task", "tid": t.task.id}))
        kb.row()
    await state_dispenser.set(message.from_id, UserTaskStates.MY_TASKS)
    await message.answer("Ваши задания:", keyboard=kb.get_json())


# Новый хендлер: просмотр задачи из "Моих заданий" с кнопкой отмены
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_my_task"))
async def view_my_task(event: GroupTypes.MessageEvent, offline_task_service, user_service,
                       state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    task = await offline_task_service.get_task(tid)
    if not task:
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                 message="Ошибка: задание не найдено", random_id=0)

    # Получаем статус принятой задачи
    user_tasks, _ = await offline_task_service.get_user_tasks(event.object.user_id, Sources.VK,
                                                              page=1)
    accepted = next((t for t in user_tasks if t.task and t.task.id == tid), None)

    text = f"📋 {task.title}\n📝 {task.description}\n📍 {task.location}\n📞 {task.contacts}\n💰 {task.reward} баллов"

    kb = Keyboard(inline=True)
    if accepted and accepted.status == TaskStatus.IN_PROGRESS:
        kb.add(Callback("❌ Отменить задание", {"cmd": "cancel_my_task", "tid": tid}))
        kb.row()
    kb.add(Callback("🔙 Назад", {"cmd": "back_to_my_tasks"}))

    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("cancel_my_task"))
async def cancel_my_task(event: GroupTypes.MessageEvent, offline_task_service, notification_service,
                         user_service):
    tid = event.object.payload["tid"]
    try:
        await offline_task_service.cancel_task(event.object.user_id, Sources.VK, tid)
        await notification_service.notify_user_vk(event.object.peer_id, f"Задание #{tid} отменено.")
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message=f"✅ Задание #{tid} успешно отменено.",
                                          random_id=0)
    except Exception as e:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                          message=f"Ошибка при отмене: {e}", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


# Возврат к списку моих заданий
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("back_to_my_tasks"))
async def back_to_my_tasks(event: GroupTypes.MessageEvent, offline_task_service, user_service,
                           state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                 message="У вас нет активных заданий.", random_id=0)

    kb = Keyboard(inline=True)
    for t in tasks:
        kb.add(Callback(f"#{t.task.id} {t.task.title} ({t.status.value})",
                        {"cmd": "view_my_task", "tid": t.task.id}))
        kb.row()
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Ваши задания:",
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)