import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from src.application.states import PostsStates
from src.application.keyboards.admin.post_keyboard import get_post_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IUserService
from src.application.filters import AdminFilter

logger = logging.getLogger(__name__)
router = Router(name=__name__)


class PostFileStates(StatesGroup):
    choose_source = State()
    await_file = State()
    get_message_file = State()
    confirm_file = State()


async def download_and_parse_excel(file_id: str, bot: Bot) -> list[int]:
    """Скачивает Excel файл и парсит столбец 'id'"""
    file = await bot.get_file(file_id)
    # В aiogram3 download_file возвращает io.BytesIO, а не bytes
    file_obj = await bot.download_file(file.file_path)
    if not file_obj:
        raise ValueError("Не удалось скачать файл")

    def safe_int(val):
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return None

    try:
        import pandas as pd
        # Передаем file_obj напрямую, так как это уже файловый объект
        df = pd.read_excel(file_obj)
        id_col = next((col for col in df.columns if str(col).lower().strip() == 'id'), None)
        if id_col is None:
            raise ValueError("Столбец 'id' не найден в файле")
        ids = [safe_int(x) for x in df[id_col].dropna().tolist()]
        return [x for x in ids if x is not None]
    except ImportError:
        import openpyxl
        wb = openpyxl.load_workbook(file_obj, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise ValueError("Файл пуст")
        headers = [str(h).lower().strip() if h else "" for h in rows[0]]
        if 'id' not in headers:
            raise ValueError("Столбец 'id' не найден в файле")
        id_idx = headers.index('id')
        ids = []
        for row in rows[1:]:
            if len(row) > id_idx and row[id_idx] is not None:
                val = safe_int(row[id_idx])
                if val is not None:
                    ids.append(val)
        return ids


# ==================== РАССЫЛКА ВСЕМ ====================
@router.message(F.text.in_(["/post", "Рассылка всем"]), AdminFilter())
async def cmd_post(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="БД"), KeyboardButton(text="Файл")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Выберите источник пользователей для рассылки:",
        reply_markup=kb
    )
    await state.set_state(PostFileStates.choose_source)


@router.message(PostFileStates.choose_source, F.text == "БД")
async def choose_db(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправьте сообщение (текст, фото, видео или документ), которое нужно разослать всем пользователям из БД:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(PostsStates.get_message)


@router.message(PostFileStates.choose_source, F.text == "Файл")
async def choose_file(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправьте Excel файл (.xlsx или .xls) со столбцом 'id', содержащим ID пользователей для рассылки:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(PostFileStates.await_file)


@router.message(PostFileStates.choose_source)
async def invalid_source_choice(message: types.Message):
    await message.answer("Пожалуйста, выберите 'БД' или 'Файл' на клавиатуре.")


@router.message(PostFileStates.await_file, F.document)
async def receive_file(message: types.Message, state: FSMContext, bot: Bot):
    doc = message.document
    if not doc.file_name or not doc.file_name.endswith(('.xlsx', '.xls')):
        return await message.answer("Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls).")

    try:
        user_ids = await download_and_parse_excel(doc.file_id, bot)
        if not user_ids:
            return await message.answer("Файл не содержит ID пользователей или столбец 'id' пуст.")

        # Уникализируем ID
        user_ids = list(set(user_ids))
        await state.update_data(user_ids=user_ids)
        await message.answer(
            f"✅ Файл успешно обработан. Найдено {len(user_ids)} уникальных ID.\n"
            "Теперь отправьте сообщение (текст, фото, видео или документ) для рассылки этим пользователям:"
        )
        await state.set_state(PostFileStates.get_message_file)
    except Exception as e:
        logger.error(f"Error parsing excel file: {e}")
        await message.answer(
            f"❌ Ошибка при обработке файла: {e}\nПопробуйте еще раз или отмените действие.")


@router.message(PostFileStates.await_file)
async def receive_file_invalid(message: types.Message):
    await message.answer("Пожалуйста, отправьте файл документом.")


@router.message(PostFileStates.get_message_file)
async def get_message_file(message: types.Message, state: FSMContext):
    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Сообщение сохранено. Подтвердите начало рассылки по файлу.",
                         reply_markup=get_post_keyboard())
    await state.set_state(PostFileStates.confirm_file)


@router.message(PostFileStates.confirm_file, F.text == "Подтвердить")
async def confirm_post_file(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_ids = data.get('user_ids', [])
    await message.answer(f"Начинаю рассылку на {len(user_ids)} пользователей из файла...",
                         reply_markup=ReplyKeyboardRemove())

    success_count = 0
    for uid in user_ids:
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=data['from_chat_id'],
                message_id=data['message_id']
            )
            success_count += 1
        except Exception as e:
            logger.debug(f"Failed to send to {uid}: {e}")

    await state.clear()
    await message.answer(
        f"Рассылка по файлу завершена. Успешно отправлено: {success_count} из {len(user_ids)}")


@router.message(PostFileStates.confirm_file, F.text == "Отменить")
async def cancel_post_file(message: types.Message, state: FSMContext, user_service: IUserService):
    await state.clear()
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Рассылка по файлу отменена.", reply_markup=get_role_menu_keyboard(role))


# ==================== СТАНДАРТНАЯ РАССЫЛКА ИЗ Бд ====================
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