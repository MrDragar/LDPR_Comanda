import logging

from vkbottle import BuiltinStateDispenser, Callback, Keyboard, Text
from vkbottle.bot import BotLabeler, Message
from vkbottle_types import GroupTypes
from vkbottle_types.events import GroupEventType

from src.application.filters import CMDRule
from src.application.keyboards.menu_keyboard import (
    get_role_entry_keyboard,
    get_role_tools_keyboard,
    get_staff_ca_headliners_keyboard,
    get_staff_ca_shop_keyboard,
    get_staff_ca_tasks_keyboard,
    get_user_menu_keyboard,
)
from src.application.states import UserTaskStates
from src.domain.entities import Sources
from src.domain.entities.task import TaskStatus
from src.domain.entities.user import UserRole
from src.services.interfaces import IUserService

logger = logging.getLogger(__name__)
router = BotLabeler()


async def _get_user_role(message: Message, user_service: IUserService) -> UserRole | None:
    try:
        return await user_service.get_user_role(message.from_id, Sources.VK)
    except Exception as e:
        logger.error(f"Failed to get user role for menu display: {e}")
        return None


@router.message(text=[
    "Меню",
    "Назад",
    "На главную",
    "Вернуться на главную страницу",
    "РњРµРЅСЋ",
    "РќР°Р·Р°Рґ",
    "РќР° РіР»Р°РІРЅСѓСЋ",
    "Р’РµСЂРЅСѓС‚СЊСЃСЏ РЅР° РіР»Р°РІРЅСѓСЋ СЃС‚СЂР°РЅРёС†Сѓ",
])
async def show_menu(message: Message, user_service: IUserService) -> None:
    role = await _get_user_role(message, user_service)
    if role is None or role == UserRole.USER:
        await message.answer("Пользовательский интерфейс:", keyboard=get_user_menu_keyboard())
        return
    await message.answer("Выберите интерфейс:", keyboard=get_role_entry_keyboard(role))


@router.message(text=["Пользователь", "РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ"])
async def show_user_interface(message: Message) -> None:
    await message.answer("Пользовательский интерфейс:", keyboard=get_user_menu_keyboard())


@router.message(text=[
    "Сотрудник ЦА",
    "Координатор РО",
    "Сотрудник РО",
    "Хэдлайнер",
    "РЎРѕС‚СЂСѓРґРЅРёРє Р¦Рђ",
    "РљРѕРѕСЂРґРёРЅР°С‚РѕСЂ Р Рћ",
    "РЎРѕС‚СЂСѓРґРЅРёРє Р Рћ",
    "РҐСЌРґР»Р°Р№РЅРµСЂ",
])
async def show_role_interface(message: Message, user_service: IUserService) -> None:
    role = await _get_user_role(message, user_service)
    if role is None or role == UserRole.USER:
        await message.answer("Этот интерфейс недоступен для вашей роли.")
        return

    if message.text not in (role.value,):
        legacy_role_values = {
            UserRole.STAFF_CA: ["РЎРѕС‚СЂСѓРґРЅРёРє Р¦Рђ"],
            UserRole.COORDINATOR_RO: ["РљРѕРѕСЂРґРёРЅР°С‚РѕСЂ Р Рћ"],
            UserRole.STAFF_RO: ["РЎРѕС‚СЂСѓРґРЅРёРє Р Рћ"],
            UserRole.HEADLINER: ["РҐСЌРґР»Р°Р№РЅРµСЂ"],
        }
        if message.text not in legacy_role_values.get(role, []):
            await message.answer("Этот интерфейс недоступен для вашей роли.")
            return

    await message.answer(f"Интерфейс роли: {role.value}", keyboard=get_role_tools_keyboard(role))


async def _require_staff_ca(message: Message, user_service: IUserService) -> bool:
    role = await _get_user_role(message, user_service)
    if role != UserRole.STAFF_CA:
        await message.answer("Этот раздел доступен только сотруднику ЦА.")
        return False
    return True


@router.message(text=["Магазин ЦА"])
async def show_staff_ca_shop(message: Message, user_service: IUserService) -> None:
    if not await _require_staff_ca(message, user_service):
        return
    await message.answer("Раздел: магазин", keyboard=get_staff_ca_shop_keyboard())


@router.message(text=["Задачи"])
async def show_staff_ca_tasks(message: Message, user_service: IUserService) -> None:
    if not await _require_staff_ca(message, user_service):
        return
    await message.answer("Раздел: задачи", keyboard=get_staff_ca_tasks_keyboard())


@router.message(text=["Хэдлайнеры"])
async def show_staff_ca_headliners(message: Message, user_service: IUserService) -> None:
    if not await _require_staff_ca(message, user_service):
        return
    await message.answer("Раздел: хэдлайнеры", keyboard=get_staff_ca_headliners_keyboard())


@router.message(text=["Назад к роли"])
async def back_to_role_interface(message: Message, user_service: IUserService) -> None:
    role = await _get_user_role(message, user_service)
    if role is None or role == UserRole.USER:
        await message.answer("Пользовательский интерфейс:", keyboard=get_user_menu_keyboard())
        return
    await message.answer(f"Интерфейс роли: {role.value}", keyboard=get_role_tools_keyboard(role))


@router.message(text=["Выполнить задание", "Р’С‹РїРѕР»РЅРёС‚СЊ Р·Р°РґР°РЅРёРµ"])
async def select_task_type(message: Message, state_dispenser):
    kb = Keyboard(inline=True).add(Text("Онлайн")).add(Text("Офлайн"))
    await state_dispenser.set(message.from_id, UserTaskStates.SELECT_TYPE)
    await message.answer("Выберите тип задания:", keyboard=kb.get_json())


@router.message(text=["Мои задания", "РњРѕРё Р·Р°РґР°РЅРёСЏ"])
async def my_tasks(message: Message, offline_task_service, user_service,
                   state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        return await message.answer("У вас нет активных заданий.")

    kb = Keyboard(inline=True)
    for t in tasks:
        kb.add(Callback(
            f"#{t.task.id} {t.task.title} ({t.status.value})",
            {"cmd": "view_my_task", "tid": t.task.id},
        ))
        kb.row()
    await state_dispenser.set(message.from_id, UserTaskStates.MY_TASKS)
    await message.answer("Ваши задания:", keyboard=kb.get_json())


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_my_task"))
async def view_my_task(event: GroupTypes.MessageEvent, offline_task_service, user_service,
                       state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    task = await offline_task_service.get_task(tid)
    if not task:
        return await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="Ошибка: задание не найдено",
            random_id=0,
        )

    user_tasks, _ = await offline_task_service.get_user_tasks(
        event.object.user_id,
        Sources.VK,
        page=1,
    )
    accepted = next((t for t in user_tasks if t.task and t.task.id == tid), None)

    text = (
        f"Задание: {task.title}\n"
        f"Описание: {task.description}\n"
        f"Место: {task.location}\n"
        f"Контакты: {task.contacts}\n"
        f"Награда: {task.reward} баллов"
    )

    kb = Keyboard(inline=True)
    if accepted and accepted.status == TaskStatus.IN_PROGRESS:
        kb.add(Callback("Отменить задание", {"cmd": "cancel_my_task", "tid": tid}))
        kb.row()
    kb.add(Callback("Назад", {"cmd": "back_to_my_tasks"}))

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=text,
        keyboard=kb.get_json(),
        random_id=0,
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id,
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("cancel_my_task"))
async def cancel_my_task(event: GroupTypes.MessageEvent, offline_task_service, notification_service,
                         user_service):
    tid = event.object.payload["tid"]
    try:
        await offline_task_service.cancel_task(event.object.user_id, Sources.VK, tid)
        await notification_service.notify_user_vk(
            event.object.peer_id,
            f"Задание #{tid} отменено.",
        )
        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message=f"Задание #{tid} успешно отменено.",
            random_id=0,
        )
    except Exception as e:
        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message=f"Ошибка при отмене: {e}",
            random_id=0,
        )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id,
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_to_my_tasks"))
async def back_to_my_tasks(event: GroupTypes.MessageEvent, offline_task_service, user_service,
                           state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        return await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="У вас нет активных заданий.",
            random_id=0,
        )

    kb = Keyboard(inline=True)
    for t in tasks:
        kb.add(Callback(
            f"#{t.task.id} {t.task.title} ({t.status.value})",
            {"cmd": "view_my_task", "tid": t.task.id},
        ))
        kb.row()
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message="Ваши задания:",
        keyboard=kb.get_json(),
        random_id=0,
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id,
    )
