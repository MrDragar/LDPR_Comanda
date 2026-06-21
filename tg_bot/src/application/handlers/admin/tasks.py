import logging
import re
from datetime import datetime, date
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import AdminTaskStates
from src.domain.entities.task import TaskType, TaskStatus
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService
from src.application.keyboards.task_keyboard import get_task_type_admin_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard


logger = logging.getLogger(__name__)
router = Router(name=__name__)
router.message.filter()

PAGE_LIMIT = 5


async def check_role_tg(user_service, user_id: int, allowed_roles: list, source: Sources) -> bool:
    try:
        role = await user_service.get_user_role(user_id, source)
        return role in allowed_roles
    except:
        return False


async def _cancel_and_exit(message: types.Message, state: FSMContext, user_service: IUserService):
    await state.clear()
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Действие отменено.", reply_markup=get_role_menu_keyboard(role))


# --- CREATE ONLINE TASK ---
@router.message(F.text == "Создать онлайн задачу")
async def start_create_online(message: types.Message, state: FSMContext,
                              user_service: IUserService):
    if not await check_role_tg(user_service, message.from_user.id, [UserRole.STAFF_CA], Sources.TG):
        return await message.answer("Недостаточно прав")
    await message.answer("📝 Введите название онлайн задачи:",
                         reply_markup=get_cancel_keyboard())
    await state.set_state(AdminTaskStates.create_online)
    await state.update_data(step="title")


@router.message(AdminTaskStates.create_online)
async def process_online_fields(message: types.Message, state: FSMContext,
                                online_task_service: IOnlineTaskService,
                                user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]:
        return await _cancel_and_exit(message, state, user_service)
    data = await state.get_data()
    step = data.get("step")
    text = message.text.strip()
    try:
        if step == "title":
            await state.update_data(title=text, step="description")
            return await message.answer("📄 Введите описание задачи:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "description":
            await state.update_data(description=text, step="type")
            return await message.answer("📌 Выберите тип задания:",
                                        reply_markup=get_task_type_admin_keyboard())
        elif step == "url":
            task_type = data.get("type")
            url = text if text != "-" else None
            if task_type != TaskType.OTHER.value:
                pattern = re.compile(r'^https?://(vk\.com|m\.vk\.com)/wall-?\d+_\d+.*$')
                if not url or not pattern.match(url):
                    return await message.answer(
                        "⚠️ Ссылка должна быть валидной ссылкой на пост ВК.",
                        reply_markup=get_cancel_keyboard())
            await state.update_data(url=url, step="date")
            return await message.answer("📅 Введите дату начала (ДД.ММ.ГГГГ):",
                                        reply_markup=get_cancel_keyboard())
        elif step == "date":
            d = datetime.strptime(text, "%d.%m.%Y").date()
            if d < date.today():
                return await message.answer(
                    "⚠️ Дата начала не может быть в прошлом.",
                    reply_markup=get_cancel_keyboard())
            await state.update_data(date=d, step="duration")
            return await message.answer("⏱ Введите количество дней активности (число):",
                                        reply_markup=get_cancel_keyboard())
        elif step == "duration":
            dur = int(text)
            await state.update_data(duration=dur, step="reward")
            return await message.answer("💰 Введите размер вознаграждения за выполнение (в баллах):",
                                        reply_markup=get_cancel_keyboard())
        elif step == "reward":
            reward = int(text)
            if reward <= 0:
                return await message.answer("Вознаграждение должно быть больше 0.",
                                            reply_markup=get_cancel_keyboard())
            await state.update_data(reward=reward, step="is_for_members")
            return await message.answer(
                "Это задание предназначено только для членов партии ЛДПР? (Да/Нет)",
                reply_markup=get_boolean_keyboard())
        elif step == "is_for_members":
            text_lower = text.lower().strip()
            if text_lower not in ['да', 'нет']:
                return await message.answer("Пожалуйста, выберите вариант на клавиатуре:",
                                            reply_markup=get_boolean_keyboard())
            is_for_members = (text_lower == 'да')

            await online_task_service.create_task(
                date=data["date"],
                duration=data["duration"],
                type=TaskType(data["type"]),
                reward=data["reward"],
                url=data.get("url"),
                title=data["title"],
                description=data["description"],
                is_for_members=is_for_members
            )
            await state.clear()
            role = await user_service.get_user_role(message.from_user.id, Sources.TG)
            return await message.answer("✅ Онлайн задача успешно создана!",
                                        reply_markup=get_role_menu_keyboard(role))
    except ValueError:
        return await message.answer("⚠️ Неверный формат данных. Попробуйте снова.",
                                    reply_markup=get_cancel_keyboard())
    except Exception as e:
        logger.error(f"Error creating online task: {e}")
        return await message.answer(f"❌ Произошла ошибка: {e}",
                                    reply_markup=get_cancel_keyboard())


@router.callback_query(F.data.startswith("set_type_"), AdminTaskStates.create_online)
async def set_online_type(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    task_type_str = query.data.split("_")[-1]
    task_type = TaskType(task_type_str)
    await state.update_data(type=task_type.value, step="url")
    if task_type == TaskType.OTHER:
        msg = "🔗 Введите ссылку на задание (или '-', если не требуется):"
    else:
        msg = "🔗 Введите ссылку на задание (URL поста ВК):"
    await query.message.answer(msg, reply_markup=get_cancel_keyboard())


# --- CREATE OFFLINE TASK ---
@router.message(F.text == "Создать офлайн задачу")
async def start_create_offline(message: types.Message, state: FSMContext,
                               user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    if role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]:
        return await message.answer("🚫 Недостаточно прав.")
    await message.answer("📝 Введите название задачи:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminTaskStates.create_offline)
    await state.update_data(step="title", role=role.value)


@router.message(AdminTaskStates.create_offline)
async def process_offline_fields(message: types.Message, state: FSMContext,
                                 user_service: IUserService,
                                 offline_task_service: IOfflineTaskService):
    if message.text and message.text in ["Отмена", "На главную"]:
        return await _cancel_and_exit(message, state, user_service)
    data = await state.get_data()
    step = data.get("step")
    text = message.text.strip()
    try:
        if step == "title":
            await state.update_data(title=text, step="description")
            return await message.answer("📄 Введите описание задачи:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "description":
            await state.update_data(description=text, step="location")
            return await message.answer("📍 Введите место проведения:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "location":
            await state.update_data(location=text, step="contacts")
            return await message.answer("📞 Введите контакты организатора:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "contacts":
            await state.update_data(contacts=text, step="start_date")
            return await message.answer("📅 Введите дату начала (ДД.ММ.ГГГГ):",
                                        reply_markup=get_cancel_keyboard())
        elif step == "start_date":
            start_date = datetime.strptime(text, "%d.%m.%Y").date()
            if start_date < date.today(): return await message.answer(
                "⚠️ Дата не может быть в прошлом.", reply_markup=get_cancel_keyboard())
            await state.update_data(start_date=start_date, step="duration")
            return await message.answer("⏱ Введите продолжительность в днях:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "duration":
            duration = int(text)
            if duration <= 0: return await message.answer("⚠️ Продолжительность должна быть > 0.",
                                                          reply_markup=get_cancel_keyboard())
            await state.update_data(duration=duration, step="reward")
            return await message.answer("💰 Введите количество баллов:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "reward":
            reward = int(text)
            if reward <= 0: return await message.answer("⚠️ Баллы должны быть > 0.",
                                                        reply_markup=get_cancel_keyboard())
            await state.update_data(reward=reward, step="is_for_members")
            return await message.answer(
                "Это задание предназначено только для членов партии ЛДПР? (Да/Нет)",
                reply_markup=get_boolean_keyboard())
        elif step == "is_for_members":
            text_lower = text.lower().strip()
            if text_lower not in ['да', 'нет']:
                return await message.answer("Пожалуйста, выберите вариант на клавиатуре:",
                                            reply_markup=get_boolean_keyboard())
            is_for_members = (text_lower == 'да')

            role = UserRole(data["role"])
            if role == UserRole.STAFF_CA:
                await state.update_data(is_for_members=is_for_members, step="region")
                return await message.answer("🌍 Введите регион для задачи:",
                                            reply_markup=get_cancel_keyboard())
            else:
                await state.update_data(is_for_members=is_for_members, step="confirm")
                return await message.answer(
                    "✅ Регион определится автоматически. Подтвердите? (Да/Нет)",
                    reply_markup=get_cancel_keyboard())
        elif step == "region":
            region_input = text.strip()
            similar = await user_service.get_similar_regions(region_input)
            if region_input != similar[0]:
                hint = f"Регион не найден. Возможно: {', '.join(similar[:3])}" if similar else "Регион не найден."
                return await message.answer(f"⚠️ {hint}", reply_markup=get_cancel_keyboard())
            await state.update_data(region=region_input, step="confirm")
            return await message.answer("✅ Регион указан. Подтвердите? (Да/Нет)",
                                        reply_markup=get_cancel_keyboard())
        elif step == "confirm":
            if text.lower() != "да":
                return await _cancel_and_exit(message, state, user_service)
            role = UserRole(data["role"])
            if role == UserRole.STAFF_CA:
                task = await offline_task_service.create_task_by_admin(
                    region=data["region"],
                    start_date=data["start_date"],
                    duration=data["duration"],
                    reward=data["reward"],
                    title=data["title"],
                    description=data["description"],
                    location=data["location"],
                    contacts=data["contacts"],
                    is_for_members=data["is_for_members"]
                )
            else:
                task = await offline_task_service.create_task_by_personal(
                    user_id=message.from_user.id, user_source=Sources.TG,
                    start_date=data["start_date"], duration=data["duration"], reward=data["reward"],
                    title=data["title"], description=data["description"], location=data["location"],
                    contacts=data["contacts"],
                    is_for_members=data["is_for_members"]
                )
            await state.clear()
            admin_role = await user_service.get_user_role(message.from_user.id, Sources.TG)
            return await message.answer(f"✅ Задача '#{task.id} {task.title}' создана!",
                                        reply_markup=get_role_menu_keyboard(admin_role))
    except ValueError:
        return await message.answer("⚠️ Неверный формат. Попробуйте снова.",
                                    reply_markup=get_cancel_keyboard())
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await state.clear()
        return await message.answer("❌ Произошла ошибка.", reply_markup=get_role_menu_keyboard(
            await user_service.get_user_role(message.from_user.id, Sources.TG)))


# --- VERIFY OFFLINE TASKS ---
@router.message(F.text == "Проверить офлайн задачи")
async def start_verify(message: types.Message, user_service: IUserService,
                       offline_task_service: IOfflineTaskService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await message.answer("Недостаточно прав")

    tasks, total_pages = await offline_task_service.search_tasks(message.from_user.id, Sources.TG,
                                                                 page=1)
    region_filter = u.region if u.role != UserRole.STAFF_CA else None
    tasks = [t for t in tasks if region_filter is None or t.region == region_filter]

    if not tasks:
        return await message.answer("Нет активных задач для проверки.")

    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(text=f"#{t.id} {t.title[:15]}...", callback_data=f"view_task_{t.id}")

    # ИСПРАВЛЕНО: Добавляем кнопки пагинации и возврата в меню
    if total_pages > 1:
        builder.button(text="Вперёд ➡️", callback_data=f"next_verify_2")
    builder.button(text="🔙 В меню", callback_data="back_to_menu")
    builder.adjust(1)

    await message.answer(f"Выберите задачу для проверки (стр. 1/{total_pages}):",
                         reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("next_verify_"))
@router.callback_query(F.data.startswith("prev_verify_"))
async def paginate_verify(query: types.CallbackQuery, user_service: IUserService,
                          offline_task_service: IOfflineTaskService):
    page = int(query.data.split("_")[-1])
    u = await user_service.get_user(query.from_user.id, Sources.TG)

    tasks, total_pages = await offline_task_service.search_tasks(query.from_user.id, Sources.TG,
                                                                 page=page)
    region_filter = u.region if u.role != UserRole.STAFF_CA else None
    tasks = [t for t in tasks if region_filter is None or t.region == region_filter]

    if not tasks:
        await query.answer("На этой странице задач нет.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(text=f"#{t.id} {t.title[:15]}...", callback_data=f"view_task_{t.id}")

    if page > 1:
        builder.button(text="⬅️ Назад", callback_data=f"prev_verify_{page - 1}")
    if page < total_pages:
        builder.button(text="Вперёд ➡️", callback_data=f"next_verify_{page + 1}")
    builder.button(text="🔙 В меню", callback_data="back_to_menu")
    builder.adjust(1)

    await query.answer()
    await query.message.answer(f"Выберите задачу для проверки (стр. {page}/{total_pages}):",
                               reply_markup=builder.as_markup())


@router.callback_query(F.data == "back_to_verify")
async def back_to_verify(query: types.CallbackQuery, user_service: IUserService,
                         offline_task_service: IOfflineTaskService):
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    tasks, total_pages = await offline_task_service.search_tasks(query.from_user.id, Sources.TG,
                                                                 page=1)
    region_filter = u.region if u.role != UserRole.STAFF_CA else None
    tasks = [t for t in tasks if region_filter is None or t.region == region_filter]

    if not tasks:
        await query.answer()
        return await query.message.answer("Нет активных задач для проверки.")

    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(text=f"#{t.id} {t.title[:15]}...", callback_data=f"view_task_{t.id}")

    if total_pages > 1:
        builder.button(text="Вперёд ➡️", callback_data=f"next_verify_2")
    builder.button(text="🔙 В меню", callback_data="back_to_menu")
    builder.adjust(1)

    await query.answer()
    await query.message.answer(f"Выберите задачу для проверки (стр. 1/{total_pages}):",
                               reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("view_task_"))
async def view_task(query: types.CallbackQuery, offline_task_service: IOfflineTaskService):
    tid = int(query.data.split("_")[-1])
    task = await offline_task_service.get_task(tid)
    if not task:
        return await query.answer("Задача не найдена", show_alert=True)

    period_str = f"{task.start_date.strftime('%d.%m.%Y')} - {task.end_date.strftime('%d.%m.%Y')}"
    text = f"📋 {task.title}\n📍 {task.location}\n📅 Период: {period_str}\n🏆 {task.reward} баллов"

    builder = InlineKeyboardBuilder()
    builder.button(text="Список участников", callback_data=f"list_users_{tid}_1")
    builder.button(text="Назад к списку задач", callback_data="back_to_verify")
    builder.adjust(1)

    await query.answer()
    await query.message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("list_users_"))
async def list_users(query: types.CallbackQuery, offline_task_service: IOfflineTaskService,
                     user_service: IUserService):
    parts = query.data.split("_")
    tid = int(parts[2])
    page = int(parts[3])

    tasks_list, total = await offline_task_service.get_users_for_task(tid, page, PAGE_LIMIT)
    if not tasks_list:
        return await query.answer()

    builder = InlineKeyboardBuilder()
    for t in tasks_list:
        try:
            # ИСПРАВЛЕНО: используем t.user_source для корректного получения пользователя
            u = await user_service.get_user(t.user_id, t.user_source)
            fio = f"{u.surname} {u.name}"
        except Exception:
            fio = f"Пользователь {t.user_id}"

        if len(fio) > 40: fio = fio[:37] + "..."
        # ИСПРАВЛЕНО: передаем source в callback_data
        builder.button(text=fio,
                       callback_data=f"check_user_{tid}_{t.user_id}_{t.user_source.value}")

    builder.adjust(1)
    if page > 1: builder.button(text="⬅️ Назад", callback_data=f"list_users_{tid}_{page - 1}")
    if len(tasks_list) == PAGE_LIMIT: builder.button(text="Вперёд ➡️",
                                                     callback_data=f"list_users_{tid}_{page + 1}")
    builder.button(text="К задаче", callback_data=f"view_task_{tid}")

    await query.answer()
    await query.message.answer("Участники со статусом IN_PROGRESS:",
                               reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("check_user_"))
async def select_user_verify(query: types.CallbackQuery, user_service: IUserService):
    parts = query.data.split("_")
    tid = int(parts[2])
    uid = int(parts[3])
    source = Sources(parts[4])  # Извлекаем source

    u = await user_service.get_user(uid, source)
    text = f"👤 {u.surname} {u.name} {u.patronymic or ''}\n🏙 {u.region}, {u.city}\n📞 {u.phone_number}"

    builder = InlineKeyboardBuilder()
    # ИСПРАВЛЕНО: передаем source в callback_data
    builder.button(text="✅ Принять",
                   callback_data=f"verify_action_{tid}_{uid}_{source.value}_accept")
    builder.button(text="❌ Отклонить",
                   callback_data=f"verify_action_{tid}_{uid}_{source.value}_decline")
    builder.button(text="⬅️ Назад", callback_data=f"list_users_{tid}_1")
    builder.adjust(2, 1)

    await query.answer()
    await query.message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("verify_action_"))
async def verify_action(query: types.CallbackQuery, offline_task_service: IOfflineTaskService,
                        notification_service: INotificationService):
    parts = query.data.split("_")
    tid = int(parts[2])
    uid = int(parts[3])
    source = Sources(parts[4])  # Извлекаем source
    action_str = parts[5]

    action = TaskStatus.ACCEPTED if action_str == "accept" else TaskStatus.DECLINED
    await offline_task_service.check_task(uid, source, tid, action)

    status_msg = "принята" if action == TaskStatus.ACCEPTED else "отклонена"
    await notification_service.notify_user(uid, source,
                                           f"Ваша офлайн задача #{tid} была {status_msg} администратором.")

    await query.answer()
    await query.message.answer(
        f"Статус задачи #{tid} для пользователя {uid} изменён на {action.value}")


@router.callback_query(F.data.startswith("tg_verify_accept_"))
@router.callback_query(F.data.startswith("tg_verify_decline_"))
async def tg_verify_action(query: types.CallbackQuery,
                           online_task_service: IOnlineTaskService,
                           notification_service: INotificationService,
                           verify_chat_id: int):
    # Проверка безопасности: кнопки должны нажиматься только в чате верификации
    if query.message.chat.id != verify_chat_id:
        await query.answer("Действие недоступно в этом чате", show_alert=True)
        return

    parts = query.data.split("_")
    action = parts[2]  # accept or decline
    uid = int(parts[3])
    source = Sources(parts[4])
    tid = int(parts[5])

    try:
        current_text = query.message.text
        new_text = current_text.replace("#in_progress\n", "").replace("#in_progress ", "").strip()

        if action == "accept":
            await online_task_service.accept_tg_online_task(uid, source, tid)
            await notification_service.notify_user(uid, source,
                                                   f"✅ Ваша онлайн задача #{tid} принята! Баллы начислены.")

            # Меняем текст и убираем кнопки
            final_text = f"✅ ПРИНЯТО\n{new_text}"
            await query.message.edit_text(final_text, reply_markup=None)
            await query.answer("Задание принято и баллы начислены.")

        else:
            await online_task_service.decline_tg_online_task(uid, source, tid)
            await notification_service.notify_user(uid, source,
                                                   f"❌ Ваша онлайн задача #{tid} отклонена.")

            # Меняем текст и убираем кнопки
            final_text = f"❌ ОТКЛОНЕНО\n{new_text}"
            await query.message.edit_text(final_text, reply_markup=None)
            await query.answer("Задание отклонено.")

    except Exception as e:
        await query.answer(f"Ошибка: {e}", show_alert=True)
