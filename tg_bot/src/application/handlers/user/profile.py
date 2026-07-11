import logging

import aiohttp
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from src.application.states import ProfileStates
from src.services.interfaces import (IUserService, IReferralService, IBalanceService,
                                     ILearningService, IOrderService, IClosedEventService,
                                     IReferralLinkService, IHeadlinerService)
from src.domain.entities.user import Sources, UserRole
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


def get_profile_kb():
    """Клавиатура личного кабинета"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="Реферальная ссылка")
    builder.button(text="Список покупок")
    builder.button(text="Список мероприятий")
    builder.button(text="Посмотреть рейтинг")
    builder.button(text="На главную")
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup(resize_keyboard=True)


def get_back_kb():
    """Клавиатура возврата"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="Назад")
    builder.button(text="На главную")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# ==================== ГЛАВНОЕ МЕНЮ ПРОФИЛЯ ====================
@router.message(F.text == "Личный кабинет")
async def profile(message: Message, state: FSMContext, user_service: IUserService,
                  referral_service: IReferralService, balance_service: IBalanceService,
                  learning_service: ILearningService, headliner_service: IHeadlinerService):
    try:
        u = await user_service.get_user(message.from_user.id, Sources.TG)
        balance = await balance_service.get_balance(u.id, u.source)
        refs = await referral_service.get_count_invitees(u.id, u.source)
        on_count = await user_service.get_completed_tasks_count(u.id, u.source, True)
        off_count = await user_service.get_completed_tasks_count(u.id, u.source, False)
        is_passed = await learning_service.is_learning_passed(u.id, u.source)

        text = (
            f"👤 Ваш ранг - {u.grade.value}\n"
            f"🌍 Ваш регион - {u.region}\n"
            f"💰 Количество баллов - {balance}\n"
            f"👥 Количество приглашённых людей - {refs}\n"
            f"🏢 Количество выполненных офлайн заданий - {off_count}\n"
            f"💻 Количество выполненных онлайн заданий - {on_count}\n"
            f"🎓 Обучение пройдено - {'да' if is_passed else 'нет'}\n"
            f"📅 Дата регистрации - {u.created_at.strftime('%d.%m.%Y')}"
        )
        if u.role == UserRole.HEADLINER:
            headliner = await headliner_service.get_by_user(u.id, u.source)
            if headliner:
                followers_count = await headliner_service.count_followers(headliner.id)
                text += (
                    f"\n\n👑 Хэдлайнер: {headliner.fio}"
                    f"\n💼 Должность: {headliner.position}"
                    f"\n🎯 Тема: {headliner.topic}"
                    f"\n👥 Последователей: {followers_count}"
                )
        await message.answer(text, reply_markup=get_profile_kb())
        await state.set_state(ProfileStates.menu)
    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        await message.answer("Ошибка загрузки профиля")


# ==================== РЕФЕРАЛЬНАЯ ССЫЛКА ====================
@router.message(ProfileStates.menu, F.text == "Реферальная ссылка")
@router.message(F.text == "Реферальная ссылка")
async def referral_link(message: Message, state: FSMContext,
                        referral_link_service: IReferralLinkService,
                        headliner_service: IHeadlinerService):
    # 1. Проверяем, является ли пользователь хедлайнером
    headliner = await headliner_service.get_by_user(message.from_user.id, Sources.TG)
    if headliner:
        links = headliner_service.make_referral_links(headliner.id)
        links_text = (
            "👑 Ваши ссылки хэдлайнера:\n"
            f"🔹 VK: {links['VK']}\n"
            f"🔹 MAX: {links['MAX']}\n"
            f"🔹 Telegram: {links['Telegram']}\n\n"
            "Все зарегистрированные по этим ссылкам попадут в вашу команду."
        )

        # Если у хедлайнера есть фото, скачиваем его и отправляем как фото с подписью
        if headliner.photo:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(headliner.photo) as resp:
                        if resp.status == 200:
                            image_bytes = await resp.read()
                            photo_file = BufferedInputFile(image_bytes, filename="headliner.jpg")
                            await message.answer_photo(
                                photo=photo_file,
                                caption=links_text,
                                reply_markup=get_back_kb()
                            )
                            await state.set_state(ProfileStates.referrals)
                            return
            except Exception as e:
                logger.error(f"Failed to send headliner photo: {e}")

        # Если фото нет или оно не загрузилось, отправляем просто текст
        await message.answer(links_text, reply_markup=get_back_kb())
        await state.set_state(ProfileStates.referrals)
        return

    # 2. Стандартная логика генерации ссылок для обычных пользователей
    repost_data = referral_link_service.generate_post(message.from_user.id)
    vk_ref = f"{referral_link_service.vk_bot_link}?ref={message.from_user.id}_{referral_link_service.source.value}"
    tg_ref = f"{referral_link_service.tg_bot_link}?start={message.from_user.id}_{referral_link_service.source.value}"
    max_ref = f"{referral_link_service.max_bot_link}?start={message.from_user.id}_{referral_link_service.source.value}"

    links_text = (
        "🔗 Ваши реферальные ссылки:\n"
        f"🔹 ВКонтакте: {vk_ref}\n"
        f"🔹 Макс: {max_ref}\n"
        f"🔹 Telegram: {tg_ref}\n"
        "Копируйте и отправляйте друзьям!"
    )
    await message.answer(links_text)

    # Читаем локальный файл через FSInputFile
    try:
        photo_file = FSInputFile(repost_data.image_path)
        await message.answer_photo(
            photo=photo_file,
            caption=repost_data.text,
            reply_markup=get_back_kb()
        )
    except Exception as e:
        logger.error(f"Failed to send repost image from path {repost_data.image_path}: {e}")
        await message.answer(repost_data.text, reply_markup=get_back_kb())

    await state.set_state(ProfileStates.referrals)


# ==================== СПИСОК ПОКУПОК ====================
@router.message(ProfileStates.menu, F.text == "Список покупок")
async def orders_history(message: Message, state: FSMContext, order_service: IOrderService):
    orders = await order_service.get_user_orders_history(message.from_user.id, Sources.TG)
    if not orders:
        await message.answer("У вас пока нет покупок.", reply_markup=get_back_kb())
        await state.set_state(ProfileStates.orders)
        return

    lines = ["🛍 Ваши покупки:"]
    for o in orders:
        status_map = {"ожидание": "Ожидает", "завершено": "Получен", "отклонено": "Отменен"}
        status_text = status_map.get(o.status.value, o.status.value)
        lines.append(f"- {o.product_name} | {status_text} | {o.created_at.strftime('%d.%m.%Y')}")

    await message.answer("\n".join(lines), reply_markup=get_back_kb())
    await state.set_state(ProfileStates.orders)


# ==================== СПИСОК МЕРОПРИЯТИЙ ====================
@router.message(ProfileStates.menu, F.text == "Список мероприятий")
async def events_history(message: Message, state: FSMContext,
                         closed_event_service: IClosedEventService):
    events = await closed_event_service.get_user_events(message.from_user.id, Sources.TG)
    if not events:
        await message.answer("Вы пока не записаны ни на одно мероприятие.",
                             reply_markup=get_back_kb())
        await state.set_state(ProfileStates.events)
        return

    lines = ["📅 Ваши мероприятия:"]
    for e in events:
        lines.append(
            f"- {e.title} | {e.date.strftime('%d.%m.%Y')} {e.time.strftime('%H:%M')} | {e.location}")

    await message.answer("\n".join(lines), reply_markup=get_back_kb())
    await state.set_state(ProfileStates.events)


# ==================== РЕЙТИНГ ====================
@router.message(ProfileStates.menu, F.text == "Посмотреть рейтинг")
async def show_rating(message: Message, state: FSMContext, user_service: IUserService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    user_score = await user_service.get_user_rating(u.id, u.source)
    global_top = await user_service.get_global_top(10)
    local_top = await user_service.get_local_top(u.region, 10)

    text = f"🏆 Ваш рейтинг: {user_score} баллов\n\n"
    text += "🌍 Глобальный рейтинг (Топ-10):\n"
    if not global_top:
        text += "Пока нет данных.\n"
    else:
        user_in_global = False
        for i, entry in enumerate(global_top, 1):
            marker = " 👈 (Это вы!)" if entry["uid"] == u.id else ""
            text += f"{i}. {entry['name']} - {entry['score']}{marker}\n"
            if entry["uid"] == u.id:
                user_in_global = True
        if not user_in_global:
            text += "... Вы не в топ-10.\n"

    text += f"\n📍 Локальный рейтинг ({u.region}, Топ-10):\n"
    if not local_top:
        text += "Пока нет данных.\n"
    else:
        user_in_local = False
        for i, entry in enumerate(local_top, 1):
            marker = " 👈 (Это вы!)" if entry["uid"] == u.id else ""
            text += f"{i}. {entry['name']} - {entry['score']}{marker}\n"
            if entry["uid"] == u.id:
                user_in_local = True
        if not user_in_local:
            text += "... Вы не в топ-10.\n"

    await message.answer(text, reply_markup=get_back_kb())
    await state.set_state(ProfileStates.rating)


# ==================== НАВИГАЦИЯ "НАЗАД" (ИСПРАВЛЕНО: СТЕК ДЕКОРАТОРОВ) ====================
@router.message(F.text == "Назад", ProfileStates.referrals)
@router.message(F.text == "Назад", ProfileStates.orders)
@router.message(F.text == "Назад", ProfileStates.events)
@router.message(F.text == "Назад", ProfileStates.rating)
async def back_to_profile(message: Message, state: FSMContext, user_service: IUserService,
                          referral_service: IReferralService, balance_service: IBalanceService,
                          learning_service: ILearningService):
    # Возвращаемся к главному меню профиля
    await profile(message, state, user_service, referral_service, balance_service, learning_service)


# ==================== НАВИГАЦИЯ "НА ГЛАВНУЮ" (ИСПРАВЛЕНО: СТЕК ДЕКОРАТОРОВ) ====================
@router.message(F.text == "На главную", ProfileStates.menu)
@router.message(F.text == "На главную", ProfileStates.referrals)
@router.message(F.text == "На главную", ProfileStates.orders)
@router.message(F.text == "На главную", ProfileStates.events)
@router.message(F.text == "На главную", ProfileStates.rating)
async def back_to_main(message: Message, state: FSMContext, user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
    await state.clear()
