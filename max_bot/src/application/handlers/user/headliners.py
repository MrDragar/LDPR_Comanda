import logging
from maxapi import Router, F
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import HeadlinerStates
from src.domain.entities.user import Sources, UserRole
from src.services.interfaces import IHeadlinerService, IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message_created(F.message.body.text == "Приветственное сообщение")
async def welcome_message_start(event: MessageCreated, context: MemoryContext,
                                user_service: IUserService, headliner_service: IHeadlinerService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.role != UserRole.HEADLINER:
        return await event.message.answer("Эта функция доступна только хедлайнерам.")

    headliner = await headliner_service.get_by_user(u.id, u.source)
    if not headliner:
        return await event.message.answer("Профиль хедлайнера не найден.")

    current = headliner.welcome_message or "не задано"
    await context.set_state(HeadlinerStates.welcome_message)
    await event.message.answer(
        f"Отправьте новое приветственное сообщение для людей, которые зарегистрируются по вашей ссылке.\n"
        f"Текущее сообщение: {current}\n\n"
        f"Чтобы отменить, отправьте 'Отмена'."
    )


@router.message_created(HeadlinerStates.welcome_message)
async def welcome_message_save(event: MessageCreated, context: MemoryContext,
                               user_service: IUserService, headliner_service: IHeadlinerService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        return await event.message.answer("Действие отменено.",
                                          attachments=[get_role_menu_keyboard(role).as_markup()])

    text = (event.message.body.text or "").strip()
    if len(text) < 3:
        return await event.message.answer(
            "Сообщение слишком короткое. Отправьте текст от 3 символов.")

    headliner = await headliner_service.update_welcome_message_by_user(
        event.from_user.user_id, Sources.MAX, text
    )
    await context.clear()
    if not headliner:
        return await event.message.answer("Профиль хедлайнера не найден.")

    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("✅ Приветственное сообщение сохранено.",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(F.message.body.text == "Рейтинг хедлайнеров")
async def headliner_rating(event: MessageCreated, user_service: IUserService,
                           headliner_service: IHeadlinerService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.role not in [UserRole.STAFF_CA, UserRole.HEADLINER]:
        return await event.message.answer("Недостаточно прав.")

    rating = await headliner_service.get_rating()
    if not rating:
        return await event.message.answer("Хедлайнеров пока нет.")

    lines = ["🏆 Рейтинг хедлайнеров:"]
    for index, (headliner, followers) in enumerate(rating[:30], start=1):
        lines.append(f"{index}. {headliner.fio} — {followers} последователей")

    await event.message.answer("\n".join(lines))
