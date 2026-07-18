import asyncio
import io
import logging
import aiohttp
from maxapi import Router, F, Bot
from maxapi.enums import ParseMode
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext, State
from maxapi.types.attachments import File

from src.application.states import PostsStates
from src.services.interfaces import IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities.user import Sources

logger = logging.getLogger(__name__)
router = Router()


class PostFileStates:
    """Состояния для рассылки по файлу"""
    CHOOSE_SOURCE = State()
    AWAIT_FILE = State()
    GET_MESSAGE_FILE = State()
    CONFIRM_FILE = State()


async def download_and_parse_excel(file_stream: io.BytesIO) -> list[int]:
    """Парсит Excel файл из потока"""

    def safe_int(val):
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return None

    try:
        import pandas as pd
        df = pd.read_excel(file_stream)
        id_col = next((col for col in df.columns if str(col).lower().strip() == 'id'), None)
        if id_col is None:
            raise ValueError("Столбец 'id' не найден в файле")
        ids = [safe_int(x) for x in df[id_col].dropna().tolist()]
        return [x for x in ids if x is not None]
    except ImportError:
        import openpyxl
        # Сбрасываем курсор, так как pandas мог его сдвинуть
        file_stream.seek(0)
        wb = openpyxl.load_workbook(file_stream, read_only=True)
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


# ==================== НАЧАЛО РАССЫЛКИ ====================
@router.message_created(F.message.body.text.in_(["/post", "Рассылка всем"]))
async def cmd_post(event: MessageCreated, context: MemoryContext, admin_ids: list[int]):
    # Проверка прав администратора
    if str(event.from_user.user_id) not in [str(i) for i in admin_ids]:
        return await event.message.answer("Недостаточно прав.")

    await event.message.answer(
        "Выберите источник пользователей для рассылки:\n"
        "Отправьте 'БД' для рассылки всем пользователям из базы.\n"
        "Отправьте 'Файл' для рассылки по списку ID из Excel файла."
    )
    await context.set_state(PostFileStates.CHOOSE_SOURCE)


@router.message_created(PostFileStates.CHOOSE_SOURCE, F.message.body.text == "БД")
async def choose_db(event: MessageCreated, context: MemoryContext):
    await event.message.answer(
        "Отправьте сообщение (текст, фото, видео или документ), которое нужно разослать всем пользователям из БД:"
    )
    await context.set_state(PostsStates.get_message)


@router.message_created(PostFileStates.CHOOSE_SOURCE, F.message.body.text == "Файл")
async def choose_file(event: MessageCreated, context: MemoryContext):
    await event.message.answer(
        "Отправьте Excel файл (.xlsx или .xls) со столбцом 'id', содержащим ID пользователей для рассылки:"
    )
    await context.set_state(PostFileStates.AWAIT_FILE)


@router.message_created(PostFileStates.CHOOSE_SOURCE)
async def invalid_source_choice(event: MessageCreated):
    await event.message.answer(
        "Пожалуйста, выберите 'БД' или 'Файл', отправив соответствующее слово.")


# ==================== РАССЫЛКА ПО ФАЙЛУ ====================
@router.message_created(PostFileStates.AWAIT_FILE)
async def receive_file(event: MessageCreated, context: MemoryContext, bot: Bot):
    attachments = event.message.body.attachments

    # Если нет вложений, напоминаем отправить файл
    if not attachments:
        return await event.message.answer("Пожалуйста, отправьте именно файл (документ).")

    # Ищем документ/файл в вложениях
    doc_attachment = None
    for att in attachments:
        # В MaxAPI документы обычно имеют тип, отличный от Image/Video, или мы проверяем наличие URL
        # Простая проверка: если это не картинка и не видео, считаем документом, или если есть явный признак файла
        if not hasattr(att, 'payload') or not hasattr(att.payload, 'url'):
            continue

        # Исключаем картинки и видео, если хотим строго Excel, но обычно Excel приходит как документ
        # В документации MaxAPI примеры показывают, что у вложений есть payload.url
        doc_attachment = att
        break

    if not doc_attachment:
        return await event.message.answer("Не удалось распознать файл. Отправьте Excel документом.")

    file_url = getattr(doc_attachment.payload, 'url', None)

    if not file_url:
        return await event.message.answer("Не удалось получить ссылку на файл. Попробуйте еще раз.")

    try:
        # Используем download_bytes_io как в документации для эффективной работы с памятью
        file_stream = await bot.download_bytes_io(file_url)

        user_ids = await download_and_parse_excel(file_stream)
        if not user_ids:
            return await event.message.answer(
                "Файл не содержит ID пользователей или столбец 'id' пуст.")

        # Уникализируем ID
        user_ids = list(set(user_ids))

        await context.update_data(user_ids=user_ids)
        await event.message.answer(
            f"✅ Файл успешно обработан. Найдено {len(user_ids)} уникальных ID.\n"
            "Теперь отправьте сообщение (текст, фото, видео или документ) для рассылки этим пользователям:"
        )
        await context.set_state(PostFileStates.GET_MESSAGE_FILE)
    except Exception as e:
        logger.error(f"Error parsing excel file: {e}")
        await event.message.answer(f"❌ Ошибка при обработке файла: {e}\nПопробуйте еще раз.")


@router.message_created(PostFileStates.GET_MESSAGE_FILE)
async def get_message_file(event: MessageCreated, context: MemoryContext):
    # Сохраняем ID сообщения для последующего получения через API
    # В MaxAPI ID сообщения может быть в body.mid или другом поле, адаптируем под текущую структуру
    # Обычно это event.message.body.mid
    await context.update_data(message_id=event.message.body.mid)
    await event.message.answer(
        "Сообщение сохранено. Подтвердите начало рассылки по файлу. (Подтвердить / Отменить)"
    )
    await context.set_state(PostFileStates.CONFIRM_FILE)


@router.message_created(PostFileStates.CONFIRM_FILE, F.message.body.text == "Подтвердить")
async def confirm_post_file(event: MessageCreated, context: MemoryContext,
                            user_service: IUserService, bot: Bot):
    if await context.get_state() != PostFileStates.CONFIRM_FILE:
        return

    data = await context.get_data()
    message_id = data.get('message_id')
    user_ids = data.get('user_ids', [])

    await event.message.answer(f"Начинаю рассылку на {len(user_ids)} пользователей из файла...")

    try:
        # Получаем исходный объект сообщения через API бота
        msg = await bot.get_message(message_id=message_id)
    except Exception as e:
        logger.error(f"Failed to get message: {e}")
        await event.message.answer("Не удалось получить исходное сообщение для рассылки.")
        await context.clear()
        return

    success_count = 0
    for idx, uid in enumerate(user_ids):
        try:
            # В MaxAPI отправка может отличаться, используем стандартный метод send_message
            # Если msg.body содержит текст и вложения, копируем их
            await bot.send_message(
                chat_id=None,
                # В MaxAPI часто используется user_id напрямую или chat_id=None для личных сообщений
                user_id=uid,
                text=msg.body.md_text if hasattr(msg.body, 'md_text') else msg.body.text,
                attachments=msg.body.attachments,
                parse_mode=ParseMode.MARKDOWN
            )
            success_count += 1
            await asyncio.sleep(0.1)
            if idx % 100 == 0:
                await event.message.answer(f"{idx}({success_count})/{len(user_ids)}")
        except Exception as e:
            logger.debug(f"Failed to send to {uid}: {e}")

    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer(
        f"Рассылка по файлу завершена. Успешно отправлено: {success_count} из {len(user_ids)}")
    await event.message.answer("Главное меню:",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(PostFileStates.CONFIRM_FILE, F.message.body.text == "Отменить")
async def cancel_post_file(event: MessageCreated, context: MemoryContext,
                           user_service: IUserService):
    if await context.get_state() != PostFileStates.CONFIRM_FILE:
        return
    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Рассылка по файлу отменена.",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


# ==================== РАССЫЛКА ИЗ БД (СТАНДАРТНАЯ) ====================
@router.message_created(PostsStates.get_message)
async def get_message(event: MessageCreated, context: MemoryContext):
    # Сохраняем ID сообщения
    await context.update_data(
        message_id=event.message.body.mid
    )
    await event.message.answer(
        "Сообщение сохранено. Подтвердите начало рассылки. (Подтвердить / Отменить)")
    await context.set_state(PostsStates.confirm)


@router.message_created(PostsStates.confirm, F.message.body.text == "Подтвердить")
async def confirm_post(event: MessageCreated, context: MemoryContext, user_service: IUserService,
                       bot: Bot):
    if await context.get_state() != PostsStates.confirm:
        return

    data = await context.get_data()
    message_id = data.get('message_id')

    users = await user_service.get_all_users()
    await event.message.answer(f"Начинаю рассылку на {len(users)} пользователей...")

    success_count = 0

    try:
        msg = await bot.get_message(message_id=message_id)
    except Exception as e:
        logger.error(f"Failed to get message: {e}")
        await event.message.answer("Не удалось получить исходное сообщение для рассылки.")
        await context.clear()
        return

    for idx, user in enumerate(users):
        try:
            await bot.send_message(
                chat_id=None, user_id=user.id, text=msg.body.md_text,
                attachments=msg.body.attachments, parse_mode=ParseMode.MARKDOWN
            )
            success_count += 1
            await asyncio.sleep(0.1)
            if idx % 100 == 0:
                await event.message.answer(f"{idx}({success_count})/{len(users)}")
        except Exception as e:
            logger.debug(f"Failed to forward to {user.id}: {e}")

    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer(
        f"Рассылка завершена. Успешно отправлено: {success_count} из {len(users)}")
    await event.message.answer("Главное меню:",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(PostsStates.confirm, F.message.body.text == "Отменить")
async def cancel_post(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if await context.get_state() != PostsStates.confirm:
        return
    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Рассылка отменена.",
                               attachments=[get_role_menu_keyboard(role).as_markup()])
