import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageButton, InputMedia
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.services.interfaces import IUserService, IReferralService, IBalanceService, \
    ILearningService, IReferralLinkService, IHeadlinerService
from src.domain.entities.user import Sources, UserRole

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


def get_referral_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="На главную"))
    return builder


@router.message_created(F.message.body.text == "Личный кабинет")
async def profile(
    event: MessageCreated, user_service: IUserService, referral_service: IReferralService,
    balance_service: IBalanceService, learning_service: ILearningService,
    headliner_service: IHeadlinerService
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
        await event.message.answer(text, attachments=[get_profile_kb().as_markup()])
    except Exception as e:
        logger.error(f"Profile error: {e}", exc_info=True)
        await event.message.answer("Ошибка загрузки профиля")


@router.message_created(F.message.body.text == "Назад")
async def back_to_profile(
    event: MessageCreated, user_service: IUserService, referral_service: IReferralService,
    balance_service: IBalanceService, learning_service: ILearningService,
    headliner_service: IHeadlinerService
):
    await profile(event, user_service, referral_service, balance_service, learning_service,
                  headliner_service)


@router.message_created(F.message.body.text == "Реферальная ссылка")
async def referral_link(
        event: MessageCreated, referral_link_service: IReferralLinkService,
        headliner_service: IHeadlinerService
):
    user_id = event.from_user.user_id
    headliner = await headliner_service.get_by_user(user_id, Sources.MAX)
    if headliner:
        links = headliner_service.make_referral_links(headliner.id)
        links_text = (
            "Ваши ссылки хэдлайнера:\n\n"
            f"VK: {links['VK']}\n"
            f"MAX: {links['MAX']}\n"
            f"Telegram: {links['Telegram']}\n\n"
            "Все зарегистрированные по этим ссылкам попадут в вашу команду."
        )
        return await event.message.answer(links_text, attachments=[get_referral_kb().as_markup()])

    repost_data = referral_link_service.generate_post(user_id)

    try:
        media = InputMedia(repost_data.image_path)
        attachment = await event.bot.upload_media(media)
        await event.message.answer(
            text=repost_data.text,
            attachments=[attachment, get_referral_kb().as_markup()]
        )
    except Exception as e:
        logger.error(f"Failed to upload referral image: {e}")
        await event.message.answer(
            text=repost_data.text,
            attachments=[get_referral_kb().as_markup()]
        )
