import logging
import re
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


def extract_photo_url(message: Message) -> str | None:
    if not message.attachments:
        return None
    for attachment in message.attachments:
        att_type = attachment.type.value if hasattr(attachment.type, "value") else str(
            attachment.type)
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
        f"ID пользователя: {headliner.user_id} ({headliner.user_source.value.upper()})\n"
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


@router.message(text=["Добавить хедлайнера", "Создать хедлайнера"])
async def create_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return
    await state_dispenser.set(message.from_id, HeadlinerStates.CREATE_USER_ID)
    await message.answer(
        "Введите ID и source пользователя, которого нужно сделать хедлайнером.\n"
        "Формат: <id>_<source> (например, 123456_vk, 789012_tg, 345678_max).\n"
        "Пользователь должен быть уже зарегистрирован в боте."
    )


@router.message(text=["Отредактировать хедлайнера"])
async def edit_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return
    await state_dispenser.set(message.from_id, HeadlinerStates.EDIT_ID)
    await message.answer("Введите ID хедлайнера, которого нужно отредактировать.")


@router.message(state=HeadlinerStates.EDIT_ID)
async def edit_headliner_id(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    try:
        headliner_id = int(message.text.strip())
    except ValueError:
        return await message.answer("Введите числовой ID хедлайнера.")

    headliner = await headliner_service.get_by_id(headliner_id)
    if headliner is None:
        return await message.answer("Хедлайнер с таким ID не найден.")

    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_PHOTO,
        user_id=headliner.user_id,
        user_source=headliner.user_source.value,
        edit_id=headliner.id,
    )
    await message.answer(
        "Редактирование найдено.\n"
        f"{format_headliner(headliner)}\n"
        "Отправьте новое фото хедлайнера одним сообщением."
    )


@router.message(state=HeadlinerStates.CREATE_USER_ID)
async def create_headliner_user_id(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    text = message.text.strip()
    match = re.match(r'^(\d+)_(vk|tg|max)$', text, re.IGNORECASE)
    if not match:
        return await message.answer(
            "Неверный формат. Пожалуйста, отправьте ID и source в формате: 123456_vk, 789012_tg или 345678_max."
        )

    user_id = int(match.group(1))
    source_str = match.group(2).lower()

    try:
        source = Sources(source_str)
    except ValueError:
        return await message.answer("Неверный source. Допустимые значения: vk, tg, max.")

    try:
        await user_service.get_user(user_id, source)
    except Exception:
        return await message.answer("Пользователь с таким ID и source не найден в базе бота.")

    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_PHOTO,
        user_id=user_id,
        user_source=source.value,
    )
    await message.answer("Отправьте фото хедлайнера одним сообщением.")


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
    await message.answer("Введите тему, над которой будет работать хедлайнер.")


@router.message(state=HeadlinerStates.CREATE_TOPIC)
async def create_headliner_topic(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_FIO,
        **state.payload,
        topic=message.text.strip(),
    )
    await message.answer("Введите ФИО хедлайнера.")


@router.message(state=HeadlinerStates.CREATE_FIO)
async def create_headliner_fio(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_POSITION,
        **state.payload,
        fio=message.text.strip(),
    )
    await message.answer("Введите должность хедлайнера.")


@router.message(state=HeadlinerStates.CREATE_POSITION)
async def create_headliner_position(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(
        message.from_id,
        HeadlinerStates.CREATE_GROUP_LINK,
        **state.payload,
        position=message.text.strip(),
    )
    await message.answer("Введите ссылку на группу хедлайнера.")


@router.message(state=HeadlinerStates.CREATE_GROUP_LINK)
async def create_headliner_finish(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
        headliner_service: IHeadlinerService,
):
    state = await state_dispenser.get(message.from_id)
    user_source = Sources(state.payload.get("user_source", "vk"))

    headliner = await headliner_service.create_headliner(
        user_id=state.payload["user_id"],
        user_source=user_source,
        fio=state.payload["fio"],
        position=state.payload["position"],
        topic=state.payload["topic"],
        group_link=message.text.strip(),
        photo=state.payload.get("photo"),
    )
    await state_dispenser.delete(message.from_id)
    links = headliner_service.make_referral_links(headliner.id)
    await message.answer(
        "Хедлайнер сохранен.\n"
        f"{format_headliner(headliner)}\n"
        "Реферальные ссылки:\n"
        f"VK: {links['VK']}\n"
        f"MAX: {links['MAX']}\n"
        f"Telegram: {links['Telegram']}"
    )


@router.message(text=["Удалить хедлайнера"])
async def delete_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return
    await state_dispenser.set(message.from_id, HeadlinerStates.DELETE_ID)
    await message.answer("Введите ID хедлайнера, которого нужно удалить.")


@router.message(state=HeadlinerStates.DELETE_ID)
async def delete_headliner_finish(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    try:
        headliner_id = int(message.text.strip())
    except ValueError:
        return await message.answer("Введите числовой ID хедлайнера.")

    headliner = await headliner_service.delete_headliner(headliner_id)
    await state_dispenser.delete(message.from_id)
    if headliner is None:
        return await message.answer("Хедлайнер с таким ID не найден.")

    await message.answer(
        "Хедлайнер удален, пользователь возвращен к обычной роли.\n"
        f"{format_headliner(headliner)}"
    )


@router.message(text=["Список хедлайнеров"])
async def list_headliners(
        message: Message,
        user_service: IUserService,
        headliner_service: IHeadlinerService,
):
    if not await require_staff_ca(message, user_service):
        return
    headliners = await headliner_service.get_all()
    if not headliners:
        return await message.answer("Хедлайнеров пока нет.")

    parts = []
    for headliner in headliners[:30]:
        followers = await headliner_service.count_followers(headliner.id)
        parts.append(format_headliner(headliner, followers))
    suffix = "" if len(headliners) <= 30 else f"\nПоказано 30 из {len(headliners)}."
    await message.answer("Список хедлайнеров:\n" + "\n".join(parts) + suffix)


@router.message(text=["Поиск хедлайнера"])
async def search_headliner_start(
        message: Message,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
):
    if not await require_staff_ca(message, user_service):
        return
    await state_dispenser.set(message.from_id, HeadlinerStates.SEARCH_SURNAME)
    await message.answer("Введите фамилию хедлайнера для поиска:")


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
        return await message.answer("Хедлайнеры по этой фамилии не найдены.")

    parts = []
    for headliner in found[:30]:
        followers = await headliner_service.count_followers(headliner.id)
        parts.append(format_headliner(headliner, followers))
    suffix = "" if len(found) <= 30 else f"\nПоказано 30 из {len(found)}."
    await message.answer("Найденные хедлайнеры:\n" + "\n".join(parts) + suffix)


@router.message(text=["Рейтинг хедлайнеров"])
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
        return await message.answer("Хедлайнеров пока нет.")

    lines = []
    for index, (headliner, followers) in enumerate(rating[:30], start=1):
        lines.append(f"{index}. ID {headliner.id}: {headliner.fio} - {followers} последователей")
    await message.answer("Рейтинг хедлайнеров:\n" + "\n".join(lines))


@router.message(text=["Приветственное сообщение"])
async def headliner_welcome_start(
        message: Message,
        headliner_service: IHeadlinerService,
        state_dispenser: BuiltinStateDispenser,
):
    headliner = await headliner_service.get_by_user(message.from_id, Sources.VK)
    if headliner is None:
        return await message.answer("Профиль хедлайнера не найден.")
    current = headliner.welcome_message or "не задано"
    await state_dispenser.set(message.from_id, HeadlinerStates.WELCOME_MESSAGE)
    await message.answer(
        "Отправьте новое приветственное сообщение для людей, которые зарегистрируются по вашей ссылке.\n"
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
        return await message.answer("Профиль хедлайнера не найден.")
    await message.answer("Приветственное сообщение сохранено.")
