import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from src.application.states import PostsStates
from src.application.keyboards.admin.post_keyboard import get_post_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IUserService
from src.application.filters import AdminFilter

logger = logging.getLogger(__name__)
router = Router(name=__name__)


# ==================== РАССЫЛКА ВСЕМ ====================
@router.message(F.text.in_(["/post", "Рассылка всем"]), AdminFilter())
async def cmd_post(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправьте сообщение (текст, фото, видео или документ), которое нужно разослать всем пользователям:",
        reply_markup=ReplyKeyboardRemove())
    await state.set_state(PostsStates.get_message)


@router.message(PostsStates.get_message)
async def get_message(message: types.Message, state: FSMContext):
    # Сохраняем ID чата и сообщения для последующего копирования
    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Сообщение сохранено. Подтвердите начало рассылки.",
                         reply_markup=get_post_keyboard())
    await state.set_state(PostsStates.confirm)


@router.message(PostsStates.confirm, F.text == "Подтвердить")
async def confirm_post(message: types.Message, state: FSMContext, user_service: IUserService,
                       bot: Bot):
    data = await state.get_data()
    users = await user_service.get_all_users()
    await message.answer(f"Начинаю рассылку на {len(users)} пользователей...",
                         reply_markup=ReplyKeyboardRemove())

    success_count = 0
    for user in users:
        try:
            await bot.copy_message(
                chat_id=user.id,
                from_chat_id=data['from_chat_id'],
                message_id=data['message_id'],
                reply_markup=get_role_menu_keyboard(user.role)
            )
            success_count += 1
        except Exception as e:
            logger.debug(f"Failed to send to {user.id}: {e}")

    await state.clear()
    await message.answer(f"Рассылка завершена. Успешно отправлено: {success_count} из {len(users)}")


@router.message(PostsStates.confirm, F.text == "Отменить")
async def cancel_post(message: types.Message, state: FSMContext, user_service: IUserService):
    await state.clear()
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Рассылка отменена.", reply_markup=get_role_menu_keyboard(role))


# ==================== РАССЫЛКА КООРДИНАТОРАМ РО ====================
@router.message(F.text == "Рассылка координаторам РО")
async def cmd_post_coord(message: types.Message, state: FSMContext, user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    if role != UserRole.STAFF_CA:
        return await message.answer("Недостаточно прав. Эта функция доступна только сотруднику ЦА.")

    await message.answer("Отправьте сообщение для рассылки координаторам РО:",
                         reply_markup=ReplyKeyboardRemove())
    await state.set_state(PostsStates.get_coord_message)


@router.message(PostsStates.get_coord_message)
async def get_coord_message(message: types.Message, state: FSMContext):
    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Сообщение сохранено. Подтвердите рассылку координаторам РО.",
                         reply_markup=get_post_keyboard())
    await state.set_state(PostsStates.confirm_coord)


@router.message(PostsStates.confirm_coord, F.text == "Подтвердить")
async def confirm_post_coord(message: types.Message, state: FSMContext, user_service: IUserService,
                             bot: Bot):
    data = await state.get_data()
    all_users = await user_service.get_all_users()
    coord_users = [u for u in all_users if u.role == UserRole.COORDINATOR_RO]

    if not coord_users:
        await state.clear()
        return await message.answer("Координаторы РО не найдены в системе.")

    await message.answer(f"Начинаю рассылку на {len(coord_users)} координаторов РО...",
                         reply_markup=ReplyKeyboardRemove())

    success_count = 0
    for user in coord_users:
        try:
            await bot.copy_message(
                chat_id=user.id,
                from_chat_id=data['from_chat_id'],
                message_id=data['message_id']
            )
            success_count += 1
        except Exception as e:
            logger.debug(f"Failed to send to coord {user.id}: {e}")

    await state.clear()
    await message.answer(
        f"Рассылка координаторам завершена. Успешно отправлено: {success_count} из {len(coord_users)}")


@router.message(PostsStates.confirm_coord, F.text == "Отменить")
async def cancel_post_coord(message: types.Message, state: FSMContext, user_service: IUserService):
    await state.clear()
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Рассылка отменена.", reply_markup=get_role_menu_keyboard(role))