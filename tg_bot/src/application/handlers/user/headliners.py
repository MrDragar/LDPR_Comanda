import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from src.application.states import HeadlinerStates
from src.domain.entities.user import Sources, UserRole
from src.services.interfaces import IHeadlinerService, IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(F.text == "Приветственное сообщение")
async def welcome_message_start(message: types.Message, state: FSMContext,
                                user_service: IUserService, headliner_service: IHeadlinerService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    if u.role != UserRole.HEADLINER:
        return await message.answer("Эта функция доступна только хедлайнерам.")

    headliner = await headliner_service.get_by_user(u.id, u.source)
    if not headliner:
        return await message.answer("Профиль хедлайнера не найден.")

    current = headliner.welcome_message or "не задано"
    await state.set_state(HeadlinerStates.welcome_message)
    await message.answer(
        f"Отправьте новое приветственное сообщение для людей, которые зарегистрируются по вашей ссылке.\n"
        f"Текущее сообщение: {current}\n\n"
        f"Чтобы отменить, отправьте 'Отмена'."
    )


@router.message(HeadlinerStates.welcome_message)
async def welcome_message_save(message: types.Message, state: FSMContext,
                               user_service: IUserService, headliner_service: IHeadlinerService):
    if message.text and message.text.lower() in ["отмена", "на главную"]:
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        return await message.answer("Действие отменено.", reply_markup=get_role_menu_keyboard(role))

    text = (message.text or "").strip()
    if len(text) < 3:
        return await message.answer("Сообщение слишком короткое. Отправьте текст от 3 символов.")

    headliner = await headliner_service.update_welcome_message_by_user(
        message.from_user.id, Sources.TG, text
    )
    await state.clear()
    if not headliner:
        return await message.answer("Профиль хедлайнера не найден.")

    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("✅ Приветственное сообщение сохранено.",
                         reply_markup=get_role_menu_keyboard(role))


@router.message(F.text == "Рейтинг хедлайнеров")
async def headliner_rating(message: types.Message, user_service: IUserService,
                           headliner_service: IHeadlinerService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    if u.role not in [UserRole.STAFF_CA, UserRole.HEADLINER]:
        return await message.answer("Недостаточно прав.")

    rating = await headliner_service.get_rating()
    if not rating:
        return await message.answer("Хедлайнеров пока нет.")

    lines = ["🏆 Рейтинг хедлайнеров:"]
    for index, (headliner, followers) in enumerate(rating[:30], start=1):
        lines.append(f"{index}. {headliner.fio} — {followers} последователей")

    await message.answer("\n".join(lines))
