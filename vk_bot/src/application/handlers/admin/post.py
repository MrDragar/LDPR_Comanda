import asyncio
import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import PostsStates
from src.application.filters import AdminFilter, check_role
from src.services.interfaces import IUserService
from src.domain.entities.user import UserRole

logger = logging.getLogger(__name__)
router = BotLabeler()
# Фильтр применяется ко всем хендлерам в этом роутере (только для админов)
router.auto_rules = [AdminFilter()]


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


# ==================== РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ ====================

@router.message(text=["/post", "Рассылка всем"])
async def cmd_post(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.set(message.from_id, PostsStates.GET_MESSAGE)
    await message.answer(
        "Отправьте сообщение (текст и/или вложения), которое нужно разослать всем пользователям:"
    )


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
        f"Текст: {message.text or '(нет)'}\nВложений: {att_count}\n\nОтправьте 'Да'."
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
        f"Вы уверены, что хотите разослать это сообщение координаторам РО?\n\n"
        f"Текст: {text_preview}\n"
        f"Вложений: {att_count}\n\n"
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