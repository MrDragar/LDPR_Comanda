import asyncio
import logging
import io
import aiohttp
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text, BaseStateGroup
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import PostsStates
from src.application.filters import AdminFilter, check_role
from src.services.interfaces import IUserService
from src.domain.entities.user import UserRole

logger = logging.getLogger(__name__)
router = BotLabeler()

# Фильтр применяется ко всем хендлерам в этом роутере (только для админов)
router.auto_rules = [AdminFilter()]


class PostFileStates(BaseStateGroup):
    CHOOSE_SOURCE = "post_choose_source"
    AWAIT_FILE = "post_await_file"
    GET_MESSAGE_FILE = "post_get_message_file"
    CONFIRM_FILE = "post_confirm_file"


def parse_attachments(message: Message) -> str | None:
    """Безопасный парсер вложений с учетом access_key и багов owner_id"""
    attachment_strings = []
    if not message.attachments:
        return None
    for att in message.attachments:
        try:
            # Определяем тип (в vkbottle это может быть Enum или строка)
            att_type = att.type.value if hasattr(att.type, 'value') else str(att.type)
            # 1. Фото
            if att_type == 'photo':
                photo = att.photo
                owner_id = photo.owner_id
                # Защита: если вдруг owner_id оказался равен peer_id (> 2 млрд)
                if owner_id > 2000000000:
                    owner_id = message.from_id
                access_key = getattr(photo, 'access_key', '')
                att_str = f"photo{owner_id}_{photo.id}"
                if access_key:
                    att_str += f"_{access_key}"
                attachment_strings.append(att_str)
            # 2. Документы
            elif att_type == 'doc':
                doc = att.doc
                owner_id = doc.owner_id
                if owner_id > 2000000000:
                    owner_id = message.from_id
                access_key = getattr(doc, 'access_key', '')
                att_str = f"doc{owner_id}_{doc.id}"
                if access_key:
                    att_str += f"_{access_key}"
                attachment_strings.append(att_str)
            # 3. Видео
            elif att_type == 'video':
                video = att.video
                owner_id = video.owner_id
                if owner_id > 2000000000:
                    owner_id = message.from_id
                access_key = getattr(video, 'access_key', '')
                att_str = f"video{owner_id}_{video.id}"
                if access_key:
                    att_str += f"_{access_key}"
                attachment_strings.append(att_str)
            # 4. Голосовые сообщения
            elif att_type == 'audio_message':
                am = att.audio_message
                owner_id = am.owner_id
                if owner_id > 2000000000:
                    owner_id = message.from_id
                access_key = getattr(am, 'access_key', '')
                att_str = f"audio_message{owner_id}_{am.id}"
                if access_key:
                    att_str += f"_{access_key}"
                attachment_strings.append(att_str)
            # 5. Аудио
            elif att_type == 'audio':
                audio = att.audio
                attachment_strings.append(f"audio{audio.owner_id}_{audio.id}")
            # 6. Посты со стены
            elif att_type == 'wall':
                wall = att.wall
                attachment_strings.append(f"wall{wall.owner_id}_{wall.id}")
        except Exception as e:
            logger.warning(f"Failed to parse attachment: {e}")
    return ",".join(attachment_strings) if attachment_strings else None


async def download_and_parse_excel(url: str) -> list[int]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                file_bytes = await resp.read()

                def safe_int(val):
                    try:
                        return int(float(str(val).strip()))
                    except (ValueError, TypeError):
                        return None

                try:
                    import pandas as pd
                    df = pd.read_excel(io.BytesIO(file_bytes))
                    id_col = next((col for col in df.columns if str(col).lower().strip() == 'id'),
                                  None)
                    if id_col is None:
                        raise ValueError("Столбец 'id' не найден в файле")
                    ids = [safe_int(x) for x in df[id_col].dropna().tolist()]
                    return [x for x in ids if x is not None]
                except ImportError:
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
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
            else:
                raise ValueError("Не удалось скачать файл")


# ==================== РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ ====================
@router.message(text=["/post", "Рассылка всем"])
async def cmd_post(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, PostFileStates.CHOOSE_SOURCE)
    kb = Keyboard(one_time=True).add(Text("БД")).add(Text("Файл")).get_json()
    await message.answer("Выберите источник пользователей для рассылки:", keyboard=kb)


@router.message(state=PostFileStates.CHOOSE_SOURCE, text=["БД"])
async def choose_db(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, PostsStates.GET_MESSAGE)
    await message.answer(
        "Отправьте сообщение (текст и/или вложения), которое нужно разослать всем пользователям из БД:"
    )


@router.message(state=PostFileStates.CHOOSE_SOURCE, text=["Файл"])
async def choose_file(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, PostFileStates.AWAIT_FILE)
    await message.answer(
        "Отправьте Excel файл (.xlsx или .xls) со столбцом 'id', содержащим ID пользователей для рассылки:"
    )


@router.message(state=PostFileStates.AWAIT_FILE)
async def receive_file(message: Message, state_dispenser: BuiltinStateDispenser):
    if not message.attachments:
        return await message.answer("Пожалуйста, отправьте файл документом.")

    doc = message.attachments[0].doc
    if not doc:
        return await message.answer("Это не документ. Отправьте Excel файл.")

    url = doc.url
    if not url:
        return await message.answer("Не удалось получить ссылку на файл. Попробуйте еще раз.")

    try:
        user_ids = await download_and_parse_excel(url)
        if not user_ids:
            return await message.answer("Файл не содержит ID пользователей или столбец 'id' пуст.")

        # Уникализируем ID
        user_ids = list(set(user_ids))

        await state_dispenser.set(
            message.from_id,
            PostFileStates.GET_MESSAGE_FILE,
            user_ids=user_ids
        )
        await message.answer(
            f"✅ Файл успешно обработан. Найдено {len(user_ids)} уникальных ID.\n"
            "Теперь отправьте сообщение (текст и/или вложения) для рассылки этим пользователям:"
        )
    except Exception as e:
        logger.error(f"Error parsing excel file: {e}")
        await message.answer(
            f"❌ Ошибка при обработке файла: {e}\nПопробуйте еще раз или отмените действие.")


@router.message(state=PostFileStates.GET_MESSAGE_FILE)
async def confirm_post_file(message: Message, state_dispenser: BuiltinStateDispenser):
    attachments_str = parse_attachments(message)
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(
        message.from_id,
        PostFileStates.CONFIRM_FILE,
        msg_text=message.text or "",
        attachments=attachments_str,
        user_ids=state.payload.get("user_ids", [])
    )
    att_count = len(attachments_str.split(',')) if attachments_str else 0
    await message.answer(
        f"Вы уверены, что хотите разослать это сообщение {len(state.payload.get('user_ids', []))} пользователям из файла?\n"
        f"Текст: {message.text or '(нет)'}\n"
        f"Вложений: {att_count}\n"
        "Отправьте 'Да'."
    )


@router.message(state=PostFileStates.CONFIRM_FILE, text=["Да", "да"])
async def start_mailing_file(message: Message, user_service: IUserService,
                             state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    msg_text = state.payload.get('msg_text', '')
    attachments = state.payload.get('attachments')
    user_ids = state.payload.get('user_ids', [])

    await message.answer(f"Начинаю рассылку на {len(user_ids)} пользователей из файла...")
    count = 0
    for uid in user_ids:
        try:
            kwargs = {"peer_id": uid, "random_id": 0}
            if msg_text: kwargs["message"] = msg_text
            if attachments: kwargs["attachment"] = attachments
            if not msg_text and not attachments: continue
            await message.ctx_api.messages.send(**kwargs)
            count += 1
            await asyncio.sleep(0.05)  # Защита от rate limit VK API
        except Exception as e:
            logger.debug(f"Failed to send to {uid}: {e}")

    await state_dispenser.delete(message.from_id)
    await message.answer(
        f"Рассылка по файлу завершена. Успешно отправлено: {count} из {len(user_ids)}")


@router.message(state=PostFileStates.CONFIRM_FILE)
async def cancel_mailing_file(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(message.from_id)
    await message.answer("Рассылка по файлу отменена.")


@router.message(state=PostsStates.GET_MESSAGE)
async def confirm_post(message: Message, state_dispenser: BuiltinStateDispenser):
    attachments_str = parse_attachments(message)
    await state_dispenser.set(
        message.from_id,
        PostsStates.CONFIRM,
        msg_text=message.text or "",
        attachments=attachments_str
    )
    att_count = len(attachments_str.split(',')) if attachments_str else 0
    await message.answer(
        f"Вы уверены, что хотите разослать это сообщение?\n"
        f"Текст: {message.text or '(нет)'}\nВложений: {att_count}\nОтправьте 'Да'."
    )


@router.message(state=PostsStates.CONFIRM, text=["Да", "да"])
async def start_mailing(message: Message, user_service: IUserService,
                        state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    msg_text = state.payload.get('msg_text', '')
    attachments = state.payload.get('attachments')
    users = await user_service.get_all_users()
    await message.answer(f"Начинаю рассылку на {len(users)} пользователей...")
    count = 0
    for u in users:
        try:
            kwargs = {"peer_id": u.id, "random_id": 0}
            if msg_text: kwargs["message"] = msg_text
            if attachments: kwargs["attachment"] = attachments
            if not msg_text and not attachments: continue
            await message.ctx_api.messages.send(**kwargs)
            count += 1
            await asyncio.sleep(0.05)  # Защита от rate limit VK API
        except Exception as e:
            logger.debug(f"Failed to send to {u.id}: {e}")
    await state_dispenser.delete(message.from_id)
    await message.answer(f"Рассылка всем завершена. Успешно отправлено: {count} из {len(users)}")


@router.message(state=PostsStates.CONFIRM)
async def cancel_mailing(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(message.from_id)
    await message.answer("Рассылка отменена.")


# ==================== РАССЫЛКА КООРДИНАТОРАМ РО ====================
@router.message(text=["Рассылка координаторам РО"])
async def cmd_post_coord(message: Message, user_service: IUserService,
                         state_dispenser: BuiltinStateDispenser):
    # Дополнительная проверка роли (AdminFilter пропустил всех админов, но эта кнопка только для ЦА)
    if not await check_role(user_service, message.from_id, [UserRole.STAFF_CA]):
        return await message.answer("Недостаточно прав. Эта функция доступна только сотруднику ЦА.")
    await state_dispenser.set(message.from_id, PostsStates.GET_COORD_MESSAGE)
    await message.answer(
        "Отправьте сообщение для рассылки координаторам РО.\n"
        "Можно прикрепить фото, видео или документы."
    )


@router.message(state=PostsStates.GET_COORD_MESSAGE)
async def confirm_post_coord(message: Message, state_dispenser: BuiltinStateDispenser):
    attachments_str = parse_attachments(message)
    await state_dispenser.set(
        message.from_id,
        PostsStates.CONFIRM_COORD,
        msg_text=message.text or "",
        attachments=attachments_str
    )
    text_preview = message.text or "(без текста)"
    att_count = len(attachments_str.split(',')) if attachments_str else 0
    await message.answer(
        f"Вы уверены, что хотите разослать это сообщение координаторам РО?\n"
        f"Текст: {text_preview}\n"
        f"Вложений: {att_count}\n"
        f"Отправьте 'Да' для подтверждения."
    )


@router.message(state=PostsStates.CONFIRM_COORD, text=["Да", "да"])
async def start_mailing_coord(message: Message, user_service: IUserService,
                              state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    msg_text = state.payload.get('msg_text', '')
    attachments = state.payload.get('attachments')
    # Получаем всех пользователей и фильтруем координаторов РО
    all_users = await user_service.get_all_users()
    coord_users = [u for u in all_users if u.role == UserRole.COORDINATOR_RO]
    if not coord_users:
        await state_dispenser.delete(message.from_id)
        return await message.answer("Координаторы РО не найдены в системе.")
    await message.answer(f"Начинаю рассылку на {len(coord_users)} координаторов РО...")
    count = 0
    for u in coord_users:
        try:
            kwargs = {"peer_id": u.id, "random_id": 0}
            if msg_text: kwargs["message"] = msg_text
            if attachments: kwargs["attachment"] = attachments
            if not msg_text and not attachments: continue
            await message.ctx_api.messages.send(**kwargs)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.debug(f"Failed to send to coord {u.id}: {e}")
    await state_dispenser.delete(message.from_id)
    await message.answer(
        f"Рассылка координаторам завершена. Успешно отправлено: {count} из {len(coord_users)}")


@router.message(state=PostsStates.CONFIRM_COORD)
async def cancel_mailing_coord(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(message.from_id)
    await message.answer("Рассылка координаторам отменена.")