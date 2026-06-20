from maxapi import F, Router
from maxapi.context import MemoryContext
from maxapi.types import CallbackButton, MessageButton, MessageCallback, MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.states import UserTaskStates
from src.domain.entities import Sources
from src.domain.entities.user import UserGrade
from src.domain.exceptions import DomainError
from src.services.interfaces import INotificationService, IOfflineTaskService, IOnlineTaskService, IUserService

router = Router()


def _uid(event) -> int:
    if hasattr(event, "from_user") and event.from_user:
        return event.from_user.user_id
    return event.callback.user.user_id


def _button_keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*[CallbackButton(text=text, payload=payload) for text, payload in row])
    return builder


async def _main_menu(event, user_service: IUserService, user_id: int):
    role = await user_service.get_user_role(user_id, Sources.MAX)
    await event.message.answer("Главное меню", attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(F.message.body.text == "Выполнить задание")
async def select_task_type(event: MessageCreated, context: MemoryContext):
    await context.set_state(UserTaskStates.SELECT_TYPE)
    keyboard = InlineKeyboardBuilder()
    keyboard.row(MessageButton(text="Онлайн"), MessageButton(text="Офлайн"))
    await event.message.answer("Выберите тип задания:", attachments=[keyboard.as_markup()])


@router.message_callback(F.callback.payload == "max_task_online")
async def online_list(event: MessageCallback, context: MemoryContext,
                      online_task_service: IOnlineTaskService, user_service: IUserService):
    tasks, total_pages = await online_task_service.search_tasks(_uid(event), Sources.MAX, page=1)
    await event.ack()
    if not tasks:
        await event.message.answer("Нет доступных онлайн заданий.")
        return await _main_menu(event, user_service, _uid(event))
    await context.set_state(UserTaskStates.ONLINE_LIST)
    await render_online_tasks(event, tasks, 1, total_pages)


@router.message_created(F.message.body.text == "Онлайн")
async def online_list_text(event: MessageCreated, context: MemoryContext,
                           online_task_service: IOnlineTaskService, user_service: IUserService):
    tasks, total_pages = await online_task_service.search_tasks(_uid(event), Sources.MAX, page=1)
    if not tasks:
        await event.message.answer("Нет доступных онлайн заданий.")
        await context.clear()
        return await _main_menu(event, user_service, _uid(event))
    await context.set_state(UserTaskStates.ONLINE_LIST)
    await render_online_tasks(event, tasks, 1, total_pages)


async def render_online_tasks(event, tasks, page: int, total_pages: int):
    rows = []
    for task in tasks:
        rows.append([(f"#{task.id} {task.type.value} - {task.reward}б", f"max_online_view:{task.id}")])
    nav = []
    if page > 1:
        nav.append(("Назад", f"max_online_page:{page - 1}"))
    if page < total_pages:
        nav.append(("Вперёд", f"max_online_page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("В меню", "max_task_menu")])
    await event.message.answer(
        f"Доступные задания (стр. {page}/{total_pages}):",
        attachments=[_button_keyboard(rows).as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_online_page:"))
async def online_page(event: MessageCallback, online_task_service: IOnlineTaskService):
    page = int(event.callback.payload.split(":", 1)[1])
    tasks, total_pages = await online_task_service.search_tasks(_uid(event), Sources.MAX, page=page)
    await event.ack()
    await render_online_tasks(event, tasks, page, total_pages)


@router.message_callback(F.callback.payload.startswith("max_online_view:"))
async def view_online(event: MessageCallback, context: MemoryContext,
                      online_task_service: IOnlineTaskService):
    task_id = int(event.callback.payload.split(":", 1)[1])
    task = await online_task_service.get_task(task_id)
    await event.ack()
    if not task:
        return await event.message.answer("Задание не найдено.")
    await context.set_state(UserTaskStates.ONLINE_VIEW)
    keyboard = _button_keyboard([
        [("Проверить", f"max_online_check:{task.id}")],
        [("К списку", "max_task_online")]
    ])
    await event.message.answer(
        f"Задание #{task.id}\n"
        f"Тип: {task.type.value}\n"
        f"Награда: {task.reward} баллов\n"
        f"Ссылка: {task.url}",
        attachments=[keyboard.as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_online_check:"))
async def check_online(event: MessageCallback, context: MemoryContext,
                       online_task_service: IOnlineTaskService, user_service: IUserService):
    task_id = int(event.callback.payload.split(":", 1)[1])
    try:
        await online_task_service.check_task(_uid(event), Sources.MAX, task_id)
        await event.ack()
        await event.message.answer("Задание принято, баллы начислены.")
        await context.clear()
        await _main_menu(event, user_service, _uid(event))
    except Exception as e:
        await event.ack()
        await event.message.answer(f"Задание не принято: {e}")


@router.message_callback(F.callback.payload == "max_task_offline")
async def offline_list(event: MessageCallback, context: MemoryContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    user = await user_service.get_user(_uid(event), Sources.MAX)
    await event.ack()
    if user.grade not in (UserGrade.AGITATOR, UserGrade.RESERVE):
        await event.message.answer(
            "Этот тип заданий открывается при достижении ранга 'Агитатор'. "
            "Для его прохождения необходимо пройти обучение."
        )
        return await _main_menu(event, user_service, _uid(event))
    all_tasks, total_pages = await offline_task_service.search_tasks(user.id, user.source, page=1)
    tasks = [task for task in all_tasks if task.region == user.region]
    if not tasks:
        await event.message.answer("Нет заданий в вашем регионе.")
        return await _main_menu(event, user_service, _uid(event))
    await context.set_state(UserTaskStates.OFFLINE_LIST)
    await render_offline_tasks(event, tasks, 1, total_pages)


@router.message_created(F.message.body.text == "Офлайн")
async def offline_list_text(event: MessageCreated, context: MemoryContext,
                            offline_task_service: IOfflineTaskService, user_service: IUserService):
    user = await user_service.get_user(_uid(event), Sources.MAX)
    if user.grade not in (UserGrade.AGITATOR, UserGrade.RESERVE):
        await event.message.answer(
            "Этот тип заданий открывается при достижении ранга 'Агитатор'. "
            "Для его прохождения необходимо пройти обучение."
        )
        await context.clear()
        return await _main_menu(event, user_service, _uid(event))
    all_tasks, total_pages = await offline_task_service.search_tasks(user.id, user.source, page=1)
    tasks = [task for task in all_tasks if task.region == user.region]
    if not tasks:
        await event.message.answer("Нет заданий в вашем регионе.")
        await context.clear()
        return await _main_menu(event, user_service, _uid(event))
    await context.set_state(UserTaskStates.OFFLINE_LIST)
    await render_offline_tasks(event, tasks, 1, total_pages)


async def render_offline_tasks(event, tasks, page: int, total_pages: int):
    rows = []
    for task in tasks:
        rows.append([(f"#{task.id} {task.title[:30]}", f"max_offline_view:{task.id}")])
    nav = []
    if page > 1:
        nav.append(("Назад", f"max_offline_page:{page - 1}"))
    if page < total_pages:
        nav.append(("Вперёд", f"max_offline_page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("В меню", "max_task_menu")])
    await event.message.answer(
        f"Задания в вашем регионе (стр. {page}/{total_pages}):",
        attachments=[_button_keyboard(rows).as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_offline_page:"))
async def offline_page(event: MessageCallback, offline_task_service: IOfflineTaskService,
                       user_service: IUserService):
    page = int(event.callback.payload.split(":", 1)[1])
    user = await user_service.get_user(_uid(event), Sources.MAX)
    all_tasks, total_pages = await offline_task_service.search_tasks(user.id, user.source, page=page)
    tasks = [task for task in all_tasks if task.region == user.region]
    await event.ack()
    await render_offline_tasks(event, tasks, page, total_pages)


@router.message_callback(F.callback.payload.startswith("max_offline_view:"))
async def view_offline(event: MessageCallback, context: MemoryContext,
                       offline_task_service: IOfflineTaskService):
    task_id = int(event.callback.payload.split(":", 1)[1])
    task = await offline_task_service.get_task(task_id)
    await event.ack()
    if not task:
        return await event.message.answer("Задание не найдено.")
    keyboard = _button_keyboard([
        [("Принять", f"max_offline_accept:{task.id}")],
        [("К списку", "max_task_offline")]
    ])
    await context.set_state(UserTaskStates.OFFLINE_VIEW)
    await event.message.answer(
        f"{task.title}\n"
        f"Период: {task.start_date.strftime('%d.%m.%Y')} - {task.end_date.strftime('%d.%m.%Y')}\n"
        f"{task.description}\n"
        f"Место: {task.location}\n"
        f"Контакты: {task.contacts}\n"
        f"Награда: {task.reward} баллов",
        attachments=[keyboard.as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_offline_accept:"))
async def accept_offline(event: MessageCallback, context: MemoryContext,
                         offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService,
                         user_service: IUserService):
    task_id = int(event.callback.payload.split(":", 1)[1])
    try:
        await offline_task_service.accept_offline_task(_uid(event), Sources.MAX, task_id)
        await notification_service.notify_user(_uid(event), Sources.MAX,
                                               f"Вы взяли офлайн задачу #{task_id}. Ожидает проверки.")
        await event.ack()
        await event.message.answer("Задача принята. Свяжитесь с местным отделением по контактам в описании.")
        await context.clear()
        await _main_menu(event, user_service, _uid(event))
    except DomainError as e:
        await event.ack()
        await event.message.answer(str(e))


@router.message_created(F.message.body.text == "Мои задания")
async def my_tasks(event: MessageCreated, context: MemoryContext,
                   offline_task_service: IOfflineTaskService, user_service: IUserService):
    user = await user_service.get_user(_uid(event), Sources.MAX)
    tasks, _ = await offline_task_service.get_user_tasks(user.id, user.source, page=1)
    if not tasks:
        await event.message.answer("У вас нет активных заданий.")
        return await _main_menu(event, user_service, _uid(event))
    rows = []
    for accepted in tasks:
        if accepted.task:
            rows.append([(f"#{accepted.task.id} {accepted.task.title[:30]}", f"max_my_task:{accepted.task.id}")])
    rows.append([("В меню", "max_task_menu")])
    await context.set_state(UserTaskStates.MY_TASKS)
    await event.message.answer("Ваши задания:", attachments=[_button_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload.startswith("max_my_task:"))
async def view_my_task(event: MessageCallback, offline_task_service: IOfflineTaskService):
    task_id = int(event.callback.payload.split(":", 1)[1])
    task = await offline_task_service.get_task(task_id)
    await event.ack()
    if not task:
        return await event.message.answer("Задание не найдено.")
    keyboard = _button_keyboard([
        [("Отменить", f"max_my_cancel:{task.id}")],
        [("К моим заданиям", "max_my_tasks_back")]
    ])
    await event.message.answer(
        f"{task.title}\n{task.description}\n"
        f"Место: {task.location}\nКонтакты: {task.contacts}\n"
        f"Награда: {task.reward} баллов",
        attachments=[keyboard.as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_my_cancel:"))
async def cancel_my_task(event: MessageCallback, context: MemoryContext,
                         offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService,
                         user_service: IUserService):
    task_id = int(event.callback.payload.split(":", 1)[1])
    try:
        await offline_task_service.cancel_task(_uid(event), Sources.MAX, task_id)
        await notification_service.notify_user(_uid(event), Sources.MAX,
                                               f"Задание #{task_id} отменено.")
        await event.ack()
        await event.message.answer(f"Задание #{task_id} успешно отменено.")
        await context.clear()
        await _main_menu(event, user_service, _uid(event))
    except Exception as e:
        await event.ack()
        await event.message.answer(f"Ошибка при отмене: {e}")


@router.message_callback(F.callback.payload == "max_my_tasks_back")
async def back_to_my_tasks(event: MessageCallback, context: MemoryContext,
                           offline_task_service: IOfflineTaskService, user_service: IUserService):
    user = await user_service.get_user(_uid(event), Sources.MAX)
    tasks, _ = await offline_task_service.get_user_tasks(user.id, user.source, page=1)
    await event.ack()
    if not tasks:
        await event.message.answer("У вас нет активных заданий.")
        await context.clear()
        return await _main_menu(event, user_service, _uid(event))
    rows = []
    for accepted in tasks:
        if accepted.task:
            rows.append([(f"#{accepted.task.id} {accepted.task.title[:30]}", f"max_my_task:{accepted.task.id}")])
    rows.append([("В меню", "max_task_menu")])
    await event.message.answer("Ваши задания:", attachments=[_button_keyboard(rows).as_markup()])


@router.message_callback(F.callback.payload == "max_task_menu")
async def back_to_menu(event: MessageCallback, context: MemoryContext, user_service: IUserService):
    await event.ack()
    await context.clear()
    await _main_menu(event, user_service, _uid(event))
