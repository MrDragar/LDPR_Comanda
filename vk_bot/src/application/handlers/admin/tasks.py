import logging
import re
from datetime import datetime, date
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import AdminTaskStates
from src.application.utils import handle_cancel, get_cancel_kb
from src.domain.entities.task import TaskType, TaskStatus
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService
from src.application.filters import check_role, CMDRule

logger = logging.getLogger(__name__)
router = BotLabeler()
PAGE_LIMIT = 5


@router.message(text=["Создать онлайн задачу"])
async def start_create_online(message: Message, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    if not await check_role(user_service, message.from_id, [UserRole.STAFF_CA]):
        return await message.answer("Недостаточно прав")
    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE, step="title")
    await message.answer("📝 Введите название онлайн задачи:", keyboard=get_cancel_kb())


@router.message(state=AdminTaskStates.CREATE_ONLINE)
async def process_online_fields(message: Message, state_dispenser: BuiltinStateDispenser,
                                online_task_service: IOnlineTaskService,
                                user_service: IUserService):
    if await handle_cancel(message, state_dispenser, user_service): return
    state = await state_dispenser.get(message.from_id)
    if not state: return
    step = state.payload.get("step")
    payload = {k: v for k, v in state.payload.items() if k != 'step'}
    text = message.text.strip()
    try:
        if step == "title":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE, **payload,
                                      title=text, step="description")
            return await message.answer("📄 Введите описание онлайн задачи:",
                                        keyboard=get_cancel_kb())
        elif step == "description":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE, **payload,
                                      description=text, step="type")
            kb = Keyboard(inline=True)
            for t in TaskType:
                kb.add(Callback(t.value, {"cmd": "set_type", "type": t.value}))
                kb.row()
            return await message.answer("📌 Выберите тип задания:", keyboard=kb.get_json())
        elif step == "url":
            task_type = payload.get("type")
            url = text if text != "-" else None
            if task_type != TaskType.OTHER:
                pattern = re.compile(r'^https?://(vk\.com|m\.vk\.com)/wall-?\d+_\d+.*$')
                if not url or not pattern.match(url):
                    return await message.answer(
                        "⚠️ Ссылка должна быть валидной ссылкой на пост ВК.",
                        keyboard=get_cancel_kb())
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE, **payload,
                                      url=url, step="date")
            return await message.answer("📅 Введите дату начала (ДД.ММ.ГГГГ):",
                                        keyboard=get_cancel_kb())
        elif step == "date":
            d = datetime.strptime(text, "%d.%m.%Y").date()
            if d < date.today(): return await message.answer(
                "⚠️ Дата начала не может быть в прошлом.", keyboard=get_cancel_kb())
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE, **payload,
                                      date=d, step="duration")
            return await message.answer("⏱ Введите количество дней активности (число):",
                                        keyboard=get_cancel_kb())
        elif step == "duration":
            dur = int(text)
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE, **payload,
                                      duration=dur, step="reward")
            return await message.answer("💰 Введите размер вознаграждения за выполнение (в баллах):",
                                        keyboard=get_cancel_kb())
        elif step == "reward":
            reward = int(text)
            if reward <= 0: return await message.answer("Вознаграждение должно быть больше 0.",
                                                        keyboard=get_cancel_kb())
            await online_task_service.create_task(
                date=payload["date"], duration=payload["duration"], type=payload["type"],
                reward=reward, url=payload["url"], title=payload["title"],
                description=payload["description"]
            )
            await state_dispenser.delete(message.from_id)
            return await message.answer("✅ Онлайн задача успешно создана!")
    except ValueError:
        return await message.answer("⚠️ Неверный формат данных. Попробуйте снова.",
                                    keyboard=get_cancel_kb())
    except Exception as e:
        logger.error(f"Error creating online task: {e}")
        return await message.answer(f"❌ Произошла ошибка: {e}")


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("set_type"))
async def set_online_type(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    payload = {k: v for k, v in state.payload.items() if k != 'step'}
    task_type = TaskType(event.object.payload["type"])

    await state_dispenser.set(event.object.peer_id, AdminTaskStates.CREATE_ONLINE, **payload,
                              type=task_type, step="url")

    if task_type == TaskType.OTHER:
        msg = "🔗 Введите ссылку на задание (или '-' если не требуется):"
    else:
        msg = "🔗 Введите ссылку на задание (URL поста ВК):"

    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=msg, random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


# --- СОЗДАНИЕ ОФФЛАЙН ЗАДАЧИ ---
@router.message(text=["Создать офлайн задачу"])
async def start_create_offline(message: Message, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    try: role = await user_service.get_user_role(message.from_id, Sources.VK)
    except Exception as e: return await message.answer("Ошибка проверки прав доступа.")
    if role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]: return await message.answer("🚫 Недостаточно прав.")
    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, step="title")
    await message.answer("📝 Введите название задачи:", keyboard=get_cancel_kb())

@router.message(state=AdminTaskStates.CREATE_OFFLINE)
async def process_offline_fields(message: Message, user_service: IUserService, offline_task_service: IOfflineTaskService, state_dispenser: BuiltinStateDispenser):
    if await handle_cancel(message, state_dispenser, user_service): return
    state = await state_dispenser.get(message.from_id)
    if not state: return
    payload = {k: v for k, v in (state.payload or {}).items() if k != 'step'}
    step = state.payload.get("step", "title")
    text = message.text.strip()
    try:
        if step == "title":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload, title=text, step="description")
            return await message.answer("📄 Введите описание задачи:", keyboard=get_cancel_kb())
        elif step == "description":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload, description=text, step="location")
            return await message.answer("📍 Введите место проведения:", keyboard=get_cancel_kb())
        elif step == "location":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload, location=text, step="contacts")
            return await message.answer("📞 Введите контакты организатора:", keyboard=get_cancel_kb())
        elif step == "contacts":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload, contacts=text, step="start_date")
            return await message.answer("📅 Введите дату начала проведения задачи (ДД.ММ.ГГГГ):", keyboard=get_cancel_kb())
        elif step == "start_date":
            try:
                start_date = datetime.strptime(text, "%d.%m.%Y").date()
                if start_date < date.today(): return await message.answer("⚠️ Дата начала не может быть в прошлом.", keyboard=get_cancel_kb())
                await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload, start_date=start_date, step="duration")
                return await message.answer("⏱ Введите продолжительность задачи в днях (число):", keyboard=get_cancel_kb())
            except ValueError: return await message.answer("⚠️ Неверный формат даты.", keyboard=get_cancel_kb())
        elif step == "duration":
            try:
                duration = int(text)
                if duration <= 0: return await message.answer("⚠️ Продолжительность должна быть больше 0.", keyboard=get_cancel_kb())
                await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload, duration=duration, step="reward")
                return await message.answer("💰 Введите количество баллов за выполнение:", keyboard=get_cancel_kb())
            except ValueError: return await message.answer("⚠️ Введите целое число дней.", keyboard=get_cancel_kb())
        elif step == "reward":
            try:
                reward = int(text)
                if reward <= 0: return await message.answer("⚠️ Количество баллов должно быть больше 0.", keyboard=get_cancel_kb())
                role = await user_service.get_user_role(message.from_id, Sources.VK)
                new_payload = {**payload, "reward": reward}
                if role == UserRole.STAFF_CA:
                    new_payload["step"] = "region"
                    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **new_payload)
                    return await message.answer("🌍 Введите регион для задачи:", keyboard=get_cancel_kb())
                else:
                    new_payload["step"] = "confirm"
                    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **new_payload)
                    return await message.answer("✅ Регион будет определен автоматически. Подтвердите создание задачи? (Отправьте 'Да')", keyboard=get_cancel_kb())
            except ValueError: return await message.answer("⚠️ Введите целое число баллов.", keyboard=get_cancel_kb())
        elif step == "region":
            region_input = text.strip()
            similar = await user_service.get_similar_regions(region_input)
            if region_input != similar[0]:
                hint = f"Регион не найден. Возможно, вы имели в виду: {', '.join(similar[:3])}" if similar else "Регион не найден."
                return await message.answer(f"⚠️ {hint}\nВведите название региона точно:", keyboard=get_cancel_kb())
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload, region=region_input, step="confirm")
            return await message.answer("✅ Регион указан. Подтвердите создание задачи? (Отправьте 'Да')", keyboard=get_cancel_kb())
        elif step == "confirm":
            if text.lower() != "да":
                await state_dispenser.delete(message.from_id)
                return await message.answer("❌ Создание задачи отменено.")
            current_state = await state_dispenser.get(message.from_id)
            p = current_state.payload if current_state else {}
            role = await user_service.get_user_role(message.from_id, Sources.VK)
            if role == UserRole.STAFF_CA:
                task = await offline_task_service.create_task_by_admin(
                    region=p["region"], start_date=p["start_date"], duration=p["duration"], reward=p["reward"], title=p["title"], description=p["description"], location=p["location"], contacts=p["contacts"]
                )
            else:
                task = await offline_task_service.create_task_by_personal(user_id=message.from_id, user_source=Sources.VK, start_date=p["start_date"], duration=p["duration"], reward=p["reward"], title=p["title"], description=p["description"], location=p["location"], contacts=p["contacts"])
            await state_dispenser.delete(message.from_id)
            return await message.answer(f"✅ Оффлайн задача '#{task.id} {task.title}' успешно создана!")
    except Exception as e:
        logger.error(f"Critical error in process_offline_fields: {e}", exc_info=True)
        await state_dispenser.delete(message.from_id)
        return await message.answer("❌ Произошла ошибка при создании задачи.")


# --- ПРОВЕРКА ОФФЛАЙН ЗАДАЧ (ПОЛНЫЙ ЦИКЛ) ---
@router.message(text=["Проверить офлайн задачи"])
async def start_verify(message: Message, user_service: IUserService,
                       offline_task_service: IOfflineTaskService,
                       state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO,
                      UserRole.STAFF_RO]: return await message.answer("Недостаточно прав")

    tasks, total_pages = await offline_task_service.search_tasks(message.from_id, Sources.VK,
                                                                 page=1)
    logger.debug(f"Total pages: {total_pages}")
    region_filter = u.region if u.role != UserRole.STAFF_CA else None
    tasks = [t for t in tasks if region_filter is None or t.region == region_filter]
    if not tasks: return await message.answer("Нет активных задач для проверки.")

    kb = Keyboard(inline=True)
    for t in tasks: kb.add(
        Callback(f"#{t.id} {t.title[:15]}...", {"cmd": "view_task", "tid": t.id})); kb.row()
    if total_pages > 1:
        if 1 < total_pages: kb.add(Callback("Вперёд ➡️", {"cmd": "next_verify"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))

    await state_dispenser.set(message.from_id, AdminTaskStates.VERIFY_TASK_LIST, page=1,
                              region=region_filter, total_pages=total_pages)
    await message.answer(f"Выберите задачу для проверки (стр. 1/{total_pages}):",
                         keyboard=kb.get_json())


async def _send_verify_page(event_or_message, offline_task_service, user_service, state_dispenser,
                            peer_id, user_id, new_page, is_callback=False):
    state = await state_dispenser.get(peer_id)
    if not state or state.state != str(AdminTaskStates.VERIFY_TASK_LIST): return
    region = state.payload.get("region")
    total_pages = state.payload.get("total_pages", 1)

    tasks_raw, total = await offline_task_service.search_tasks(user_id, Sources.VK, page=new_page)
    tasks = [t for t in tasks_raw if region is None or t.region == region]
    display_pages = (total + PAGE_LIMIT - 1) // PAGE_LIMIT if total else 1
    if new_page > display_pages: new_page = 1

    if not tasks:
        msg = event_or_message.ctx_api.messages.send if is_callback else event_or_message.answer
        if is_callback:
            await event_or_message.ctx_api.messages.send(peer_id=peer_id,
                                                         message="Нет задач на этой странице.",
                                                         random_id=0)
        else:
            msg("Нет задач на этой странице.")
        return

    kb = Keyboard(inline=True)
    for t in tasks: kb.add(
        Callback(f"#{t.id} {t.title[:15]}...", {"cmd": "view_task", "tid": t.id})); kb.row()
    kb.row()
    if new_page > 1: kb.add(Callback("⬅️ Назад", {"cmd": "prev_verify"}))
    if new_page < total_pages: kb.add(Callback("Вперёд ➡️", {"cmd": "next_verify"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))

    await state_dispenser.set(peer_id, AdminTaskStates.VERIFY_TASK_LIST, page=new_page,
                              region=region, total_pages=total_pages)
    api = event_or_message.ctx_api
    if is_callback:
        await api.messages.send(peer_id=peer_id,
                                message=f"Выберите задачу для проверки (стр. {new_page}/{total_pages}):",
                                keyboard=kb.get_json(), random_id=0)
        await api.messages.send_message_event_answer(event_id=event_or_message.object.event_id,
                                                     user_id=event_or_message.object.user_id,
                                                     peer_id=peer_id)
    else:
        await api.messages.send(peer_id=peer_id,
                                message=f"Выберите задачу для проверки (стр. {new_page}/{total_pages}):",
                                keyboard=kb.get_json(), random_id=0)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_verify"))
async def next_verify(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                      user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    await _send_verify_page(event, offline_task_service, user_service, state_dispenser,
                            event.object.peer_id, event.object.user_id,
                            state.payload.get("page", 1) + 1, is_callback=True)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_verify"))
async def prev_verify(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                      user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    await _send_verify_page(event, offline_task_service, user_service, state_dispenser,
                            event.object.peer_id, event.object.user_id,
                            max(1, state.payload.get("page", 1) - 1), is_callback=True)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_task"))
async def view_task(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService, state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    task = await offline_task_service.get_task(tid)
    if not task: return
    period_str = f"{task.start_date.strftime('%d.%m.%Y')} - {task.end_date.strftime('%d.%m.%Y')}"
    text = f"📋 {task.title}\n📍 {task.location}\n📅 Период: {period_str}\n🏆 {task.reward} баллов"
    kb = Keyboard(inline=True).add(Callback("Список участников", {"cmd": "list_users", "tid": tid, "page": 1})).row().add(Callback("Назад к списку задач", {"cmd": "back_to_verify"}))
    await state_dispenser.set(event.object.peer_id, AdminTaskStates.VERIFY_USERS, tid=tid, page=1)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text, keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("list_users"))
async def list_users(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                     user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    page = event.object.payload.get("page", 1)
    tasks_list, total = await offline_task_service.get_users_for_task(tid, page, PAGE_LIMIT)
    if not tasks_list:
        return await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="Нет пользователей в статусе 'in_progress'",
            random_id=0
        )
    kb = Keyboard(inline=True)
    for t in tasks_list:
        # Получаем пользователя для отображения ФИО с учетом его реального источника
        try:
            u = await user_service.get_user(t.user_id, t.user_source)
            fio = f"{u.surname} {u.name}"
        except Exception:
            fio = f"Пользователь {t.user_id}"

        # Ограничение VK API: текст Callback кнопки не может превышать 40 символов
        if len(fio) > 40:
            fio = fio[:37] + "..."

        # Передаем source пользователя в payload
        kb.add(Callback(fio, {"cmd": "check_user", "tid": tid, "uid": t.user_id,
                              "src": t.user_source.value}))
        kb.row()

    kb.row()
    if page > 1:
        kb.add(Callback("⬅️ Назад", {"cmd": "list_users", "tid": tid, "page": page - 1}))
    if len(tasks_list) == PAGE_LIMIT:
        kb.add(Callback("Вперёд ➡️", {"cmd": "list_users", "tid": tid, "page": page + 1}))
    kb.add(Callback("К задаче", {"cmd": "view_task", "tid": tid}))

    await state_dispenser.set(event.object.peer_id, AdminTaskStates.VERIFY_USERS, tid=tid,
                              page=page)
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message="Участники со статусом IN_PROGRESS:",
        keyboard=kb.get_json(),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("check_user"))
async def select_user(event: GroupTypes.MessageEvent, user_service: IUserService,
                      state_dispenser: BuiltinStateDispenser):
    uid = event.object.payload["uid"]
    src = Sources(event.object.payload["src"])
    tid = event.object.payload["tid"]

    u = await user_service.get_user(uid, src)
    text = (f"👤 {u.surname} {u.name} {u.patronymic or ''}\n"
            f"🏙 {u.region}, {u.city}\n"
            f"📞 {u.phone_number}")

    # Передаем source в кнопки принятия/отклонения
    kb = Keyboard(inline=True).add(
        Callback("✅ Принять", {"cmd": "verify_action", "tid": tid, "uid": uid, "act": "accept",
                               "src": src.value})
    ).add(
        Callback("❌ Отклонить", {"cmd": "verify_action", "tid": tid, "uid": uid, "act": "decline",
                                 "src": src.value})
    ).row().add(
        Callback("⬅️ Назад", {"cmd": "list_users", "tid": tid, "page": 1})
    )

    await state_dispenser.set(event.object.peer_id, AdminTaskStates.VERIFY_ACTION, tid=tid, uid=uid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("verify_action"))
async def verify_action(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService,
                        notification_service: INotificationService,
                        state_dispenser: BuiltinStateDispenser):
    p = event.object.payload
    action = TaskStatus.ACCEPTED if p["act"] == "accept" else TaskStatus.DECLINED

    uid = p["uid"]
    src = Sources(p["src"])
    tid = p["tid"]

    await offline_task_service.check_task(uid, src, tid, action)
    status_msg = "принята" if action == TaskStatus.ACCEPTED else "отклонена"

    # Используем универсальный метод notify_user, чтобы уведомление ушло в нужный мессенджер (ВК/TG/MAX)
    await notification_service.notify_user(uid, src,
                                           f"Ваша офлайн задача #{tid} была {status_msg} администратором.")

    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message=f"Статус задачи #{tid} для пользователя {uid} изменён на {action.value}",
                                      random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)

    await list_users(event, offline_task_service=offline_task_service,
                     state_dispenser=state_dispenser)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_to_tasks"))
async def back_to_tasks(event: GroupTypes.MessageEvent, user_service: IUserService,
                        offline_task_service: IOfflineTaskService,
                        state_dispenser: BuiltinStateDispenser):
    """Возврат к списку задач на проверку из просмотра конкретной задачи"""
    u = await user_service.get_user(event.object.user_id, Sources.VK)

    # Загружаем задачи и фильтруем по региону (как в start_verify)
    tasks, total_pages = await offline_task_service.search_tasks(event.object.user_id, Sources.VK,
                                                                 page=1)
    region_filter = u.region if u.role != UserRole.STAFF_CA else None
    tasks = [t for t in tasks if region_filter is None or t.region == region_filter]

    if not tasks:
        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="Нет активных задач для проверки.",
            random_id=0
        )
    else:
        kb = Keyboard(inline=True)
        for t in tasks:
            kb.add(Callback(f"#{t.id} {t.title[:15]}...", {"cmd": "view_task", "tid": t.id}))
            kb.row()

        kb.row()
        if total_pages > 1:
            kb.add(Callback("Вперёд ➡️", {"cmd": "next_verify"}))
        kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))

        # Восстанавливаем состояние списка задач
        await state_dispenser.set(
            event.object.peer_id,
            AdminTaskStates.VERIFY_TASK_LIST,
            page=1,
            region=region_filter,
            total_pages=total_pages
        )
        await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message=f"Выберите задачу для проверки (стр. 1/{total_pages}):",
            keyboard=kb.get_json(),
            random_id=0
        )

    # Обязательно отвечаем на callback, чтобы убрать "часики" на кнопке
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("vk_verify_accept"))
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("vk_verify_decline"))
async def vk_verify_action(event: GroupTypes.MessageEvent, online_task_service: IOnlineTaskService,
                           notification_service: INotificationService, verify_chat_id: int):
    if verify_chat_id and event.object.peer_id != verify_chat_id:
        return

    cmd = event.object.payload.get("cmd")
    uid = event.object.payload.get("uid")
    tid = event.object.payload.get("tid")
    source = Sources.VK

    try:
        # Получаем исходное сообщение, чтобы отредактировать его и убрать кнопки
        msgs = await event.ctx_api.messages.get_by_conversation_message_id(
            peer_id=event.object.peer_id,
            conversation_message_ids=[event.object.conversation_message_id]
        )
        old_text = msgs.items[0].text if msgs.items else ""
        msg_id = msgs.items[0].id if msgs.items else None

        if cmd == "vk_verify_accept":
            await online_task_service.accept_tg_online_task(uid, source, tid)
            await notification_service.notify_user(uid, source,
                                                   f"✅ Ваша онлайн задача #{tid} принята! Баллы начислены.")
            new_text = old_text.replace("#in_progress", "#accepted")
        else:
            await online_task_service.decline_tg_online_task(uid, source, tid)
            await notification_service.notify_user(uid, source,
                                                   f"❌ Ваша онлайн задача #{tid} отклонена.")
            new_text = old_text.replace("#in_progress", "#declined")

        if msg_id:
            await event.ctx_api.messages.edit(
                peer_id=event.object.peer_id,
                message_id=msg_id,
                message=new_text,
                keyboard="{}"
            )
        else:
            await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                              message=f"ОБРАБОТАНО\n{new_text}", random_id=0)

    except Exception as e:
        logger.error(e)
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"Ошибка: {e}",
                                          random_id=0)

    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)
