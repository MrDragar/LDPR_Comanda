import logging
import re
from datetime import datetime
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import AdminTaskStates
from src.domain.entities.task import TaskType, TaskStatus
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService
from src.application.filters import check_role, CMDRule

logger = logging.getLogger(__name__)
router = BotLabeler()
PAGE_LIMIT = 5


@router.message(text=["Создать онлайн задачу"])
async def start_create_online(message: Message, user_service: IUserService,
                             state_dispenser: BuiltinStateDispenser):
    if not await check_role(user_service, message.from_id, [UserRole.STAFF_CA]):
        return await message.answer("Недостаточно прав")
    # Сразу переходим к шагу ввода URL
    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE, step="url")
    await message.answer("🔗 Введите ссылку на задание (URL поста ВК, например: https://vk.com/wall-123_456):")


@router.message(state=AdminTaskStates.CREATE_ONLINE)
async def process_online_fields(message: Message, state_dispenser: BuiltinStateDispenser,
                                online_task_service: IOnlineTaskService):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    step = state.payload.get("step")
    payload = {k: v for k, v in state.payload.items() if k != 'step'}
    text = message.text.strip()

    try:
        if step == "url":
            pattern = re.compile(r'^https?://(vk\.com|m\.vk\.com)/wall-?\d+_\d+.*$')
            if not pattern.match(text):
                return await message.answer(
                    "⚠️ Ссылка должна быть валидной ссылкой на пост ВК (начинаться с https://vk.com/wall-...). Попробуйте снова.")

            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE,
                                      **payload, url=text, step="type")

            kb = Keyboard(inline=True)
            for t in TaskType:
                kb.add(Callback(t.value, {"cmd": "set_type", "type": t.value}))
                kb.row()
            return await message.answer("📌 Выберите тип задания:", keyboard=kb.get_json())

        elif step == "date":
            d = datetime.strptime(text, "%d.%m.%Y").date()
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE,
                                      **payload, date=d, step="duration")
            return await message.answer("⏱ Введите количество дней активности (число):")

        elif step == "duration":
            dur = int(text)
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_ONLINE,
                                      **payload, duration=dur, step="reward")
            return await message.answer("💰 Введите размер вознаграждения за выполнение (в баллах):")

        elif step == "reward":
            reward = int(text)
            if reward <= 0: return await message.answer("Вознаграждение должно быть больше 0.")

            await online_task_service.create_task(
                date=payload["date"],
                duration=payload["duration"],
                type=payload["type"],
                reward=reward,
                url=payload["url"]
            )
            await state_dispenser.delete(message.from_id)
            return await message.answer("✅ Онлайн задача успешно создана!")

        else:
            return await message.answer("Неизвестный шаг создания задачи. Начните заново.")

    except ValueError:
        return await message.answer("⚠️ Неверный формат данных. Попробуйте снова.")
    except Exception as e:
        logger.error(f"Error creating online task: {e}")
        return await message.answer(f"❌ Произошла ошибка: {e}")


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("set_type"))
async def set_online_type(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    del state.payload['step']
    await state_dispenser.set(event.object.peer_id, AdminTaskStates.CREATE_ONLINE, **state.payload,
                              type=TaskType(event.object.payload["type"]), step="date")
    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message="Введите дату начала (ДД.ММ.ГГГГ):", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


# --- СОЗДАНИЕ ОФФЛАЙН ЗАДАЧИ ---
@router.message(text=["Создать офлайн задачу"])
async def start_create_offline(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser
) -> None:
    """Точка входа в создание задачи. Проверяет роль."""
    try:
        role = await user_service.get_user_role(message.from_id, Sources.VK)
    except Exception as e:
        logger.error(f"Failed to get role for user {message.from_id}: {e}")
        return await message.answer("Ошибка проверки прав доступа.")

    if role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]:
        return await message.answer(
            "🚫 Недостаточно прав. Создавать офлайн задачи могут только сотрудники ЦА и координаторы РО.")

    # Инициализируем стейт с первым шагом
    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, step="title")
    logger.info(f"User {message.from_id} (role: {role.value}) started offline task creation flow.")
    await message.answer("📝 Введите название задачи:")


@router.message(state=AdminTaskStates.CREATE_OFFLINE)
async def process_offline_fields(
        message: Message,
        user_service: IUserService,
        offline_task_service: IOfflineTaskService,
        state_dispenser: BuiltinStateDispenser
) -> None:
    """Обрабатывает пошаговый ввод полей в зависимости от текущего шага."""
    state = await state_dispenser.get(message.from_id)
    if not state:
        return

    payload = {k: v for k, v in (state.payload or {}).items() if k != 'step'}
    step = state.payload.get("step", "title")
    text = message.text.strip()

    try:
        # --- ШАГ 1: Название ---
        if step == "title":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE,
                                      **payload, title=text, step="description")
            return await message.answer("📄 Введите описание задачи:")

        # --- ШАГ 2: Описание ---
        elif step == "description":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE,
                                      **payload, description=text, step="location")
            return await message.answer("📍 Введите место проведения:")

        # --- ШАГ 3: Место ---
        elif step == "location":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE,
                                      **payload, location=text, step="contacts")
            return await message.answer(
                "📞 Введите контакты организатора (телефон, email или Telegram):")

        # --- ШАГ 4: Контакты ---
        elif step == "contacts":
            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE,
                                      **payload, contacts=text, step="date")
            return await message.answer("📅 Введите дату проведения задачи (ДД.ММ.ГГГГ):")

        # --- ШАГ 5: Дата ---
        elif step == "date":
            try:
                task_date = datetime.strptime(text, "%d.%m.%Y").date()
                await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE,
                                          **payload, date=task_date, step="reward")
                return await message.answer("💰 Введите количество баллов за выполнение:")
            except ValueError:
                return await message.answer(
                    "⚠️ Неверный формат даты. Пожалуйста, используйте ДД.ММ.ГГГГ (например, 25.12.2024)")

        # --- ШАГ 6: Баллы -> Регион или Подтверждение ---
        elif step == "reward":
            try:
                reward = int(text)
                if reward <= 0:
                    return await message.answer("⚠️ Количество баллов должно быть больше 0.")

                role = await user_service.get_user_role(message.from_id, Sources.VK)
                # ИСПРАВЛЕНО: ключ "reward" как строка
                new_payload = {**payload, "reward": reward}

                if role == UserRole.STAFF_CA:
                    # Сотрудник ЦА указывает регион вручную
                    new_payload["step"] = "region"
                    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE,
                                              **new_payload)
                    return await message.answer(
                        "🌍 Введите регион для задачи (например, Москва или Краснодарский край):")
                else:
                    # Координатор РО -> регион определяется автоматически через сервис
                    new_payload["step"] = "confirm"
                    await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE,
                                              **new_payload)
                    return await message.answer(
                        "✅ Регион будет определен автоматически по вашему профилю. Подтвердите создание задачи? (Отправьте 'Да')")

            except ValueError:
                return await message.answer("⚠️ Введите целое число баллов.")

        # --- ШАГ 7: Регион (только для ЦА) -> Подтверждение ---
        elif step == "region":
            # Валидация региона: должен совпадать 1 в 1 со списком в UserService
            region_input = text.strip()
            similar = await user_service.get_similar_regions(region_input)
            if region_input != similar[0]:
                hint = f"Регион не найден. Возможно, вы имели в виду: {', '.join(similar[:3])}" if similar else "Регион не найден. Проверьте название."
                return await message.answer(
                    f"⚠️ {hint}\n\nВведите название региона точно как в списке субъектов РФ:")

            await state_dispenser.set(message.from_id, AdminTaskStates.CREATE_OFFLINE, **payload,
                                      region=region_input, step="confirm")
            return await message.answer(
                "✅ Регион указан. Подтвердите создание задачи? (Отправьте 'Да')")

        # --- ШАГ 8: Подтверждение и вызов сервиса ---
        elif step == "confirm":
            if text.lower() != "да":
                await state_dispenser.delete(message.from_id)
                logger.info(f"User {message.from_id} cancelled offline task creation.")
                return await message.answer("❌ Создание задачи отменено.")

            # Получаем актуальный payload из состояния
            current_state = await state_dispenser.get(message.from_id)
            p = current_state.payload if current_state else {}
            role = await user_service.get_user_role(message.from_id, Sources.VK)
            logger.info(
                f"Finalizing offline task creation for user {message.from_id} (role: {role.value})")

            if role == UserRole.STAFF_CA:
                # Вызов сервиса с явным указанием региона
                task = await offline_task_service.create_task_by_admin(
                    region=p["region"], date=p["date"], reward=p["reward"],
                    title=p["title"], description=p["description"],
                    location=p["location"], contacts=p["contacts"]
                )
            else:
                # Вызов сервиса с авто-определением региона по user_id
                task = await offline_task_service.create_task_by_personal(
                    user_id=message.from_id, user_source=Sources.VK, date=p["date"],
                    reward=p["reward"],
                    title=p["title"], description=p["description"],
                    location=p["location"], contacts=p["contacts"]
                )

            await state_dispenser.delete(message.from_id)
            logger.info(f"Offline task #{task.id} successfully created by user {message.from_id}.")
            return await message.answer(
                f"✅ Оффлайн задача '#{task.id} {task.title}' успешно создана и доступна пользователям!")

    except Exception as e:
        logger.error(f"Critical error in process_offline_fields: {e}", exc_info=True)
        await state_dispenser.delete(message.from_id)
        return await message.answer(
            "❌ Произошла ошибка при создании задачи. Попробуйте позже или обратитесь к разработчику.")


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
    text = f"📋 {task.title}\n📍 {task.location}\n📅 {task.date.strftime('%d.%m.%Y')}\n💰 {task.reward} баллов"
    kb = Keyboard(inline=True).add(Callback("Список участников", {"cmd": "list_users", "tid": tid, "page": 1})).row().add(Callback("Назад к списку задач", {"cmd": "back_to_verify"}))
    await state_dispenser.set(event.object.peer_id, AdminTaskStates.VERIFY_USERS, tid=tid, page=1)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text, keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("list_users"))
async def list_users(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService, state_dispenser: BuiltinStateDispenser):
    tid = event.object.payload["tid"]
    page = event.object.payload.get("page", 1)
    tasks_list, total = await offline_task_service.get_users_for_task(tid, page, PAGE_LIMIT)
    if not tasks_list:
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Нет пользователей в статусе 'in_progress'", random_id=0)
    kb = Keyboard(inline=True)
    for t in tasks_list: kb.add(Callback(f"{t.user_id} ({t.status.value})", {"cmd": "check_user",
                                                                             "tid": tid, "uid": t.user_id})); kb.row()
    kb.row()
    if page > 1: kb.add(Callback("⬅️ Назад", {"cmd": "list_users", "tid": tid, "page": page - 1}))
    if len(tasks_list) == PAGE_LIMIT: kb.add(Callback("Вперёд ➡️", {"cmd": "list_users", "tid": tid, "page": page + 1}))
    kb.add(Callback("К задаче", {"cmd": "view_task", "tid": tid}))
    await state_dispenser.set(event.object.peer_id, AdminTaskStates.VERIFY_USERS, tid=tid, page=page)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Участники со статусом IN_PROGRESS:", keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("check_user"))
async def select_user(event: GroupTypes.MessageEvent, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    uid = event.object.payload["uid"]; tid = event.object.payload["tid"]
    u = await user_service.get_user(uid, Sources.VK)
    text = f"👤 {u.surname} {u.name} {u.patronymic or ''}\n🏙 {u.region}, {u.city}\n📞 {u.phone_number}"
    kb = Keyboard(inline=True).add(Callback("✅ Принять", {"cmd": "verify_action", "tid": tid, "uid": uid, "act": "accept"})).add(Callback("❌ Отклонить", {"cmd": "verify_action", "tid": tid, "uid": uid, "act": "decline"})).row().add(Callback("⬅️ Назад", {"cmd": "list_users", "tid": tid, "page": 1}))
    await state_dispenser.set(event.object.peer_id, AdminTaskStates.VERIFY_ACTION, tid=tid, uid=uid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=text, keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("verify_action"))
async def verify_action(event: GroupTypes.MessageEvent, offline_task_service: IOfflineTaskService, notification_service: INotificationService, state_dispenser: BuiltinStateDispenser):
    p = event.object.payload
    action = TaskStatus.ACCEPTED if p["act"] == "accept" else TaskStatus.DECLINED
    await offline_task_service.check_task(p["uid"], Sources.VK, p["tid"], action)
    status_msg = "принята" if action == TaskStatus.ACCEPTED else "отклонена"
    await notification_service.notify_user_vk(p["uid"], f"Ваша офлайн задача #{p['tid']} была {status_msg} администратором.")
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"Статус задачи #{p['tid']} для пользователя {p['uid']} изменён на {action.value}", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)
    await list_users(event, offline_task_service=offline_task_service, state_dispenser=state_dispenser)
