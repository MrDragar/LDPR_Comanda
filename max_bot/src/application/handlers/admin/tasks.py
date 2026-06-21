import logging
import re
from datetime import datetime, date
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback
from maxapi.context import MemoryContext
from src.application.states import AdminTaskStates
from src.application.keyboards.task_keyboard import get_task_type_admin_keyboard, \
    get_admin_verify_task_keyboard, get_admin_verify_users_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.domain.entities.task import TaskType, TaskStatus
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService

logger = logging.getLogger(__name__)
router = Router()
PAGE_LIMIT = 5


async def _cancel_and_exit(event, context: MemoryContext, user_service: IUserService):
    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Действие отменено.",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


# ==================== СОЗДАНИЕ ОНЛАЙН ЗАДАЧИ ====================
@router.message_created(F.message.body.text == "Создать онлайн задачу")
async def start_create_online(event: MessageCreated, context: MemoryContext,
                              user_service: IUserService):
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    if role != UserRole.STAFF_CA:
        return await event.message.answer("Недостаточно прав")

    await event.message.answer("🔗 Введите ссылку на задание (URL поста ВК):",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(AdminTaskStates.CREATE_ONLINE)
    await context.update_data(step="url")


@router.message_created(AdminTaskStates.CREATE_ONLINE)
async def process_online_fields(event: MessageCreated, context: MemoryContext,
                                online_task_service: IOnlineTaskService,
                                user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        return await _cancel_and_exit(event, context, user_service)

    data = await context.get_data()
    step = data.get("step")
    text = event.message.body.text.strip()

    try:
        if step == "url":
            pattern = re.compile(r'^https?://(vk\.com|m\.vk\.com)/wall-?\d+_\d+.*$')
            if not pattern.match(text):
                return await event.message.answer(
                    "⚠️ Ссылка должна быть валидной ссылкой на пост ВК.",
                    attachments=[get_cancel_keyboard().as_markup()])
            await context.update_data(url=text, step="type")
            return await event.message.answer("📌 Выберите тип задания:", attachments=[
                get_task_type_admin_keyboard().as_markup()])
        elif step == "date":
            d = datetime.strptime(text, "%d.%m.%Y").date()
            if d < date.today():
                return await event.message.answer("⚠️ Дата начала не может быть в прошлом.",
                                                  attachments=[get_cancel_keyboard().as_markup()])
            await context.update_data(date=d, step="duration")
            return await event.message.answer("⏱ Введите количество дней активности (число):",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "duration":
            dur = int(text)
            await context.update_data(duration=dur, step="reward")
            return await event.message.answer(
                "💰 Введите размер вознаграждения за выполнение (в баллах):",
                attachments=[get_cancel_keyboard().as_markup()])
        elif step == "reward":
            reward = int(text)
            if reward <= 0:
                return await event.message.answer("Вознаграждение должно быть больше 0.",
                                                  attachments=[get_cancel_keyboard().as_markup()])

            await online_task_service.create_task(date=data["date"], duration=data["duration"],
                                                  type=TaskType(data["type"]), reward=reward,
                                                  url=data["url"])
            await context.clear()
            role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
            return await event.message.answer("✅ Онлайн задача успешно создана!", attachments=[
                get_role_menu_keyboard(role).as_markup()])
    except ValueError:
        return await event.message.answer("⚠️ Неверный формат данных. Попробуйте снова.",
                                          attachments=[get_cancel_keyboard().as_markup()])
    except Exception as e:
        return await event.message.answer(f"❌ Произошла ошибка: {e}",
                                          attachments=[get_cancel_keyboard().as_markup()])


@router.message_callback(F.callback.payload.startswith("set_type_"))
async def set_online_type(event: MessageCallback, context: MemoryContext):
    await event.answer()
    task_type = event.callback.payload.split("_")[-1]
    await context.update_data(type=task_type, step="date")
    await event.message.answer("Введите дату начала (ДД.ММ.ГГГГ):",
                               attachments=[get_cancel_keyboard().as_markup()])
    await event.callback.answer()


# ==================== СОЗДАНИЕ ОФЛАЙН ЗАДАЧИ ====================
@router.message_created(F.message.body.text == "Создать офлайн задачу")
async def start_create_offline(event: MessageCreated, context: MemoryContext,
                               user_service: IUserService):
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    if role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]:
        return await event.message.answer("🚫 Недостаточно прав.")

    await event.message.answer("📝 Введите название задачи:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(AdminTaskStates.CREATE_OFFLINE)
    await context.update_data(step="title", role=role.value)


@router.message_created(AdminTaskStates.CREATE_OFFLINE)
async def process_offline_fields(event: MessageCreated, context: MemoryContext,
                                 user_service: IUserService,
                                 offline_task_service: IOfflineTaskService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        return await _cancel_and_exit(event, context, user_service)

    data = await context.get_data()
    step = data.get("step")
    text = event.message.body.text.strip()

    try:
        if step == "title":
            await context.update_data(title=text, step="description")
            return await event.message.answer("📄 Введите описание задачи:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "description":
            await context.update_data(description=text, step="location")
            return await event.message.answer("📍 Введите место проведения:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "location":
            await context.update_data(location=text, step="contacts")
            return await event.message.answer("📞 Введите контакты организатора:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "contacts":
            await context.update_data(contacts=text, step="start_date")
            return await event.message.answer("📅 Введите дату начала (ДД.ММ.ГГГГ):",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "start_date":
            start_date = datetime.strptime(text, "%d.%m.%Y").date()
            if start_date < date.today():
                return await event.message.answer("⚠️ Дата не может быть в прошлом.",
                                                  attachments=[get_cancel_keyboard().as_markup()])
            await context.update_data(start_date=start_date, step="duration")
            return await event.message.answer("⏱ Введите продолжительность в днях:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "duration":
            duration = int(text)
            if duration <= 0:
                return await event.message.answer("⚠️ Продолжительность должна быть > 0.",
                                                  attachments=[get_cancel_keyboard().as_markup()])
            await context.update_data(duration=duration, step="reward")
            return await event.message.answer("💰 Введите количество баллов:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "reward":
            reward = int(text)
            if reward <= 0:
                return await event.message.answer("⚠️ Баллы должны быть > 0.",
                                                  attachments=[get_cancel_keyboard().as_markup()])

            role = UserRole(data["role"])
            if role == UserRole.STAFF_CA:
                await context.update_data(reward=reward, step="region")
                return await event.message.answer("🌍 Введите регион для задачи:",
                                                  attachments=[get_cancel_keyboard().as_markup()])
            else:
                await context.update_data(reward=reward, step="confirm")
                return await event.message.answer(
                    "✅ Регион определится автоматически. Подтвердите? (Да/Нет)",
                    attachments=[get_cancel_keyboard().as_markup()])
        elif step == "region":
            region_input = text.strip()
            similar = await user_service.get_similar_regions(region_input)
            if region_input != similar[0]:
                hint = f"Регион не найден. Возможно: {', '.join(similar[:3])}" if similar else "Регион не найден."
                return await event.message.answer(f"⚠️ {hint}",
                                                  attachments=[get_cancel_keyboard().as_markup()])
            await context.update_data(region=region_input, step="confirm")
            return await event.message.answer("✅ Регион указан. Подтвердите? (Да/Нет)",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "confirm":
            if text.lower() != "да":
                return await _cancel_and_exit(event, context, user_service)

            role = UserRole(data["role"])
            if role == UserRole.STAFF_CA:
                task = await offline_task_service.create_task_by_admin(region=data["region"],
                                                                       start_date=data[
                                                                           "start_date"],
                                                                       duration=data["duration"],
                                                                       reward=data["reward"],
                                                                       title=data["title"],
                                                                       description=data[
                                                                           "description"],
                                                                       location=data["location"],
                                                                       contacts=data["contacts"])
            else:
                task = await offline_task_service.create_task_by_personal(
                    user_id=event.from_user.user_id, user_source=Sources.MAX,
                    start_date=data["start_date"], duration=data["duration"],
                    reward=data["reward"], title=data["title"],
                    description=data["description"], location=data["location"],
                    contacts=data["contacts"])

            await context.clear()
            admin_role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
            return await event.message.answer(f"✅ Задача '#{task.id} {task.title}' создана!",
                                              attachments=[
                                                  get_role_menu_keyboard(admin_role).as_markup()])
    except ValueError:
        return await event.message.answer("⚠️ Неверный формат. Попробуйте снова.",
                                          attachments=[get_cancel_keyboard().as_markup()])
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await context.clear()
        return await event.message.answer("❌ Произошла ошибка.", attachments=[
            get_role_menu_keyboard(await user_service.get_user_role(event.from_user.user_id,
                                                                    Sources.MAX)).as_markup()])


# ==================== ПРОВЕРКА ОФЛАЙН ЗАДАЧ ====================
@router.message_created(F.message.body.text == "Проверить офлайн задачи")
async def start_verify(event: MessageCreated, user_service: IUserService,
                       offline_task_service: IOfflineTaskService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await event.message.answer("Недостаточно прав")

    tasks, total_pages = await offline_task_service.search_tasks(event.from_user.user_id,
                                                                 Sources.MAX, page=1)
    region_filter = u.region if u.role != UserRole.STAFF_CA else None
    tasks = [t for t in tasks if region_filter is None or t.region == region_filter]

    if not tasks:
        return await event.message.answer("Нет активных задач для проверки.")

    from maxapi.types import CallbackButton
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.row(CallbackButton(text=f"#{t.id} {t.title[:15]}...", payload=f"view_task_{t.id}"))

    await event.message.answer(f"Выберите задачу для проверки:", attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("view_task_"))
async def view_task(event: MessageCallback, offline_task_service: IOfflineTaskService):
    await event.answer()
    tid = int(event.callback.payload.split("_")[-1])
    task = await offline_task_service.get_task(tid)
    if not task:
        return await event.message.answer("Задача не найдена")

    period_str = f"{task.start_date.strftime('%d.%m.%Y')} - {task.end_date.strftime('%d.%m.%Y')}"
    text = f"📋 {task.title}\n📍 {task.location}\n📅 Период: {period_str}\n🏆 {task.reward} баллов"

    await event.message.answer(text, attachments=[get_admin_verify_task_keyboard(tid).as_markup()])
    await event.message.answer()


@router.message_callback(F.callback.payload.startswith("list_users_"))
async def list_users(event: MessageCallback, offline_task_service: IOfflineTaskService,
                     user_service: IUserService):
    await event.answer()
    parts = event.callback.payload.split("_")
    tid = int(parts[2])
    page = int(parts[3])

    tasks_list, total = await offline_task_service.get_users_for_task(tid, page, PAGE_LIMIT)
    total_pages = (total + PAGE_LIMIT - 1) // PAGE_LIMIT
    if not tasks_list:
        await event.message.answer()
        return await event.message.answer("Участников нет.")

    from maxapi.types import CallbackButton
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for t in tasks_list:
        try:
            u = await user_service.get_user(t.user_id, t.user_source)
            fio = f"{u.surname} {u.name}"
        except Exception:
            fio = f"Пользователь {t.user_id}"

        builder.row(CallbackButton(text=fio[:40],
                                   payload=f"check_user_{tid}_{t.user_id}_{t.user_source.value}"))

    if page > 1: builder.row(
        CallbackButton(text="⬅️ Назад", payload=f"list_users_{tid}_{page - 1}"))
    if page < total_pages: builder.row(
        CallbackButton(text="Вперёд ➡️", payload=f"list_users_{tid}_{page + 1}"))
    builder.row(CallbackButton(text="К задаче", payload=f"view_task_{tid}"))

    await event.message.answer("Участники со статусом IN_PROGRESS:",
                               attachments=[builder.as_markup()])
    await event.message.answer()


@router.message_callback(F.callback.payload.startswith("check_user_"))
async def select_user_verify(event: MessageCallback, user_service: IUserService):
    await event.answer()
    parts = event.callback.payload.split("_")
    tid = int(parts[2])
    uid = int(parts[3])
    source = Sources(parts[4])

    u = await user_service.get_user(uid, source)
    text = f"👤 {u.surname} {u.name} {u.patronymic or ''}\n🏙 {u.region}, {u.city}\n📞 {u.phone_number}"

    await event.message.answer(text, attachments=[
        get_admin_verify_users_keyboard(tid, uid, source.value, 1, 1).as_markup()])
    await event.message.answer()


@router.message_callback(F.callback.payload.startswith("verify_action_"))
async def verify_action(event: MessageCallback, offline_task_service: IOfflineTaskService,
                        notification_service: INotificationService):
    await event.answer()
    parts = event.callback.payload.split("_")
    tid = int(parts[2])
    uid = int(parts[3])
    source = Sources(parts[4])
    action_str = parts[5]
    action = TaskStatus.ACCEPTED if action_str == "accept" else TaskStatus.DECLINED

    await offline_task_service.check_task(uid, source, tid, action)
    status_msg = "принята" if action == TaskStatus.ACCEPTED else "отклонена"
    await notification_service.notify_user(uid, source,
                                           f"Ваша офлайн задача #{tid} была {status_msg} администратором.")

    await event.message.answer()
    await event.message.answer(
        f"Статус задачи #{tid} для пользователя {uid} изменён на {action.value}")


# ==================== ВЕРИФИКАЦИЯ ТГ/МАКС ОНЛАЙН ЗАДАЧ ====================
@router.message_callback(F.callback.payload.startswith("tg_verify_accept_"))
@router.message_callback(F.callback.payload.startswith("tg_verify_decline_"))
async def tg_verify_action(event: MessageCallback, online_task_service: IOnlineTaskService,
                           notification_service: INotificationService, verify_chat_id: int):
    await event.answer()
    if event.chat.chat_id != verify_chat_id:
        return

    parts = event.callback.payload.split("_")
    action = parts[2]
    uid = int(parts[3])
    source = Sources(parts[4])
    tid = int(parts[5])

    try:
        if action == "accept":
            await online_task_service.accept_tg_online_task(uid, source, tid)
            await notification_service.notify_user(uid, source,
                                                   f"✅ Ваша онлайн задача #{tid} принята! Баллы начислены.")
            await event.message.edit(text=f"✅ ПРИНЯТО\n{event.message.body.text}", attachments=[])
        else:
            await online_task_service.decline_tg_online_task(uid, source, tid)
            await notification_service.notify_user(uid, source,
                                                   f"❌ Ваша онлайн задача #{tid} отклонена.")
            await event.message.edit(text=f"❌ ОТКЛОНЕНО\n{event.message.body.text}", attachments=[])
    except Exception as e:
        logger.error(e)
        await event.message.answer(f"Ошибка: {e}")


@router.message_callback(F.callback.payload == "back_to_verify")
async def back_to_verify(event: MessageCallback, user_service: IUserService,
                         offline_task_service: IOfflineTaskService):
    await event.answer()
    # Просто возвращаемся к списку задач
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    tasks, _ = await offline_task_service.search_tasks(event.from_user.user_id, Sources.MAX, page=1)
    region_filter = u.region if u.role != UserRole.STAFF_CA else None
    tasks = [t for t in tasks if region_filter is None or t.region == region_filter]

    if not tasks:
        await event.message.answer("Нет активных задач для проверки.")
        await event.message.answer()
        return

    from maxapi.types import CallbackButton
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.row(CallbackButton(text=f"#{t.id} {t.title[:15]}...", payload=f"view_task_{t.id}"))

    await event.message.answer("Выберите задачу для проверки:", attachments=[builder.as_markup()])
    await event.message.answer()
