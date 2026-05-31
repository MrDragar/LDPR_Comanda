import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text, PhotoMessageUploader
from src.services.interfaces import (IUserService, IReferralService, IBalanceService,
                                     ILearningService, IOrderService, IClosedEventService,
                                     IReferralLinkService)
from src.domain.entities.user import Sources

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


@router.message(text=["Личный кабинет"])
async def profile(message: Message, user_service: IUserService, referral_service: IReferralService,
                  balance_service: IBalanceService, learning_service: ILearningService):
    try:
        u = await user_service.get_user(message.from_id, Sources.VK)
        balance = await balance_service.get_balance(u.id, u.source)
        refs = await referral_service.get_count_invitees(u.id, u.source)
        on_count = await user_service.get_completed_tasks_count(u.id, u.source, True)
        off_count = await user_service.get_completed_tasks_count(u.id, u.source, False)
        is_passed = await learning_service.is_learning_passed(u.id, u.source)

        text = (
            f"Ваш ранг - {u.grade.value}\n"
            f"Ваш регион - {u.region}\n"
            f"Количество баллов - {balance}\n"
            f"Количество приглашённых людей - {refs}\n"
            f"Количество выполненных офлайн заданий - {off_count}\n"
            f"Количество выполненных онлайн заданий - {on_count}\n"
            f"Обучение пройдено - {'да' if is_passed else 'нет'}\n"
            f"Дата регистрации - {u.created_at.strftime('%d.%m.%Y')}"
        )
        await message.answer(text, keyboard=get_profile_kb())
    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        await message.answer("Ошибка загрузки профиля")


@router.message(text=["Реферальная ссылка"])
async def referral_link(message: Message, referral_link_service: IReferralLinkService,
                        photo_uploader: PhotoMessageUploader):
    repost_data = referral_link_service.generate_post(message.from_id)

    # 1️⃣ Сообщение с прямыми ссылками для копирования
    vk_ref = f"{referral_link_service.vk_bot_link}?ref={message.from_id}_{referral_link_service.source.value}"
    tg_ref = f"{referral_link_service.tg_bot_link}?start={message.from_id}_{referral_link_service.source.value}"

    links_text = (
        "🔗 Ваши реферальные ссылки:\n\n"
        f"🔹 ВКонтакте: {vk_ref}\n"
        f"🔹 Telegram: {tg_ref}\n\n"
        "Копируйте и отправляйте друзьям!"
    )
    await message.answer(links_text, keyboard=get_back_kb())

    # 2️⃣ Сообщение для репоста с картинкой
    photo = await photo_uploader.upload(repost_data.image_path, peer_id=message.peer_id)
    await message.answer(
        message=repost_data.text,
        attachment=photo,
        keyboard=get_back_kb()
    )


@router.message(text=["Список покупок"])
async def orders_history(message: Message, order_service: IOrderService):
    orders = await order_service.get_user_orders_history(message.from_id, Sources.VK)
    if not orders:
        return await message.answer("У вас пока нет покупок.", keyboard=get_back_kb())

    lines = ["🛍 Ваши покупки:"]
    for o in orders:
        status_map = {"pending": "Ожидает", "completed": "Получен", "cancelled": "Отменен"}
        status_text = status_map.get(o.status.value, o.status.value)
        lines.append(f"- {o.product_name} | {status_text} | {o.created_at.strftime('%d.%m.%Y')}")

    await message.answer("\n".join(lines), keyboard=get_back_kb())


@router.message(text=["Список мероприятий"])
async def events_history(message: Message, closed_event_service: IClosedEventService):
    events = await closed_event_service.get_user_events(message.from_id, Sources.VK)
    if not events:
        return await message.answer("Вы пока не записаны ни на одно мероприятие.",
                                    keyboard=get_back_kb())

    lines = ["📅 Ваши мероприятия:"]
    for e in events:
        lines.append(
            f"- {e.title} | {e.date.strftime('%d.%m.%Y')} {e.time.strftime('%H:%M')} | {e.location}")

    await message.answer("\n".join(lines), keyboard=get_back_kb())


@router.message(text=["Посмотреть рейтинг"])
async def show_rating(message: Message, user_service: IUserService):
    u = await user_service.get_user(message.from_id, Sources.VK)
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
            if entry["uid"] == u.id: user_in_global = True
        if not user_in_global:
            text += f"... Вы не в топ-10.\n"

    text += f"\n📍 Локальный рейтинг ({u.region}, Топ-10):\n"
    if not local_top:
        text += "Пока нет данных.\n"
    else:
        user_in_local = False
        for i, entry in enumerate(local_top, 1):
            marker = " 👈 (Это вы!)" if entry["uid"] == u.id else ""
            text += f"{i}. {entry['name']} - {entry['score']}{marker}\n"
            if entry["uid"] == u.id: user_in_local = True
        if not user_in_local:
            text += f"... Вы не в топ-10.\n"

    await message.answer(text, keyboard=get_back_kb())


@router.message(text=["Назад"])
async def back_to_profile(message: Message, user_service: IUserService,
                          referral_service: IReferralService,
                          balance_service: IBalanceService, learning_service: ILearningService):
    # Возврат в личный кабинет
    await profile(message, user_service, referral_service, balance_service, learning_service)