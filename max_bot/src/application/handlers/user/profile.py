import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, InputMedia
from maxapi.context import MemoryContext
from src.application.states import ProfileStates
from src.application.keyboards.profile_keyboard import get_profile_kb, get_back_kb
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.services.interfaces import IUserService, IReferralService, IBalanceService, \
    ILearningService, IOrderService, IClosedEventService, IReferralLinkService
from src.domain.entities.user import Sources

logger = logging.getLogger(__name__)
router = Router()


@router.message_created(F.message.body.text == "Личный кабинет")
async def profile(event: MessageCreated, context: MemoryContext, user_service: IUserService,
                  referral_service: IReferralService, balance_service: IBalanceService,
                  learning_service: ILearningService):
    try:
        u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
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
        await event.message.answer(text, attachments=[get_profile_kb().as_markup()])
        await context.set_state(ProfileStates.MENU)
    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        await event.message.answer("Ошибка загрузки профиля")


@router.message_created(F.message.body.text == "Реферальная ссылка")
async def referral_link(event: MessageCreated, context: MemoryContext,
                        referral_link_service: IReferralLinkService):
    repost_data = referral_link_service.generate_post(event.from_user.user_id)
    vk_ref = f"{referral_link_service.vk_bot_link}?ref={event.from_user.user_id}_{referral_link_service.source.value}"
    tg_ref = f"{referral_link_service.tg_bot_link}?start={event.from_user.user_id}_{referral_link_service.source.value}"
    max_ref = f"{referral_link_service.max_bot_link}?start={event.from_user.user_id}_{referral_link_service.source.value}"

    links_text = (
        "🔗 Ваши реферальные ссылки:\n"
        f"🔹 ВКонтакте: {vk_ref}\n"
        f"🔹 Макс: {max_ref}\n"
        f"🔹 Telegram: {tg_ref}\n"
        "Копируйте и отправляйте друзьям!"
    )
    await event.message.answer(links_text)

    try:
        media = InputMedia(repost_data.image_path)
        attachment = await event.bot.upload_media(media)
        await event.message.answer(attachments=[attachment, get_back_kb().as_markup()])
    except Exception as e:
        logger.error(f"Failed to send repost image: {e}")
        await event.message.answer(repost_data.text, attachments=[get_back_kb().as_markup()])

    await context.set_state(ProfileStates.REFERRALS)


@router.message_created(F.message.body.text == "Список покупок")
async def orders_history(event: MessageCreated, context: MemoryContext,
                         order_service: IOrderService):
    orders = await order_service.get_user_orders_history(event.from_user.user_id, Sources.MAX)
    if not orders:
        await event.message.answer("У вас пока нет покупок.",
                                   attachments=[get_back_kb().as_markup()])
        await context.set_state(ProfileStates.ORDERS)
        return

    lines = ["🛍 Ваши покупки:"]
    for o in orders:
        status_map = {"ожидание": "Ожидает", "завершено": "Получен", "отклонено": "Отменен"}
        status_text = status_map.get(o.status.value, o.status.value)
        lines.append(f"- {o.product_name} | {status_text} | {o.created_at.strftime('%d.%m.%Y')}")

    await event.message.answer("\n".join(lines), attachments=[get_back_kb().as_markup()])
    await context.set_state(ProfileStates.ORDERS)


@router.message_created(F.message.body.text == "Список мероприятий")
async def events_history(event: MessageCreated, context: MemoryContext,
                         closed_event_service: IClosedEventService):
    events = await closed_event_service.get_user_events(event.from_user.user_id, Sources.MAX)
    if not events:
        await event.message.answer("Вы пока не записаны ни на одно мероприятие.",
                                   attachments=[get_back_kb().as_markup()])
        await context.set_state(ProfileStates.EVENTS)
        return

    lines = ["📅 Ваши мероприятия:"]
    for e in events:
        lines.append(
            f"- {e.title} | {e.date.strftime('%d.%m.%Y')} {e.time.strftime('%H:%M')} | {e.location}")

    await event.message.answer("\n".join(lines), attachments=[get_back_kb().as_markup()])
    await context.set_state(ProfileStates.EVENTS)


@router.message_created(F.message.body.text == "Посмотреть рейтинг")
async def show_rating(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    user_score = await user_service.get_user_rating(u.id, u.source)
    global_top = await user_service.get_global_top(10)
    local_top = await user_service.get_local_top(u.region, 10)

    text = f"🏆 Ваш рейтинг: {user_score} баллов\n"
    text += "🌍 Глобальный рейтинг (Топ-10):\n"
    if not global_top:
        text += "Пока нет данных.\n"
    else:
        for i, entry in enumerate(global_top, 1):
            marker = " 👈 (Это вы!)" if entry["uid"] == u.id else ""
            text += f"{i}. {entry['name']} - {entry['score']}{marker}\n"

    text += f"\n📍 Локальный рейтинг ({u.region}, Топ-10):\n"
    if not local_top:
        text += "Пока нет данных.\n"
    else:
        for i, entry in enumerate(local_top, 1):
            marker = " 👈 (Это вы!)" if entry["uid"] == u.id else ""
            text += f"{i}. {entry['name']} - {entry['score']}{marker}\n"

    await event.message.answer(text, attachments=[get_back_kb().as_markup()])
    await context.set_state(ProfileStates.RATING)


@router.message_created(F.message.body.text == "Назад")
async def back_to_profile(event: MessageCreated, context: MemoryContext, user_service: IUserService,
                          referral_service: IReferralService, balance_service: IBalanceService,
                          learning_service: ILearningService):
    await profile(event, context, user_service, referral_service, balance_service, learning_service)


@router.message_created(F.message.body.text == "На главную")
async def back_to_main(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Главное меню",
                               attachments=[get_role_menu_keyboard(role).as_markup()])
    await context.clear()
