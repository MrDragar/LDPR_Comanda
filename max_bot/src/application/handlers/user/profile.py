import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageButton, InputMedia
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.services.interfaces import IUserService, IReferralService, IBalanceService, \
    ILearningService, IReferralLinkService
from src.domain.entities.user import Sources

logger = logging.getLogger(__name__)
router = Router()


def get_profile_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Реферальная ссылка"))
    # builder.row(MessageButton(text="Список покупок"))
    # builder.row(MessageButton(text="Список мероприятий"))
    # builder.row(MessageButton(text="Посмотреть рейтинг"))
    builder.row(MessageButton(text="На главную"))
    return builder


def get_back_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Назад"))
    builder.row(MessageButton(text="На главную"))
    return builder


@router.message_created(F.message.body.text == "Личный кабинет")
async def profile(
    event: MessageCreated, user_service: IUserService, referral_service: IReferralService,
    balance_service: IBalanceService, learning_service: ILearningService
):
    try:
        u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
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
        await event.message.answer(text, attachments=[get_profile_kb().as_markup()])
    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        await event.message.answer("Ошибка загрузки профиля")


@router.message_created(F.message.body.text == "Назад")
async def back_to_profile(
    event: MessageCreated, user_service: IUserService, referral_service: IReferralService,
    balance_service: IBalanceService, learning_service: ILearningService
):
    await profile(event, user_service, referral_service, balance_service, learning_service)


@router.message_created(F.message.body.text == "Реферальная ссылка")
async def referral_link(
        event: MessageCreated, referral_link_service: IReferralLinkService
):
    user_id = event.from_user.user_id
    repost_data = referral_link_service.generate_post(user_id)

    vk_ref = f"{referral_link_service.vk_bot_link}?ref={user_id}_{referral_link_service.source.value}"
    tg_ref = f"{referral_link_service.tg_bot_link}?start={user_id}_{referral_link_service.source.value}"
    max_ref = f"{referral_link_service.max_bot_link}?start={user_id}_{referral_link_service.source.value}"

    links_text = (
        "🔗 Ваши реферальные ссылки:\n"
        f"🔹 ВКонтакте: {vk_ref}\n"
        f"🔹 Telegram: {tg_ref}\n"
        f"🔹 MAX: {max_ref}\n"
        "Копируйте и отправляйте друзьям!"
    )
    await event.message.answer(links_text, attachments=[get_back_kb().as_markup()])

    try:
        media = InputMedia(repost_data.image_path)
        attachment = await event.bot.upload_media(media)
        await event.message.answer(
            text=repost_data.text,
            attachments=[attachment, get_back_kb().as_markup()]
        )
    except Exception as e:
        logger.error(f"Failed to upload referral image: {e}")
        await event.message.answer(
            text=repost_data.text,
            attachments=[get_back_kb().as_markup()]
        )
