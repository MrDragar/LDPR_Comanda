import re

from maxapi import F, Router
from maxapi.context import MemoryContext
from maxapi.types import MessageCreated

from src.application.keyboards.menu_keyboard import get_staff_ca_headliners_keyboard
from src.application.states import HeadlinerStates
from src.domain.entities import Sources
from src.domain.entities.headliner import Headliner
from src.domain.entities.user import User, UserRole
from src.services.interfaces import IHeadlinerService, INotificationService, IUserService

router = Router()


def _text(event: MessageCreated) -> str:
    body = getattr(event.message, "body", None)
    return (getattr(body, "text", None) or "").strip()


def _profile_id(value: str) -> int | None:
    match = re.search(r"(\d+)", value)
    if not match:
        return None
    return int(match.group(1))


def _normalize_phone(value: str) -> str:
    value = (value or "").strip()
    if value.startswith("+7"):
        value = "8" + value[2:]
    value = "".join([symbol for symbol in value if symbol.isdigit()])
    if len(value) == 11 and value.startswith("7"):
        value = "8" + value[1:]
    return value


def _user_fio(user: User) -> str:
    return " ".join([part for part in [user.surname, user.name, user.patronymic] if part])


def _pack_users(users: list[User]) -> list[dict]:
    return [{"id": user.id, "source": user.source.name} for user in users]


def _format_user_group(users: list[User]) -> str:
    first = users[0]
    platforms = ", ".join([user.source.name for user in users])
    return f"{_user_fio(first)} | {first.phone_number} | {platforms}"


async def _find_users_for_headliner(user_service: IUserService, fio: str, phone_value: str) -> list[User]:
    phone = _normalize_phone(phone_value)
    parts = fio.strip().split()
    if len(phone) != 11 or len(parts) < 2:
        return []

    users = await user_service.search_users_by_phone(phone)
    if not users:
        return []

    fio_users = []
    surname = parts[0]
    name = parts[1]
    patronymic = parts[2] if len(parts) > 2 else None
    for user in users:
        direct = user.surname.lower() == surname.lower() and (user.name or "").lower() == name.lower()
        reverse = user.surname.lower() == name.lower() and (user.name or "").lower() == surname.lower()
        patronymic_ok = patronymic is None or (user.patronymic or "").lower() == patronymic.lower()
        if (direct or reverse) and patronymic_ok:
            fio_users.append(user)
    return fio_users


def _group_users_for_query(query: str, users: list[User]) -> list[list[User]]:
    groups = {}
    for user in users:
        groups.setdefault((_user_fio(user).lower(), user.phone_number), []).append(user)
    return list(groups.values())


def _headliner_text(headliner: Headliner, followers_count: int | None = None) -> str:
    lines = [
        f"ID: {headliner.id}",
        f"ФИО: {headliner.fio}",
        f"Профиль: {headliner.user_id}",
        f"Должность: {headliner.position}",
        f"Тема: {headliner.topic}",
        f"Группа: {headliner.group_link}",
    ]
    if headliner.photo:
        lines.append(f"Фото: {headliner.photo}")
    if followers_count is not None:
        lines.append(f"Последователей: {followers_count}")
    return "\n".join(lines)


async def _is_staff_ca(event: MessageCreated, user_service: IUserService) -> bool:
    try:
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    except Exception:
        role = None
    if role != UserRole.STAFF_CA:
        await event.message.answer("Этот раздел доступен только сотруднику ЦА.")
        return False
    return True


async def _is_headliner(event: MessageCreated, user_service: IUserService) -> bool:
    try:
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    except Exception:
        role = None
    if role != UserRole.HEADLINER:
        await event.message.answer("Этот раздел доступен только хэдлайнеру.")
        return False
    return True


async def _find_headliners(headliner_service: IHeadlinerService, value: str) -> list[Headliner]:
    headliners = await headliner_service.get_all()
    value = value.strip().lower()
    if value.isdigit():
        found = await headliner_service.get_by_id(int(value))
        return [found] if found else []
    return [h for h in headliners if value in h.fio.lower()]


@router.message_created(F.message.body.text.in_(["Добавить хэдлайнера", "Добавить хедлайнера"]))
async def start_create_headliner(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService
):
    if not await _is_staff_ca(event, user_service):
        return
    await context.set_state(HeadlinerStates.CREATE_PROFILE_LINK)
    await event.message.answer(
        "Введите ФИО пользователя."
    )


@router.message_created(HeadlinerStates.CREATE_PROFILE_LINK)
async def get_headliner_profile(event: MessageCreated, context: MemoryContext):
    await context.update_data(fio_query=_text(event))
    await context.set_state(HeadlinerStates.CREATE_PHONE)
    await event.message.answer("Введите номер телефона пользователя.")


@router.message_created(HeadlinerStates.CREATE_PHONE)
async def get_headliner_phone(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    data = await context.get_data()
    fio_query = data["fio_query"]
    users = await _find_users_for_headliner(user_service, fio_query, _text(event))
    groups = _group_users_for_query(fio_query, users)
    if not groups:
        await context.set_state(HeadlinerStates.CREATE_PROFILE_LINK)
        await event.message.answer("Пользователь не найден. Введите ФИО еще раз.")
        return

    if len(groups) > 1:
        text = "\n".join([f"{index}. {_format_user_group(group)}" for index, group in enumerate(groups[:10], start=1)])
        await event.message.answer(
            "Найдено несколько пользователей. Введите номер телефона нужного пользователя:\n\n" + text
        )
        return

    users = groups[0]
    await context.update_data(users=_pack_users(users), fio=_user_fio(users[0]))
    await context.set_state(HeadlinerStates.CREATE_POSITION)
    await event.message.answer(
        "Пользователь найден:\n"
        f"{_format_user_group(users)}\n\n"
        "Введите должность хэдлайнера:"
    )


@router.message_created(HeadlinerStates.CREATE_FIO)
async def get_headliner_fio(event: MessageCreated, context: MemoryContext):
    await context.update_data(fio=_text(event))
    await context.set_state(HeadlinerStates.CREATE_POSITION)
    await event.message.answer("Введите должность хэдлайнера:")


@router.message_created(HeadlinerStates.CREATE_POSITION)
async def get_headliner_position(event: MessageCreated, context: MemoryContext):
    await context.update_data(position=_text(event))
    await context.set_state(HeadlinerStates.CREATE_TOPIC)
    await event.message.answer("Введите тему, над которой будет работать хэдлайнер:")


@router.message_created(HeadlinerStates.CREATE_TOPIC)
async def get_headliner_topic(event: MessageCreated, context: MemoryContext):
    await context.update_data(topic=_text(event))
    await context.set_state(HeadlinerStates.CREATE_GROUP_LINK)
    await event.message.answer("Введите ссылку на группу хэдлайнера:")


@router.message_created(HeadlinerStates.CREATE_GROUP_LINK)
async def get_headliner_group(event: MessageCreated, context: MemoryContext):
    await context.update_data(group_link=_text(event))
    await context.set_state(HeadlinerStates.CREATE_PHOTO)
    await event.message.answer("Введите ссылку на фото хэдлайнера или '-' если фото нет:")


@router.message_created(HeadlinerStates.CREATE_PHOTO)
async def finish_create_headliner(
        event: MessageCreated,
        context: MemoryContext,
        headliner_service: IHeadlinerService,
        user_service: IUserService
):
    data = await context.get_data()
    photo = _text(event)
    created = []
    for user_data in data["users"]:
        headliner = await headliner_service.create_headliner(
            user_id=user_data["id"],
            fio=data["fio"],
            position=data["position"],
            topic=data["topic"],
            group_link=data["group_link"],
            photo=None if photo in ("", "-") else photo,
            user_source=Sources[user_data["source"]]
        )
        created.append(headliner)
    lines = []
    for headliner in created:
        links = headliner_service.make_referral_links(headliner.id)
        lines.append(
            f"{headliner.user_source.name}: ID {headliner.id}\n"
            f"VK: {links['VK']}\n"
            f"MAX: {links['MAX']}\n"
            f"Telegram: {links['Telegram']}"
        )
    await context.clear()
    await event.message.answer(
        "Хэдлайнер создан на площадках пользователя.\n\n"
        f"ФИО: {data['fio']}\n"
        f"Должность: {data['position']}\n"
        f"Тема: {data['topic']}\n"
        f"Группа: {data['group_link']}\n\n"
        "Реферальные ссылки:\n\n" + "\n\n".join(lines),
        attachments=[get_staff_ca_headliners_keyboard().as_markup()]
    )


@router.message_created(F.message.body.text.in_(["Список хэдлайнеров", "Список хедлайнеров"]))
async def list_headliners(
        event: MessageCreated,
        user_service: IUserService,
        headliner_service: IHeadlinerService
):
    if not await _is_staff_ca(event, user_service):
        return
    headliners = await headliner_service.get_all()
    if not headliners:
        await event.message.answer("Хэдлайнеры пока не созданы.")
        return
    text = "\n\n".join([_headliner_text(h) for h in headliners])
    await event.message.answer(text)


@router.message_created(F.message.body.text.in_(["Рейтинг хэдлайнеров", "Рейтинг хедлайнеров"]))
async def headliner_rating(event: MessageCreated, headliner_service: IHeadlinerService):
    rating = await headliner_service.get_rating()
    if not rating:
        await event.message.answer("Рейтинг хэдлайнеров пока пуст.")
        return
    lines = []
    for index, (headliner, count) in enumerate(rating, start=1):
        lines.append(f"{index}. {headliner.fio} — {count} последователей")
    await event.message.answer("\n".join(lines))


@router.message_created(F.message.body.text.in_(["Поиск хэдлайнера", "Поиск хедлайнера"]))
async def start_search_headliner(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService
):
    if not await _is_staff_ca(event, user_service):
        return
    await context.set_state(HeadlinerStates.SEARCH)
    await event.message.answer("Введите фамилию или ID хэдлайнера:")


@router.message_created(HeadlinerStates.SEARCH)
async def search_headliner(
        event: MessageCreated,
        context: MemoryContext,
        headliner_service: IHeadlinerService
):
    found = await _find_headliners(headliner_service, _text(event))
    await context.clear()
    if not found:
        await event.message.answer("Хэдлайнеры не найдены.")
        return
    lines = []
    for headliner in found:
        count = await headliner_service.count_followers(headliner.id)
        lines.append(_headliner_text(headliner, count))
    await event.message.answer("\n\n".join(lines))


@router.message_created(F.message.body.text.in_(["Удалить хэдлайнера", "Удалить хедлайнера"]))
async def start_delete_headliner(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService
):
    if not await _is_staff_ca(event, user_service):
        return
    await context.set_state(HeadlinerStates.DELETE_SEARCH)
    await event.message.answer("Введите ID или фамилию хэдлайнера для удаления:")


@router.message_created(HeadlinerStates.DELETE_SEARCH)
async def delete_headliner(
        event: MessageCreated,
        context: MemoryContext,
        headliner_service: IHeadlinerService
):
    found = await _find_headliners(headliner_service, _text(event))
    await context.clear()
    if len(found) != 1:
        await event.message.answer("Нужно найти ровно одного хэдлайнера. Уточните запрос.")
        return
    deleted = await headliner_service.delete_headliner(found[0].id)
    await event.message.answer(f"Хэдлайнер удален: {deleted.fio}")


@router.message_created(F.message.body.text.in_(["Отредактировать хэдлайнера", "Отредактировать хедлайнера"]))
async def start_edit_headliner(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService
):
    if not await _is_staff_ca(event, user_service):
        return
    await context.set_state(HeadlinerStates.EDIT_SEARCH)
    await event.message.answer("Введите ID или фамилию хэдлайнера для редактирования:")


@router.message_created(HeadlinerStates.EDIT_SEARCH)
async def choose_edit_headliner(
        event: MessageCreated,
        context: MemoryContext,
        headliner_service: IHeadlinerService
):
    found = await _find_headliners(headliner_service, _text(event))
    if len(found) != 1:
        await event.message.answer("Нужно найти ровно одного хэдлайнера. Уточните запрос.")
        return
    await context.update_data(headliner_id=found[0].id)
    await context.set_state(HeadlinerStates.EDIT_FIELD)
    await event.message.answer("Что изменить? Напишите: ФИО, должность, тема, группа, фото")


@router.message_created(HeadlinerStates.EDIT_FIELD)
async def choose_edit_field(event: MessageCreated, context: MemoryContext):
    fields = {
        "фио": "fio",
        "должность": "position",
        "тема": "topic",
        "группа": "group_link",
        "фото": "photo",
    }
    field = fields.get(_text(event).lower())
    if field is None:
        await event.message.answer("Можно изменить: ФИО, должность, тема, группа, фото")
        return
    await context.update_data(field=field)
    await context.set_state(HeadlinerStates.EDIT_VALUE)
    await event.message.answer("Введите новое значение:")


@router.message_created(HeadlinerStates.EDIT_VALUE)
async def save_edit_headliner(
        event: MessageCreated,
        context: MemoryContext,
        headliner_service: IHeadlinerService
):
    data = await context.get_data()
    value = _text(event)
    if data["field"] == "photo" and value == "-":
        value = None
    headliner = await headliner_service.update_headliner(
        data["headliner_id"],
        **{data["field"]: value}
    )
    await context.clear()
    await event.message.answer(f"Хэдлайнер обновлен.\n\n{_headliner_text(headliner)}")


@router.message_created(F.message.body.text == "Приветственное сообщение")
async def start_welcome_message(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService
):
    if not await _is_headliner(event, user_service):
        return
    await context.set_state(HeadlinerStates.WELCOME_TEXT)
    await event.message.answer("Введите приветственное сообщение для новых последователей:")


@router.message_created(HeadlinerStates.WELCOME_TEXT)
async def save_welcome_message(
        event: MessageCreated,
        context: MemoryContext,
        headliner_service: IHeadlinerService
):
    headliner = await headliner_service.update_welcome_message_by_user(
        event.from_user.user_id,
        Sources.MAX,
        _text(event)
    )
    await context.clear()
    if headliner is None:
        await event.message.answer("Ваш профиль хэдлайнера не найден.")
        return
    await event.message.answer("Приветственное сообщение сохранено.")


@router.message_created(F.message.body.text == "Рассылка последователям")
async def start_mailing(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService
):
    if not await _is_headliner(event, user_service):
        return
    await context.set_state(HeadlinerStates.MAILING_TEXT)
    await event.message.answer("Введите текст рассылки для ваших последователей:")


@router.message_created(HeadlinerStates.MAILING_TEXT)
async def send_mailing(
        event: MessageCreated,
        context: MemoryContext,
        headliner_service: IHeadlinerService,
        notification_service: INotificationService
):
    headliner = await headliner_service.get_by_user(event.from_user.user_id, Sources.MAX)
    if headliner is None:
        await context.clear()
        await event.message.answer("Ваш профиль хэдлайнера не найден.")
        return
    followers = await headliner_service.get_followers(headliner.id)
    sent = 0
    for follower in followers:
        await notification_service.notify_user(follower.follower_id, follower.follower_source, _text(event))
        sent += 1
    await context.clear()
    await event.message.answer(f"Рассылка отправлена. Получателей: {sent}.")
