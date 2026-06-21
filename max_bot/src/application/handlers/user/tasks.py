import asyncio
import json
import logging
from maxapi import Router, F, Bot
from maxapi.types import MessageCreated, MessageCallback
from maxapi.context import MemoryContext
from src.application.states import UserTaskStates
from src.application.keyboards.task_keyboard import (
    get_task_type_keyboard, get_online_tasks_keyboard, get_offline_tasks_keyboard,
    get_online_task_view_keyboard, get_offline_task_view_keyboard, get_my_tasks_keyboard,
    get_my_task_view_keyboard
)
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.exceptions import DomainError
from src.domain.entities.user import Sources, UserGrade
from src.domain.entities.task import TaskStatus
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService

logger = logging.getLogger(__name__)
router = Router()


# ==================== ВЫБОР ТИПА ЗАДАНИЯ ====================
@router.message_created(F.message.body.text == "Выполнить задание")
async def select_task_type(event: MessageCreated, context: MemoryContext):
    await event.message.answer("Выберите тип задания:",
                               attachments=[get_task_type_keyboard().as_markup()])
    await context.set_state(UserTaskStates.SELECT_TYPE)


@router.message_callback(F.callback.payload == "task_type_online")
async def online_list(event: MessageCallback, context: MemoryContext,
                      online_task_service: IOnlineTaskService, user_service: IUserService):
    await event.answer()
    tasks, total_pages = await online_task_service.search_tasks(event.from_user.user_id,
                                                                Sources.MAX, page=1)
    if not tasks:
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("Нет доступных онлайн заданий.",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        await context.clear()
        return

    await event.message.answer(f"Доступные задания (стр. 1/{total_pages}):",
                               attachments=[
                                   get_online_tasks_keyboard(tasks, 1, total_pages).as_markup()])
    await context.update_data(page=1, total_pages=total_pages)
    await context.set_state(UserTaskStates.ONLINE_LIST)


@router.message_callback(F.callback.payload.startswith("next_online_"))
@router.message_callback(F.callback.payload.startswith("prev_online_"))
async def paginate_online(event: MessageCallback, context: MemoryContext,
                          online_task_service: IOnlineTaskService):
    await event.answer()
    page = int(event.callback.payload.split("_")[-1])
    tasks, total_pages = await online_task_service.search_tasks(event.from_user.user_id,
                                                                Sources.MAX, page=page)
    if not tasks:
        await event.message.answer("На этой странице заданий нет.")
        return

    await event.message.answer(f"Доступные задания (стр. {page}/{total_pages}):",
                               attachments=[
                                   get_online_tasks_keyboard(tasks, page, total_pages).as_markup()])
    await context.update_data(page=page, total_pages=total_pages)


@router.message_callback(F.callback.payload.startswith("view_online_"))
async def view_online(event: MessageCallback, context: MemoryContext,
                      online_task_service: IOnlineTaskService):
    await event.answer()
    tid = int(event.callback.payload.split("_")[-1])
    task = await online_task_service.get_task(tid)
    if not task:
        await event.message.answer("Ошибка: задание не найдено")
        return

    text = f"📋 {task.title}\n"
    text += f"📝 {task.description}\n"
    text += f"📌 Тип: {task.type.value}\n"
    text += f"🏆 Награда: {task.reward} баллов\n"
    if task.url:
        text += f"🔗 Ссылка на задание: {task.url}\n"

    await event.message.answer(text, attachments=[get_online_task_view_keyboard(tid).as_markup()])
    await context.update_data(tid=tid)
    await context.set_state(UserTaskStates.ONLINE_VIEW)


# ==================== ПРОВЕРКА ОНЛАЙН ЗАДАНИЯ ====================
@router.message_callback(F.callback.payload.startswith("check_online_"))
async def check_online(event: MessageCallback, context: MemoryContext):
    await event.answer()
    tid = int(event.callback.payload.split("_")[-1])
    await context.update_data(tid=tid)
    await event.message.answer("Отправьте текст, ссылку или скриншот, подтверждающий выполнение задания:")
    await context.set_state(UserTaskStates.TG_ONLINE_AWAIT_PROOF)


@router.message_created(UserTaskStates.TG_ONLINE_AWAIT_PROOF)
async def receive_proof(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("Отправка отменена.",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        return

    proof_text = event.message.body.text or ""
    # ✅ Сохраняем вложения из сообщения пользователя (скриншоты, фото и т.д.)
    user_attachments = getattr(event.message.body, 'attachments', []) or []

    await context.update_data(proof_text=proof_text, user_attachments=user_attachments)

    from maxapi.types import CallbackButton
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="✅ Да, отправить", payload="confirm_submit_online"))
    builder.row(CallbackButton(text="❌ Нет, отмена", payload="cancel_submit_online"))

    await event.message.answer("Вы уверены, что хотите отправить это сообщение на проверку?",
                               attachments=[builder.as_markup()])
    await context.set_state(UserTaskStates.TG_ONLINE_CONFIRM_PROOF)


@router.message_callback(F.callback.payload == "cancel_submit_online")
async def cancel_submit(event: MessageCallback, context: MemoryContext, user_service: IUserService):
    await event.answer()
    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Главное меню",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_callback(F.callback.payload == "confirm_submit_online")
async def confirm_submit(event: MessageCallback, context: MemoryContext,
                         online_task_service: IOnlineTaskService, user_service: IUserService,
                         bot: Bot, verify_chat_id: int):
    await event.answer()
    data = await context.get_data()
    tid = data['tid']
    uid = event.from_user.user_id
    source = Sources.MAX

    try:
        await online_task_service.submit_tg_online_task(uid, source, tid)

        task = await online_task_service.get_task(tid)
        user = await user_service.get_user(uid, source)

        proof_text = data.get('proof_text', '')
        user_attachments = data.get('user_attachments', [])

        # 1. ПЕРЕСЫЛАЕМ сообщение пользователя (текст и вложения) в чат проверки
        if proof_text or user_attachments:
            await bot.send_message(
                chat_id=verify_chat_id,
                text=proof_text if proof_text else "Доказательство выполнения",
                attachments=user_attachments
            )
            await asyncio.sleep(0.5)

        # 2. Отправляем информацию о задании с кнопками "ПОД НИМ" (следующим сообщением)
        info_text = (
            f"#in_progress\n"
            f"📋 Онлайн задание #{task.id} на проверку\n"
            f"👤 Пользователь: {user.surname} {user.name} (ID: {uid}, MAX)\n"
            f"📌 Тип: {task.type.value}\n"
            f"🏆 Награда: {task.reward} баллов\n"
        )
        if task.url:
            info_text += f"🔗 Ссылка: {task.url}\n"

        from maxapi.types import CallbackButton
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="✅ Принять",
                                   payload=f"tg_verify_accept_{uid}_{source.value}_{tid}"))
        builder.row(CallbackButton(text="❌ Отклонить",
                                   payload=f"tg_verify_decline_{uid}_{source.value}_{tid}"))

        await bot.send_message(chat_id=verify_chat_id, text=info_text,
                               attachments=[builder.as_markup()])

        role = await user_service.get_user_role(uid, source)
        await event.message.answer(
            "✅ Задание отправлено на проверку. Ожидайте решения администратора.",
            attachments=[get_role_menu_keyboard(role).as_markup()])
        await context.clear()
    except Exception as e:
        await event.message.answer(f"Ошибка: {e}")


@router.message_callback(F.callback.payload == "back_online_list")
async def back_online_list(event: MessageCallback, context: MemoryContext,
                           online_task_service: IOnlineTaskService):
    await event.answer()
    tasks, total_pages = await online_task_service.search_tasks(event.from_user.user_id,
                                                                Sources.MAX, page=1)
    await event.message.answer(f"Доступные задания (стр. 1/{total_pages}):",
                               attachments=[
                                   get_online_tasks_keyboard(tasks, 1, total_pages).as_markup()])
    await context.update_data(page=1, total_pages=total_pages)
    await context.set_state(UserTaskStates.ONLINE_LIST)


# ==================== ОФЛАЙН ЗАДАНИЯ ====================
@router.message_callback(F.callback.payload == "task_type_offline")
async def offline_list(event: MessageCallback, context: MemoryContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    await event.answer()
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.grade not in (UserGrade.AGITATOR, UserGrade.RESERVE):
        await event.message.answer("Этот тип заданий открывается при достижении ранга 'Агитатор'.",
                                   attachments=[get_role_menu_keyboard(u.role).as_markup()])
        await context.clear()
        return

    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1)
    tasks = [t for t in all_tasks if t.region == u.region]
    if not tasks:
        await event.message.answer("Нет заданий в вашем регионе.",
                                   attachments=[get_role_menu_keyboard(u.role).as_markup()])
        await context.clear()
        return

    await event.message.answer(f"Задания в вашем регионе (стр. 1/{total_pages}):",
                               attachments=[
                                   get_offline_tasks_keyboard(tasks, 1, total_pages).as_markup()])
    await context.update_data(page=1, total_pages=total_pages)
    await context.set_state(UserTaskStates.OFFLINE_LIST)


@router.message_callback(F.callback.payload.startswith("next_offline_"))
@router.message_callback(F.callback.payload.startswith("prev_offline_"))
async def paginate_offline(event: MessageCallback, context: MemoryContext,
                           offline_task_service: IOfflineTaskService, user_service: IUserService):
    await event.answer()
    page = int(event.callback.payload.split("_")[-1])
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=page)
    tasks = [t for t in all_tasks if t.region == u.region]

    await event.message.answer(f"Задания в вашем регионе (стр. {page}/{total_pages}):",
                               attachments=[get_offline_tasks_keyboard(tasks, page,
                                                                       total_pages).as_markup()])
    await context.update_data(page=page, total_pages=total_pages)


@router.message_callback(F.callback.payload.startswith("view_offline_"))
async def view_offline(event: MessageCallback, context: MemoryContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    await event.answer()
    tid = int(event.callback.payload.split("_")[-1])
    task = await offline_task_service.get_task(tid)
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)

    active_tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, 1)
    if len(active_tasks) >= 2:
        await event.message.answer("❌ Нельзя взять более 2 активных офлайн задач одновременно.")
        return

    period_str = f"{task.start_date.strftime('%d.%m.%Y')} - {task.end_date.strftime('%d.%m.%Y')}"
    text = (f"📋 {task.title}\n"
            f"📅 Период: {period_str}\n"
            f"📝 {task.description}\n"
            f"📍 {task.location}\n"
            f"📞 {task.contacts}\n"
            f"🏆 {task.reward} баллов")

    await event.message.answer(text, attachments=[get_offline_task_view_keyboard(tid).as_markup()])
    await context.update_data(tid=tid)
    await context.set_state(UserTaskStates.OFFLINE_VIEW)


@router.message_callback(F.callback.payload.startswith("accept_offline_"))
async def accept_offline(event: MessageCallback, context: MemoryContext,
                         offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService, user_service: IUserService):
    await event.answer()
    tid = int(event.callback.payload.split("_")[-1])
    try:
        await offline_task_service.accept_offline_task(event.from_user.user_id, Sources.MAX, tid)
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer(
            "✅ Задача принята. Свяжитесь с местным отделением по контактам в описании.",
            attachments=[get_role_menu_keyboard(role).as_markup()])
        await notification_service.notify_user(event.from_user.user_id, Sources.MAX,
                                               f"Вы взяли офлайн задачу #{tid}. Ожидает проверки.")
        await context.clear()
    except DomainError as e:
        await event.message.answer(str(e))


@router.message_callback(F.callback.payload == "back_offline_list")
async def back_offline_list(event: MessageCallback, context: MemoryContext,
                            offline_task_service: IOfflineTaskService, user_service: IUserService):
    await event.answer()
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1)
    tasks = [t for t in all_tasks if t.region == u.region]
    await event.message.answer(f"Задания в регионе (стр. 1/{total_pages}):",
                               attachments=[
                                   get_offline_tasks_keyboard(tasks, 1, total_pages).as_markup()])
    await context.update_data(page=1, total_pages=total_pages)
    await context.set_state(UserTaskStates.OFFLINE_LIST)


# ==================== МОИ ЗАДАНИЯ ====================
@router.message_created(F.message.body.text == "Мои задания")
async def my_tasks(event: MessageCreated, context: MemoryContext,
                   offline_task_service: IOfflineTaskService, user_service: IUserService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        await event.message.answer("У вас нет активных заданий.",
                                   attachments=[get_role_menu_keyboard(u.role).as_markup()])
        return
    await event.message.answer("Ваши задания:",
                               attachments=[get_my_tasks_keyboard(tasks).as_markup()])
    await context.set_state(UserTaskStates.MY_TASKS)


@router.message_callback(F.callback.payload.startswith("view_my_task_"))
async def view_my_task(event: MessageCallback, context: MemoryContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    await event.answer()
    tid = int(event.callback.payload.split("_")[-1])
    task = await offline_task_service.get_task(tid)
    if not task:
        await event.message.answer("Ошибка: задание не найдено")
        return

    user_tasks, _ = await offline_task_service.get_user_tasks(event.from_user.user_id, Sources.MAX,
                                                              page=1)
    accepted = next((t for t in user_tasks if t.task and t.task.id == tid), None)

    text = (f"📋 {task.title}\n"
            f"📝 {task.description}\n"
            f"📍 {task.location}\n"
            f"📞 {task.contacts}\n"
            f"💰 {task.reward} баллов")

    is_in_progress = accepted and accepted.status == TaskStatus.IN_PROGRESS
    await event.message.answer(text, attachments=[
        get_my_task_view_keyboard(tid, is_in_progress).as_markup()])


@router.message_callback(F.callback.payload.startswith("cancel_my_task_"))
async def cancel_my_task(event: MessageCallback, context: MemoryContext,
                         offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService, user_service: IUserService):
    await event.answer()
    tid = int(event.callback.payload.split("_")[-1])
    try:
        await offline_task_service.cancel_task(event.from_user.user_id, Sources.MAX, tid)
        await notification_service.notify_user(event.from_user.user_id, Sources.MAX,
                                               f"Задание #{tid} отменено.")
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer(f"✅ Задание #{tid} успешно отменено.",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        await context.clear()
    except Exception as e:
        await event.message.answer(f"Ошибка при отмене: {e}")


@router.message_callback(F.callback.payload == "back_to_my_tasks")
async def back_to_my_tasks(event: MessageCallback, context: MemoryContext,
                           offline_task_service: IOfflineTaskService, user_service: IUserService):
    await event.answer()
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        await event.message.answer("У вас нет активных заданий.",
                                   attachments=[get_role_menu_keyboard(u.role).as_markup()])
        await context.clear()
        return
    await event.message.answer("Ваши задания:",
                               attachments=[get_my_tasks_keyboard(tasks).as_markup()])


@router.message_callback(F.callback.payload == "back_to_menu")
async def back_to_menu(event: MessageCallback, context: MemoryContext, user_service: IUserService):
    await event.answer()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Главное меню",
                               attachments=[get_role_menu_keyboard(role).as_markup()])
    await context.clear()
