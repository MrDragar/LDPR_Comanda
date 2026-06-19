import asyncio
import logging
import re
from urllib.parse import urlparse

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.filters import check_role
from src.application.handlers.admin.post import parse_attachments
from src.application.states import HeadlinerStates
from src.domain.entities.headliner import Headliner
from src.domain.entities.user import Sources, UserRole
from src.services.interfaces import IHeadlinerService, IUserService

logger = logging.getLogger(__name__)
router = BotLabeler()


def parse_vk_profile_reference(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""

    value = value.split()[0].strip()
    if value.startswith("@"):
        value = value[1:]
    if "://" not in value and value.startswith(("vk.com/", "m.vk.com/")):
        value = "https://" + value
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if parsed.netloc.lower() not in ("vk.com", "m.vk.com", "www.vk.com"):
            return ""
        value = parsed.path.strip("/").split("/")[0]

    value = value.strip("/")
    if re.fullmatch(r"id\d+", value):
        return value[2:]
    if re.fullmatch(r"\d+", value):
        return value
    if re.fullmatch(r"[A-Za-z0-9_.]+", value):
        return value
    return ""


async def resolve_vk_profile_id(message: Message) -> int | None:
    user_ref = parse_vk_profile_reference(message.text or "")
    if not user_ref:
        return None
    if user_ref.isdigit():
        return int(user_ref)

    users = await message.ctx_api.users.get(user_ids=user_ref)
    if not users:
        return None
    return users[0].id


def extract_photo_url(message: Message) -> str | None:
    if not message.attachments:
        return None

    for attachment in message.attachments:
        att_type = attachment.type.value if hasattr(attachment.type, "value") else str(attachment.type)
        if att_type != "photo":
            continue

        photo = attachment.photo
        sizes = getattr(photo, "sizes", None) or []
        if not sizes:
            return None

        best_size = max(
            sizes,
            key=lambda item: getattr(item, "width", 0) * getattr(item, "height", 0),
        )
        return getattr(best_size, "url", None)

    return None


def format_headliner(headliner: Headliner, followers_count: int | None = None) -> str:
    followers = "" if followers_count is None else f"\nПоследователей: {followers_count}"
    return (
        f"ID: {headliner.id}\n"
        f"VK ID: {headliner.user_id}\n"
        f"ФИО: {headliner.fio}\n"
        f"Должность: {headliner.position}\n"
        f"Тема: {headliner.topic}\n"
        f"Группа: {headliner.group_link}"
        f"{followers}"
    )


async def require_staff_ca(message: Message, user_service: IUserService) -> bool:
    if not await check_role(user_service, message.from_id, [UserRole.STAFF_CA]):
        await message.answer("Недостаточно прав.")
        return False
    return True


@router.message(text=["Добавить хэдлайнера", "Создать хэдлайнера"])
async def create_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return

    await state_dispenser.set(message.from_id, HeadlinerStates.CREATE_USER_ID)
    await message.answer(
        "Отправьте ссылку на профиль VK пользователя, которого нужно сделать хэдлайнером.\n"
        "Пользователь должен быть уже зарегистрирован в боте."
    )


@router.message(text=["Отредактировать хэдлайнера"])
async def edit_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return

    await state_dispenser.set(message.from_id, HeadlinerStates.EDIT_ID)
    await message.answer("Введите ID хэдлайнера, которого нужно отредактировать.")


@router.message(state=HeadlinerStates.EDIT_ID)
async def edit_headliner_id(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    try:
        headliner_id = int(message.text.strip())
    except ValueError:
        return await message.answer("Введите числовой ID хэдлайнера.")

    headliner = await headliner_service.get_by_id(headliner_id)
    if headliner is None:
        return await message.answer("Хэдлайнер с таким ID не найден.")

    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_PHOTO,
        user_id=headliner.user_id,
        edit_id=headliner.id,
    )
    await message.answer(
        "Редактирование найдено.\n\n"
        f"{format_headliner(headliner)}\n\n"
        "Отправьте новое фото хэдлайнера одним сообщением."
    )


@router.message(state=HeadlinerStates.CREATE_USER_ID)
async def create_headliner_user_id(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    try:
        user_id = await resolve_vk_profile_id(message)
        if user_id is None:
            return await message.answer(
                "Не удалось определить профиль VK. Отправьте ссылку вида https://vk.com/id123 или https://vk.com/username."
            )
        await user_service.get_user(user_id, Sources.VK)
    except Exception:
        return await message.answer("Пользователь с таким профилем VK не найден в базе бота.")

    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_PHOTO,
        user_id=user_id,
    )
    await message.answer("Отправьте фото хэдлайнера одним сообщением.")


@router.message(state=HeadlinerStates.CREATE_PHOTO)
async def create_headliner_photo(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    photo = extract_photo_url(message) or parse_attachments(message)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_TOPIC,
        **state.payload,
        photo=photo,
    )
    await message.answer("Введите тему, над которой будет работать хэдлайнер.")


@router.message(state=HeadlinerStates.CREATE_TOPIC)
async def create_headliner_topic(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_FIO,
        **state.payload,
        topic=message.text.strip(),
    )
    await message.answer("Введите ФИО хэдлайнера.")


@router.message(state=HeadlinerStates.CREATE_FIO)
async def create_headliner_fio(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_POSITION,
        **state.payload,
        fio=message.text.strip(),
    )
    await message.answer("Введите должность хэдлайнера.")


@router.message(state=HeadlinerStates.CREATE_POSITION)
async def create_headliner_position(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_GROUP_LINK,
        **state.payload,
        position=message.text.strip(),
    )
    await message.answer("Введите ссылку на группу хэдлайнера.")


@router.message(state=HeadlinerStates.CREATE_GROUP_LINK)
async def create_headliner_finish(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
        headliner_service: IHeadlinerService,
):
    state = await state_dispenser.get(message.from_id)
    headliner = await headliner_service.create_headliner(
        user_id=state.payload["user_id"],
        fio=state.payload["fio"],
        position=state.payload["position"],
        topic=state.payload["topic"],
        group_link=message.text.strip(),
        photo=state.payload.get("photo"),
    )
    await state_dispenser.delete(message.from_id)

    links = headliner_service.make_referral_links(headliner.id)
    await message.answer(
        "Хэдлайнер сохранен.\n\n"
        f"{format_headliner(headliner)}\n\n"
        "Реферальные ссылки:\n"
        f"VK: {links['VK']}\n"
        f"MAX: {links['MAX']}\n"
        f"Telegram: {links['Telegram']}"
    )


@router.message(text=["Удалить хэдлайнера"])
async def delete_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return

    await state_dispenser.set(message.from_id, HeadlinerStates.DELETE_ID)
    await message.answer("Введите ID хэдлайнера, которого нужно удалить.")


@router.message(state=HeadlinerStates.DELETE_ID)
async def delete_headliner_finish(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    try:
        headliner_id = int(message.text.strip())
    except ValueError:
        return await message.answer("Введите числовой ID хэдлайнера.")

    headliner = await headliner_service.delete_headliner(headliner_id)
    await state_dispenser.delete(message.from_id)
    if headliner is None:
        return await message.answer("Хэдлайнер с таким ID не найден.")

    await message.answer(
        "Хэдлайнер удален, пользователь возвращен к обычной роли.\n\n"
        f"{format_headliner(headliner)}"
    )


@router.message(text=["Список хэдлайнеров"])
async def list_headliners(
        message: Message,
        user_service: IUserService,
        headliner_service: IHeadlinerService,
):
    if not await require_staff_ca(message, user_service):
        return

    headliners = await headliner_service.get_all()
    if not headliners:
        return await message.answer("Хэдлайнеров пока нет.")

    parts = []
    for headliner in headliners[:30]:
        followers = await headliner_service.count_followers(headliner.id)
        parts.append(format_headliner(headliner, followers))

    suffix = "" if len(headliners) <= 30 else f"\n\nПоказано 30 из {len(headliners)}."
    await message.answer("Список хэдлайнеров:\n\n" + "\n\n".join(parts) + suffix)


@router.message(text=["Поиск хэдлайнера"])
async def search_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return

    await state_dispenser.set(message.from_id, HeadlinerStates.SEARCH_SURNAME)
    await message.answer("Введите фамилию хэдлайнера для поиска:")


@router.message(state=HeadlinerStates.SEARCH_SURNAME)
async def search_headliner_by_surname(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    query = message.text.strip().lower()
    if len(query) < 2:
        return await message.answer("Введите минимум 2 символа фамилии.")

    headliners = await headliner_service.get_all()
    found = []
    for headliner in headliners:
        surname = (headliner.fio or "").strip().split()[0].lower() if headliner.fio else ""
        if surname.startswith(query) or query in surname:
            found.append(headliner)

    await state_dispenser.delete(message.from_id)
    if not found:
        return await message.answer("Хэдлайнеры по этой фамилии не найдены.")

    parts = []
    for headliner in found[:30]:
        followers = await headliner_service.count_followers(headliner.id)
        parts.append(format_headliner(headliner, followers))

    suffix = "" if len(found) <= 30 else f"\n\nПоказано 30 из {len(found)}."
    await message.answer("Найденные хэдлайнеры:\n\n" + "\n\n".join(parts) + suffix)


@router.message(text=["Рейтинг хэдлайнеров"])
async def headliner_rating(
        message: Message,
        user_service: IUserService,
        headliner_service: IHeadlinerService,
):
    role = await user_service.get_user_role(message.from_id, Sources.VK)
    if role not in [UserRole.STAFF_CA, UserRole.HEADLINER]:
        await message.answer("Недостаточно прав.")
        return

    rating = await headliner_service.get_rating()
    if not rating:
        return await message.answer("Хэдлайнеров пока нет.")

    lines = []
    for index, (headliner, followers) in enumerate(rating[:30], start=1):
        lines.append(f"{index}. ID {headliner.id}: {headliner.fio} - {followers} последователей")

    await message.answer("Рейтинг хэдлайнеров:\n\n" + "\n".join(lines))


@router.message(text=["Рассылка последователям"])
async def headliner_mailing_start(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    headliner = await headliner_service.get_by_user(message.from_id, Sources.VK)
    if headliner is None:
        return await message.answer("Профиль хэдлайнера не найден.")

    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.MAILING_MESSAGE,
        headliner_id=headliner.id,
    )
    await message.answer(
        "Отправьте сообщение для рассылки вашим последователям. "
        "Можно приложить фото, видео или документ."
    )


@router.message(text=["Приветственное сообщение"])
async def headliner_welcome_start(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    headliner = await headliner_service.get_by_user(message.from_id, Sources.VK)
    if headliner is None:
        return await message.answer("Профиль хэдлайнера не найден.")

    current = headliner.welcome_message or "не задано"
    await state_dispenser.set(message.from_id, HeadlinerStates.WELCOME_MESSAGE)
    await message.answer(
        "Отправьте новое приветственное сообщение для людей, которые зарегистрируются по вашей ссылке.\n\n"
        f"Текущее сообщение: {current}"
    )


@router.message(state=HeadlinerStates.WELCOME_MESSAGE)
async def headliner_welcome_save(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    text = (message.text or "").strip()
    if len(text) < 3:
        return await message.answer("Сообщение слишком короткое. Отправьте текст от 3 символов.")

    headliner = await headliner_service.update_welcome_message_by_user(
        message.from_id,
        Sources.VK,
        text
    )
    await state_dispenser.delete(message.from_id)
    if headliner is None:
        return await message.answer("Профиль хэдлайнера не найден.")

    await message.answer("Приветственное сообщение сохранено.")


@router.message(state=HeadlinerStates.MAILING_MESSAGE)
async def headliner_mailing_confirm(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    attachments = parse_attachments(message)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.MAILING_CONFIRM,
        **state.payload,
        msg_text=message.text or "",
        attachments=attachments,
    )
    att_count = len(attachments.split(",")) if attachments else 0
    await message.answer(
        "Подтвердите рассылку сообщением Да.\n\n"
        f"Текст: {message.text or '(без текста)'}\n"
        f"Вложений: {att_count}"
    )


@router.message(state=HeadlinerStates.MAILING_CONFIRM, text=["Да", "да"])
async def headliner_mailing_send(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    state = await state_dispenser.get(message.from_id)
    headliner_id = state.payload["headliner_id"]
    followers = await headliner_service.get_followers(headliner_id)

    msg_text = state.payload.get("msg_text", "")
    attachments = state.payload.get("attachments")
    if not msg_text and not attachments:
        await state_dispenser.delete(message.from_id)
        return await message.answer("Пустое сообщение не отправлено.")

    await message.answer(f"Начинаю рассылку на {len(followers)} последователей...")
    count = 0
    for follower in followers:
        if follower.follower_source != Sources.VK:
            continue
        try:
            kwargs = {"peer_id": follower.follower_id, "random_id": 0}
            if msg_text:
                kwargs["message"] = msg_text
            if attachments:
                kwargs["attachment"] = attachments
            await message.ctx_api.messages.send(**kwargs)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.debug(f"Failed to send headliner mailing to {follower.follower_id}: {e}")

    await state_dispenser.delete(message.from_id)
    await message.answer(f"Рассылка завершена. Отправлено: {count} из {len(followers)}")


@router.message(state=HeadlinerStates.MAILING_CONFIRM)
async def headliner_mailing_cancel(message: Message, state_dispenser: BuiltinStateDispenser):
    await state_dispenser.delete(message.from_id)
    await message.answer("Рассылка отменена.")
