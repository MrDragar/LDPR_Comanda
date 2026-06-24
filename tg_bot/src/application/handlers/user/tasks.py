import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.application.states import UserTaskStates
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.domain.exceptions import DomainError
from src.services.interfaces import IOnlineTaskService, IOfflineTaskService, IUserService, \
    INotificationService
from src.domain.entities.user import Sources, UserGrade
from src.application.keyboards.task_keyboard import (
    get_task_type_keyboard, get_online_tasks_keyboard, get_offline_tasks_keyboard,
    get_online_task_view_keyboard, get_offline_task_view_keyboard, get_my_tasks_keyboard,
    get_my_task_view_keyboard
)
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def _get_task_filter(user_service: IUserService, user_id: int) -> bool | None:
    try:
        u = await user_service.get_user(user_id, Sources.TG)
        return bool(u.is_member)
    except Exception:
        return False


@router.message(F.text == "Выполнить задание")
async def select_task_type(message: types.Message, state: FSMContext, user_service: IUserService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)

    if u.is_member is None:
        builder = InlineKeyboardBuilder()
        builder.button(text="Да", callback_data="set_member_yes")
        builder.button(text="Нет", callback_data="set_member_no")
        await message.answer("Вы являетесь членом партии ЛДПР?", reply_markup=builder.as_markup())
        return

    await message.answer("Выберите тип задания:", reply_markup=get_task_type_keyboard())
    await state.set_state(UserTaskStates.select_type)


@router.callback_query(F.data.in_(["set_member_yes", "set_member_no"]))
async def set_member_callback(query: types.CallbackQuery, user_service: IUserService,
                              state: FSMContext):
    is_member = (query.data == "set_member_yes")
    await user_service.update_user_profile(query.from_user.id, Sources.TG, is_member=is_member)

    await query.answer()
    await query.message.answer("Выберите тип задания:", reply_markup=get_task_type_keyboard())
    await state.set_state(UserTaskStates.select_type)


@router.callback_query(F.data == "task_type_online")
async def online_list(query: types.CallbackQuery, state: FSMContext,
                      online_task_service: IOnlineTaskService, user_service: IUserService):
    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    tasks, total_pages = await online_task_service.search_tasks(query.from_user.id, Sources.TG,
                                                                page=1, is_member=is_member_filter)
    if not tasks:
        role = await user_service.get_user_role(query.from_user.id, Sources.TG)
        await query.answer()
        await query.message.answer("Нет доступных онлайн заданий. Загляните к нам снова — скоро будут новые.",
                                   reply_markup=get_role_menu_keyboard(role))
        await state.clear()
        return
    await query.answer()
    await query.message.answer(
        f"Доступные задания (стр. 1/{total_pages}):",
        reply_markup=get_online_tasks_keyboard(tasks, 1, total_pages)
    )
    await state.update_data(page=1, total_pages=total_pages)
    await state.set_state(UserTaskStates.online_list)


@router.callback_query(F.data.startswith("next_online_"), UserTaskStates.online_list)
async def next_online(query: types.CallbackQuery, state: FSMContext,
                      online_task_service: IOnlineTaskService, user_service: IUserService):
    page = int(query.data.split("_")[-1])
    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    tasks, total_pages = await online_task_service.search_tasks(query.from_user.id, Sources.TG,
                                                                page=page, is_member=is_member_filter)
    if not tasks:
        await query.answer("На этой странице заданий нет.", show_alert=True)
        return
    await query.answer()
    await query.message.answer(
        f"Доступные задания (стр. {page}/{total_pages}):",
        reply_markup=get_online_tasks_keyboard(tasks, page, total_pages)
    )
    await state.update_data(page=page, total_pages=total_pages)


@router.callback_query(F.data.startswith("prev_online_"), UserTaskStates.online_list)
async def prev_online(query: types.CallbackQuery, state: FSMContext,
                      online_task_service: IOnlineTaskService, user_service: IUserService):
    page = int(query.data.split("_")[-1])
    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    tasks, total_pages = await online_task_service.search_tasks(query.from_user.id, Sources.TG,
                                                                page=page, is_member=is_member_filter)
    await query.answer()
    await query.message.answer(
        f"Доступные задания (стр. {page}/{total_pages}):",
        reply_markup=get_online_tasks_keyboard(tasks, page, total_pages)
    )
    await state.update_data(page=page, total_pages=total_pages)


@router.callback_query(F.data.startswith("view_online_"))
async def view_online(query: types.CallbackQuery, state: FSMContext,
                      online_task_service: IOnlineTaskService):
    tid = int(query.data.split("_")[-1])
    task = await online_task_service.get_task(tid)
    if not task:
        await query.answer("Ошибка: задание не найдено", show_alert=True)
        return

    text = f"📋 {task.title}\n"
    text += f"📝 {task.description}\n"
    text += f"📌 Тип: {task.type.value}\n"
    text += f"🏆 Награда: {task.reward} баллов\n"
    if task.url:
        text += f"🔗 Ссылка на задание: {task.url}"

    await query.answer()
    await query.message.answer(text, reply_markup=get_online_task_view_keyboard(tid))
    await state.update_data(tid=tid)
    await state.set_state(UserTaskStates.online_view)


# === НОВАЯ ЛОГИКА ПРОВЕРКИ ОНЛАЙН ЗАДАНИЙ В ТГ ===
@router.callback_query(F.data.startswith("check_online_"), UserTaskStates.online_view)
async def check_online(query: types.CallbackQuery, state: FSMContext):
    tid = int(query.data.split("_")[-1])
    await state.update_data(tid=tid)
    await query.message.answer(
        "Отправьте сообщение (текст, ссылку или фото), подтверждающее выполнение задания:",
        reply_markup=get_cancel_keyboard())
    await state.set_state(UserTaskStates.tg_online_await_proof)
    await query.answer()


@router.message(UserTaskStates.tg_online_await_proof)
async def receive_proof(message: types.Message, state: FSMContext, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]:
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        await message.answer("Отправка отменена.", reply_markup=get_role_menu_keyboard(role))
        return

    await state.update_data(proof_chat_id=message.chat.id, proof_message_id=message.message_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, отправить", callback_data="confirm_submit_online")
    builder.button(text="❌ Нет, отмена", callback_data="cancel_submit_online")
    await message.answer("Вы уверены, что хотите отправить это сообщение на проверку?",
                         reply_markup=builder.as_markup())
    await state.set_state(UserTaskStates.tg_online_confirm_proof)


@router.callback_query(F.data == "cancel_submit_online", UserTaskStates.tg_online_confirm_proof)
async def cancel_submit(query: types.CallbackQuery, state: FSMContext, user_service: IUserService):
    await query.message.answer("Отправка отменена.")
    role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    await query.message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
    await state.clear()
    await query.answer()


@router.callback_query(F.data == "confirm_submit_online", UserTaskStates.tg_online_confirm_proof)
async def confirm_submit(query: types.CallbackQuery, state: FSMContext,
                         online_task_service: IOnlineTaskService,
                         user_service: IUserService,
                         verify_chat_id: int):
    data = await state.get_data()
    tid = data['tid']
    proof_chat_id = data['proof_chat_id']
    proof_message_id = data['proof_message_id']
    uid = query.from_user.id
    source = Sources.TG
    bot = query.bot

    try:
        # 1. Создаём accepted_task со статусом IN_PROGRESS
        await online_task_service.submit_tg_online_task(uid, source, tid)

        # 2. Копируем ЛЮБОЕ сообщение пользователя в спец. чат (без плашки "Переслано от...")
        sent_msg = await bot.copy_message(
            chat_id=verify_chat_id,
            from_chat_id=proof_chat_id,
            message_id=proof_message_id
        )

        # 3. Отправляем инфо-сообщение с хэштегом #in_progress ответом на доказательство
        task = await online_task_service.get_task(tid)
        user = await user_service.get_user(uid, source)

        info_text = (
            f"#in_progress\n"
            f"📋 Онлайн задание #{task.id} на проверку\n"
            f"👤 Пользователь: {user.surname} {user.name} (ID: {uid}, TG)\n"
            f"📌 Тип: {task.type.value}\n"
            f"🏆 Награда: {task.reward} баллов\n"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Принять",
                       callback_data=f"tg_verify_accept_{uid}_{source.value}_{tid}")
        builder.button(text="❌ Отклонить",
                       callback_data=f"tg_verify_decline_{uid}_{source.value}_{tid}")

        await bot.send_message(
            verify_chat_id,
            info_text,
            reply_to_message_id=sent_msg.message_id,
            reply_markup=builder.as_markup()
        )

        await query.message.answer(
            "✅ Задание отправлено на проверку. Ожидайте решения администратора.")
        role = await user_service.get_user_role(uid, source)
        await query.message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
        await state.clear()
        await query.answer()
    except Exception as e:
        await query.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "back_online_list")
async def back_online_list(query: types.CallbackQuery, state: FSMContext,
                           online_task_service: IOnlineTaskService, user_service: IUserService):
    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    tasks, total_pages = await online_task_service.search_tasks(query.from_user.id, Sources.TG,
                                                                page=1, is_member=is_member_filter)
    await query.answer()
    await query.message.answer(
        f"Доступные задания (стр. 1/{total_pages}):",
        reply_markup=get_online_tasks_keyboard(tasks, 1, total_pages)
    )
    await state.update_data(page=1, total_pages=total_pages)
    await state.set_state(UserTaskStates.online_list)


@router.callback_query(F.data == "task_type_offline")
async def offline_list(query: types.CallbackQuery, state: FSMContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    if u.grade not in (UserGrade.AGITATOR, UserGrade.RESERVE):
        await query.answer()
        await query.message.answer(
            "Этот тип заданий открывается при достижении ранга 'Агитатор'. "
            "Для его прохождения необходимо пройти обучение.",
            reply_markup=get_role_menu_keyboard(u.role)
        )
        await state.clear()
        return

    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1,
                                                                     is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]

    if not tasks:
        await query.answer()
        await query.message.answer("Нет заданий в вашем регионе. Загляните к нам снова — скоро будут новые.",
                                   reply_markup=get_role_menu_keyboard(u.role))
        await state.clear()
        return
    await query.answer()
    await query.message.answer(
        f"Задания в вашем регионе (стр. 1/{total_pages}):",
        reply_markup=get_offline_tasks_keyboard(tasks, 1, total_pages)
    )
    await state.update_data(page=1, total_pages=total_pages)
    await state.set_state(UserTaskStates.offline_list)


@router.callback_query(F.data.startswith("next_offline_"), UserTaskStates.offline_list)
async def next_offline(query: types.CallbackQuery, state: FSMContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    page = int(query.data.split("_")[-1])
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=page,
                                                                     is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]
    if not tasks:
        await query.answer("Больше заданий в вашем регионе нет.", show_alert=True)
        return
    await query.answer()
    await query.message.answer(
        f"Задания в вашем регионе (стр. {page}/{total_pages}):",
        reply_markup=get_offline_tasks_keyboard(tasks, page, total_pages)
    )
    await state.update_data(page=page, total_pages=total_pages)


@router.callback_query(F.data.startswith("prev_offline_"), UserTaskStates.offline_list)
async def prev_offline(query: types.CallbackQuery, state: FSMContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    page = int(query.data.split("_")[-1])
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=page,
                                                                     is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]
    await query.answer()
    await query.message.answer(
        f"Задания в вашем регионе (стр. {page}/{total_pages}):",
        reply_markup=get_offline_tasks_keyboard(tasks, page, total_pages)
    )
    await state.update_data(page=page, total_pages=total_pages)


@router.callback_query(F.data.startswith("view_offline_"))
async def view_offline(query: types.CallbackQuery, state: FSMContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    tid = int(query.data.split("_")[-1])
    task = await offline_task_service.get_task(tid)
    u = await user_service.get_user(query.from_user.id, Sources.TG)

    active_tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, 1)
    period_str = f"{task.start_date.strftime('%d.%m.%Y')} - {task.end_date.strftime('%d.%m.%Y')}"
    text = (f"📋 {task.title}\n"
            f"📅 Период: {period_str}\n"
            f"📝 {task.description}\n"
            f"📍 {task.location}\n"
            f"📞 {task.contacts}\n"
            f"🏆 {task.reward} баллов")

    await query.answer()
    await query.message.answer(text, reply_markup=get_offline_task_view_keyboard(tid))
    await state.update_data(tid=tid)
    await state.set_state(UserTaskStates.offline_view)


@router.callback_query(F.data.startswith("accept_offline_"), UserTaskStates.offline_view)
async def accept_offline(query: types.CallbackQuery, state: FSMContext,
                         offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService,
                         user_service: IUserService):
    tid = int(query.data.split("_")[-1])
    try:
        await offline_task_service.accept_offline_task(query.from_user.id, Sources.TG, tid)
        role = await user_service.get_user_role(query.from_user.id, Sources.TG)
        await query.answer()
        await query.message.answer(
            "✅ Задача принята. Свяжитесь с местным отделением по контактам в описании.",
            reply_markup=get_role_menu_keyboard(role)
        )
        await notification_service.notify_user(query.from_user.id, Sources.TG,
                                               f"Вы взяли офлайн задачу #{tid}. Ожидает проверки.")
        await state.clear()
    except DomainError as e:
        await query.answer(str(e), show_alert=True)


@router.callback_query(F.data == "back_offline_list")
async def back_offline_list(query: types.CallbackQuery, state: FSMContext,
                            offline_task_service: IOfflineTaskService, user_service: IUserService):
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    is_member_filter = await _get_task_filter(user_service, query.from_user.id)
    all_tasks, total_pages = await offline_task_service.search_tasks(u.id, u.source, page=1, is_member=is_member_filter)
    tasks = [t for t in all_tasks if t.region == u.region]
    await query.answer()
    await query.message.answer(
        f"Задания в регионе (стр. 1/{total_pages}):",
        reply_markup=get_offline_tasks_keyboard(tasks, 1, total_pages)
    )
    await state.update_data(page=1, total_pages=total_pages)
    await state.set_state(UserTaskStates.offline_list)


@router.message(F.text == "Мои задания")
async def my_tasks(message: types.Message, state: FSMContext,
                   offline_task_service: IOfflineTaskService, user_service: IUserService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        await message.answer("У вас нет активных заданий.",
                             reply_markup=get_role_menu_keyboard(u.role))
        return

    await message.answer("Ваши задания:", reply_markup=get_my_tasks_keyboard(tasks))
    await state.set_state(UserTaskStates.my_tasks)


@router.callback_query(F.data.startswith("view_my_task_"))
async def view_my_task(query: types.CallbackQuery, state: FSMContext,
                       offline_task_service: IOfflineTaskService, user_service: IUserService):
    tid = int(query.data.split("_")[-1])
    task = await offline_task_service.get_task(tid)
    if not task:
        await query.answer("Ошибка: задание не найдено", show_alert=True)
        return

    user_tasks, _ = await offline_task_service.get_user_tasks(query.from_user.id, Sources.TG,
                                                              page=1)
    accepted = next((t for t in user_tasks if t.task and t.task.id == tid), None)

    text = (f"📋 {task.title}\n"
            f"📝 {task.description}\n"
            f"📍 {task.location}\n"
            f"📞 {task.contacts}\n"
            f"💰 {task.reward} баллов")

    is_in_progress = accepted and accepted.status.value == "в процессе"
    await query.answer()
    await query.message.answer(text, reply_markup=get_my_task_view_keyboard(tid, is_in_progress))


@router.callback_query(F.data.startswith("cancel_my_task_"))
async def cancel_my_task(query: types.CallbackQuery, state: FSMContext,
                         offline_task_service: IOfflineTaskService,
                         notification_service: INotificationService,
                         user_service: IUserService):
    tid = int(query.data.split("_")[-1])
    try:
        await offline_task_service.cancel_task(query.from_user.id, Sources.TG, tid)
        await notification_service.notify_user(query.from_user.id, Sources.TG,
                                               f"Задание #{tid} отменено.")
        role = await user_service.get_user_role(query.from_user.id, Sources.TG)
        await query.answer()
        await query.message.answer(f"✅ Задание #{tid} успешно отменено.",
                                   reply_markup=get_role_menu_keyboard(role))
        await state.clear()
    except Exception as e:
        await query.answer(f"Ошибка при отмене: {e}", show_alert=True)


@router.callback_query(F.data == "back_to_my_tasks")
async def back_to_my_tasks(query: types.CallbackQuery, state: FSMContext,
                           offline_task_service: IOfflineTaskService, user_service: IUserService):
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    tasks, _ = await offline_task_service.get_user_tasks(u.id, u.source, page=1)
    if not tasks:
        await query.answer()
        await query.message.answer("У вас нет активных заданий.",
                                   reply_markup=get_role_menu_keyboard(u.role))
        await state.clear()
        return

    await query.answer()
    await query.message.answer("Ваши задания:", reply_markup=get_my_tasks_keyboard(tasks))


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(query: types.CallbackQuery, state: FSMContext, user_service: IUserService):
    role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    await query.answer()
    await query.message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
    await state.clear()