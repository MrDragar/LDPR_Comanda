import logging
import aiohttp

from vkbottle import Keyboard, PhotoMessageUploader, Text
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.states import ProfileStates
from src.domain.entities.user import Sources, UserRole
from src.services.interfaces import (IBalanceService, IClosedEventService, IHeadlinerService,
                                     ILearningService, IOrderService, IReferralLinkService,
                                     IReferralService, IUserService)

logger = logging.getLogger(__name__)
router = BotLabeler()


def get_profile_kb():
    return (Keyboard(one_time=False)
            .add(Text("Реферальная ссылка")).row()
            .add(Text("Список покупок")).row()
            .add(Text("Список мероприятий")).row()
            .add(Text("Посмотреть рейтинг")).row()
            .add(Text("На главную")).get_json())


def get_back_kb():
    return (Keyboard(one_time=False)
            .add(Text("Назад")).row()
            .add(Text("На главную")).get_json())


async def _get_main_menu_kb(user_service: IUserService, user_id: int) -> str:
    """Безопасное получение клавиатуры главного меню по роли"""
    try:
        role = await user_service.get_user_role(user_id, Sources.VK)
        return get_role_menu_keyboard(role)
    except Exception:
        return get_role_menu_keyboard(UserRole.USER)


@router.message(text=["Личный кабинет"])
async def profile(message: Message, user_service: IUserService, referral_service: IReferralService,
                  balance_service: IBalanceService, learning_service: ILearningService,
                  headliner_service: IHeadlinerService, state_dispenser: BuiltinStateDispenser):
    try:
        # Устанавливаем стейт главного меню ЛК
        await state_dispenser.set(message.from_id, ProfileStates.MAIN)

        u = await user_service.get_user(message.from_id, Sources.VK)
        balance = await balance_service.get_balance(u.id, u.source)
        refs = await referral_service.get_count_invitees(u.id, u.source)
        on_count = await user_service.get_completed_tasks_count(u.id, u.source, True)
        off_count = await user_service.get_completed_tasks_count(u.id, u.source, False)
        is_passed = await learning_service.is_learning_passed(u.id, u.source)

        text = (
            f"Ваш ранг - {u.grade.value}\n"
            f"Ваша роль - {u.role.value}\n"
            f"Ваш регион - {u.region}\n"
            f"Количество баллов - {balance}\n"
            f"Количество приглашённых людей - {refs}\n"
            f"Количество выполненных офлайн заданий - {off_count}\n"
            f"Количество выполненных онлайн заданий - {on_count}\n"
            f"Обучение пройдено - {'да' if is_passed else 'нет'}\n"
            f"Дата регистрации - {u.created_at.strftime('%d.%m.%Y')}"
        )

        if u.role == UserRole.HEADLINER:
            headliner = await headliner_service.get_by_user(u.id, u.source)
            if headliner:
                followers_count = await headliner_service.count_followers(headliner.id)
                text += (
                    f"\n\nХэдлайнер: {headliner.fio}\n"
                    f"Должность: {headliner.position}\n"
                    f"Тема: {headliner.topic}\n"
                    f"Последователей: {followers_count}"
                )

        await message.answer(text, keyboard=get_profile_kb())
    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        await message.answer("Ошибка загрузки профиля")


# ==================== ПОДМЕНЮ ЛК ====================
# ==================== РЕФЕРАЛЬНАЯ ССЫЛКА ====================
@router.message(state=ProfileStates.MAIN, text=["Реферальная ссылка"])
@router.message(text=["Реферальная ссылка"])
async def referral_link(message: Message, referral_link_service: IReferralLinkService,
                        photo_uploader: PhotoMessageUploader,
                        headliner_service: IHeadlinerService,
                        state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, ProfileStates.REFERRAL)
    headliner = await headliner_service.get_by_user(message.from_id, Sources.VK)

    if headliner:
        links = headliner_service.make_referral_links(headliner.id)
        links_text = (
            "Ваши ссылки хэдлайнера:\n"
            f"VK: {links['VK']}\n"
            f"MAX: {links['MAX']}\n"
            f"Telegram: {links['Telegram']}\n"
            "Все зарегистрированные по этим ссылкам попадут в вашу команду."
        )

        # Если у хедлайнера есть фото, скачиваем его и отправляем как вложение
        if headliner.photo:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(headliner.photo) as resp:
                        if resp.status == 200:
                            file_bytes = await resp.read()
                            photo = await photo_uploader.upload(file_source=file_bytes,
                                                                peer_id=message.peer_id)
                            return await message.answer(links_text, attachment=photo,
                                                        keyboard=get_back_kb())
            except Exception as e:
                logger.error(f"Failed to upload headliner photo: {e}")

        # Если фото нет или оно не загрузилось, отправляем просто текст
        return await message.answer(links_text, keyboard=get_back_kb())

    # Стандартная логика для обычных пользователей (остается без изменений)
    repost_data = referral_link_service.generate_post(message.from_id)
    vk_ref = f"{referral_link_service.vk_bot_link}?ref={message.from_id}_{referral_link_service.source.value}"
    tg_ref = f"{referral_link_service.tg_bot_link}?start={message.from_id}_{referral_link_service.source.value}"
    max_ref = (f"{referral_link_service.max_bot_link}?start={message.from_id}"
               f"_{referral_link_service.source.value}")

    links_text = (
        "Ваши реферальные ссылки:\n\n"
        f"ВКонтакте: {vk_ref}\n"
        f"Макс: {max_ref}\n"
        f"Telegram: {tg_ref}\n\n"
        "Копируйте и отправляйте друзьям!"
    )
    await message.answer(links_text, keyboard=get_back_kb())

    photo = await photo_uploader.upload(repost_data.image_path, peer_id=message.peer_id)
    await message.answer(
        message=repost_data.text,
        attachment=photo,
        keyboard=get_back_kb()
    )


@router.message(state=ProfileStates.MAIN, text=["Список покупок"])
async def orders_history(message: Message, order_service: IOrderService,
                         state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, ProfileStates.ORDERS)
    orders = await order_service.get_user_orders_history(message.from_id, Sources.VK)
    if not orders:
        return await message.answer("У вас пока нет покупок.", keyboard=get_back_kb())

    lines = ["Ваши покупки:"]
    for o in orders:
        # ИСПРАВЛЕНО: ключи теперь соответствуют реальным значениям из Enum OrderStatus
        status_map = {"ожидание": "Ожидает", "завершено": "Получен", "отклонено": "Отменен"}
        status_text = status_map.get(o.status.value, o.status.value)
        lines.append(f"- {o.product_name} | {status_text} | {o.created_at.strftime('%d.%m.%Y')}")

    await message.answer("\n".join(lines), keyboard=get_back_kb())


@router.message(state=ProfileStates.MAIN, text=["Список мероприятий"])
async def events_history(message: Message, closed_event_service: IClosedEventService,
                         state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, ProfileStates.EVENTS)
    events = await closed_event_service.get_user_events(message.from_id, Sources.VK)
    if not events:
        return await message.answer("Вы пока не записаны ни на одно мероприятие.",
                                    keyboard=get_back_kb())

    lines = ["Ваши мероприятия:"]
    for e in events:
        lines.append(
            f"- {e.title} | {e.date.strftime('%d.%m.%Y')} {e.time.strftime('%H:%M')} | {e.location}")

    await message.answer("\n".join(lines), keyboard=get_back_kb())


@router.message(state=ProfileStates.MAIN, text=["Посмотреть рейтинг"])
async def show_rating(message: Message, user_service: IUserService,
                      state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, ProfileStates.RATING)
    u = await user_service.get_user(message.from_id, Sources.VK)
    user_score = await user_service.get_user_rating(u.id, u.source)

    global_top = await user_service.get_global_top(10)
    local_top = await user_service.get_local_top(u.region, 10)

    text = f"Ваш рейтинг: {user_score} баллов\n\n"
    text += "Глобальный рейтинг (Топ-10):\n"
    if not global_top:
        text += "Пока нет данных.\n"
    else:
        for i, entry in enumerate(global_top, 1):
            marker = " (Это вы!)" if entry["uid"] == u.id else ""
            text += f"{i}. {entry['name']} - {entry['score']}{marker}\n"

    text += f"\nЛокальный рейтинг ({u.region}, Топ-10):\n"
    if not local_top:
        text += "Пока нет данных.\n"
    else:
        for i, entry in enumerate(local_top, 1):
            marker = " (Это вы!)" if entry["uid"] == u.id else ""
            text += f"{i}. {entry['name']} - {entry['score']}{marker}\n"

    await message.answer(text, keyboard=get_back_kb())


# ==================== НАВИГАЦИЯ НАЗАД / В ГЛАВНОЕ МЕНЮ ====================

@router.message(state=[ProfileStates.REFERRAL, ProfileStates.ORDERS, ProfileStates.EVENTS,
                       ProfileStates.RATING], text=["Назад"])
async def back_to_profile(message: Message, user_service: IUserService,
                          referral_service: IReferralService,
                          balance_service: IBalanceService, learning_service: ILearningService,
                          headliner_service: IHeadlinerService,
                          state_dispenser: BuiltinStateDispenser):
    """Возврат в главное меню Личного кабинета"""
    await profile(message, user_service, referral_service, balance_service, learning_service,
                  headliner_service, state_dispenser)


@router.message(
    state=[
        ProfileStates.MAIN,
        ProfileStates.REFERRAL,
        ProfileStates.ORDERS,
        ProfileStates.EVENTS,
        ProfileStates.RATING
    ], 
    text=["На главную"]
)
async def go_to_main_menu(message: Message, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    """Полный выход из ЛК в главное меню бота"""
    await state_dispenser.delete(message.from_id)
    kb = await _get_main_menu_kb(user_service, message.from_id)
    await message.answer("Главное меню:", keyboard=kb)
