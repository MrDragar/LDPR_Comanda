import json
import secrets
import sqlite3
from datetime import date, datetime

from maxapi import F, Router
from maxapi.context import MemoryContext
from maxapi.types import MessageCreated

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.states import RegistrationStates
from src.core import config
from src.domain.entities import Sources
from src.domain.entities.user import UserGrade, UserRole
from src.services.interfaces import IHeadlinerService, INotificationService, IUserService

router = Router()


def _normalize_phone(value: str | None) -> str:
    value = (value or "").strip()
    if value.startswith("+7"):
        value = "8" + value[2:]
    value = "".join(symbol for symbol in value if symbol.isdigit())
    if len(value) == 11 and value.startswith("7"):
        value = "8" + value[1:]
    return value


def _normalize_fio(surname: str, name: str | None, patronymic: str | None) -> str:
    parts = [surname, name, patronymic]
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


def _pack_data(data: dict) -> dict:
    packed = {}
    for key, value in data.items():
        packed[key] = value.isoformat() if isinstance(value, (date, datetime)) else value
    return packed


def _parse_date(value):
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, "%d.%m.%Y").date()


def _ensure_table():
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_confirmations (
                token TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                request_user_id INTEGER NOT NULL,
                request_source TEXT NOT NULL,
                confirm_user_id INTEGER NOT NULL,
                confirm_source TEXT NOT NULL,
                data_json TEXT NOT NULL
            )
        """)


async def request_auth_confirmation(
        user_service: IUserService,
        notification_service: INotificationService,
        new_user_id: int,
        new_source: Sources,
        data: dict
) -> bool:
    _ensure_table()
    phone = _normalize_phone(data.get("phone") or data.get("phone_number"))
    fio = _normalize_fio(data.get("surname", ""), data.get("name"), data.get("patronymic"))
    users = await user_service.search_users_by_phone(phone)
    if data.get("merge_allowed") and data.get("merge_user_id") and data.get("merge_source"):
        candidates = [
            user for user in users
            if user.id == int(data["merge_user_id"]) and user.source.name == data["merge_source"]
        ]
    else:
        candidates = [
            user for user in users
            if user.source != new_source and _normalize_fio(user.surname, user.name, user.patronymic) == fio
        ]
    if not candidates:
        return False

    candidates.sort(key=lambda user: user.created_at or datetime.max)
    confirmer = candidates[0]
    token = secrets.token_hex(3).upper()
    payload = _pack_data({**data, "user_id": new_user_id, "source": new_source.name})

    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute(
            "DELETE FROM auth_confirmations WHERE request_user_id = ? AND request_source = ? AND status = 'pending'",
            (new_user_id, new_source.name)
        )
        conn.execute(
            """
            INSERT INTO auth_confirmations (
                token, status, created_at, request_user_id, request_source,
                confirm_user_id, confirm_source, data_json
            ) VALUES (?, 'pending', ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                datetime.now().isoformat(sep=" ", timespec="seconds"),
                new_user_id,
                new_source.name,
                confirmer.id,
                confirmer.source.name,
                json.dumps(payload, ensure_ascii=False),
            )
        )

    await notification_service.notify_user(
        confirmer.id,
        confirmer.source,
        "Запрос на авторизацию с новой площадки.\n\n"
        f"Площадка: {new_source.name}\n"
        f"ФИО: {data.get('surname')} {data.get('name')} {data.get('patronymic') or ''}\n"
        f"Телефон: {phone}\n\n"
        f"Код для авторизации: {token}\n\n"
        "Если это не вы, то проигнорируйте это сообщение."
    )
    return True


def _get_pending(token: str) -> dict | None:
    _ensure_table()
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM auth_confirmations WHERE token = ? AND status = 'pending'",
            (token.strip().upper(),)
        ).fetchone()
        return dict(row) if row else None


def _set_status(token: str, status: str):
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute(
            "UPDATE auth_confirmations SET status = ? WHERE token = ?",
            (status, token.strip().upper())
        )


def _create_user_direct(user_id: int, source: Sources, data: dict):
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO users (
                id, source, is_member, username, surname, name, patronymic,
                birth_date, phone_number, region, email, gender, city,
                wish_to_join, home_address, news_subscription, balance,
                role, grade, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                source.name,
                data.get("is_member"),
                data.get("username"),
                data.get("surname"),
                data.get("name"),
                data.get("patronymic"),
                _parse_date(data.get("birth_date")).isoformat() if data.get("birth_date") else None,
                _normalize_phone(data.get("phone") or data.get("phone_number")),
                data.get("region"),
                data.get("email"),
                data.get("gender"),
                data.get("city"),
                data.get("wish_to_join", False),
                data.get("home_address"),
                bool(data.get("news_subscription", False)),
                0,
                UserRole.USER.name,
                UserGrade.SYMPATHIZER.name,
                datetime.now().isoformat(sep=" ", timespec="seconds"),
            )
        )


async def _sync_headliner(user, user_service: IUserService, headliner_service: IHeadlinerService | None):
    if headliner_service is None:
        return
    if await headliner_service.get_by_user(user.id, user.source):
        return
    user_fio = _normalize_fio(user.surname, user.name, user.patronymic)
    user_phone = _normalize_phone(user.phone_number)
    for headliner in await headliner_service.get_all():
        try:
            headliner_user = await user_service.get_user(headliner.user_id, headliner.user_source)
        except Exception:
            continue
        if _normalize_phone(headliner_user.phone_number) != user_phone:
            continue
        if _normalize_fio(headliner_user.surname, headliner_user.name, headliner_user.patronymic) != user_fio:
            continue
        await headliner_service.create_headliner(
            user_id=user.id,
            user_source=user.source,
            fio=headliner.fio,
            position=headliner.position,
            topic=headliner.topic,
            group_link=headliner.group_link,
            photo=headliner.photo,
        )
        if headliner.welcome_message:
            await headliner_service.update_welcome_message_by_user(
                user.id, user.source, headliner.welcome_message
            )
        return


async def approve_auth(
        token: str,
        confirmer_id: int,
        confirmer_source: Sources,
        user_service: IUserService,
        notification_service: INotificationService,
        headliner_service: IHeadlinerService | None = None
) -> str:
    row = _get_pending(token)
    if row is None:
        return "Запрос не найден или уже обработан."
    if row["confirm_user_id"] != confirmer_id or row["confirm_source"] != confirmer_source.name:
        return "Этот запрос должен подтвердить первый зарегистрированный профиль."

    data = json.loads(row["data_json"])
    new_source = Sources[data["source"]]
    new_user_id = int(data["user_id"])
    if not await user_service.is_user_exists(new_user_id, new_source):
        _create_user_direct(new_user_id, new_source, data)
        user = await user_service.get_user(new_user_id, new_source)
        await _sync_headliner(user, user_service, headliner_service)
        headliner_id = data.get("headliner_id") or data.get("pending_headliner_id")
        if headliner_id and headliner_service is not None:
            await headliner_service.attach_follower(int(headliner_id), new_user_id, new_source)
    _set_status(token, "approved")
    await notification_service.notify_user(
        new_user_id,
        new_source,
        "Авторизация подтверждена. Напишите «Начать», чтобы открыть меню."
    )
    return "Авторизация подтверждена."


async def approve_auth_by_request(
        token: str,
        request_user_id: int,
        request_source: Sources,
        user_service: IUserService,
        notification_service: INotificationService,
        headliner_service: IHeadlinerService | None = None
) -> str:
    row = _get_pending(token)
    if row is None:
        return "Код не найден или уже использован."
    if row["request_user_id"] != request_user_id or row["request_source"] != request_source.name:
        return "Этот код нужно ввести на той площадке, которую вы привязываете."

    data = json.loads(row["data_json"])
    new_source = Sources[data["source"]]
    new_user_id = int(data["user_id"])
    if not await user_service.is_user_exists(new_user_id, new_source):
        _create_user_direct(new_user_id, new_source, data)
        user = await user_service.get_user(new_user_id, new_source)
        await _sync_headliner(user, user_service, headliner_service)
        headliner_id = data.get("headliner_id") or data.get("pending_headliner_id")
        if headliner_id and headliner_service is not None:
            await headliner_service.attach_follower(int(headliner_id), new_user_id, new_source)
    _set_status(token, "approved")
    await notification_service.notify_user(
        int(row["confirm_user_id"]),
        Sources[row["confirm_source"]],
        f"Площадка {new_source.name} привязана к вашему профилю."
    )
    return "Авторизация подтверждена."


async def decline_auth(
        token: str,
        confirmer_id: int,
        confirmer_source: Sources,
        notification_service: INotificationService
) -> str:
    row = _get_pending(token)
    if row is None:
        return "Запрос не найден или уже обработан."
    if row["confirm_user_id"] != confirmer_id or row["confirm_source"] != confirmer_source.name:
        return "Этот запрос должен отклонить первый зарегистрированный профиль."
    data = json.loads(row["data_json"])
    _set_status(token, "declined")
    await notification_service.notify_user(
        int(data["user_id"]),
        Sources[data["source"]],
        "Авторизация отклонена на основной площадке."
    )
    return "Авторизация отклонена."


@router.message_created(F.message.body.text == "Подтвердить авторизацию")
async def approve_auth_empty(event: MessageCreated):
    await event.message.answer("Укажите код подтверждения после команды.")


@router.message_created(RegistrationStates.AUTH_CODE)
async def approve_auth_code(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService,
        notification_service: INotificationService,
        headliner_service: IHeadlinerService
):
    token = (event.message.body.text or "").strip()
    answer = await approve_auth_by_request(
        token,
        event.from_user.user_id,
        Sources.MAX,
        user_service,
        notification_service,
        headliner_service
    )
    if answer.startswith("Авторизация подтверждена"):
        await context.clear()
    await event.message.answer(answer)
    if answer.startswith("Авторизация подтверждена"):
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("Главное меню:", attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(F.message.body.text == "Отклонить авторизацию")
async def decline_auth_empty(event: MessageCreated):
    await event.message.answer("Укажите код подтверждения после команды.")


@router.message_created(F.message.body.text.startswith("Подтвердить авторизацию"))
async def approve_auth_message(
        event: MessageCreated,
        user_service: IUserService,
        notification_service: INotificationService,
        headliner_service: IHeadlinerService
):
    token = (event.message.body.text or "").strip().split()[-1]
    answer = await approve_auth(
        token,
        event.from_user.user_id,
        Sources.MAX,
        user_service,
        notification_service,
        headliner_service
    )
    await event.message.answer(answer)


@router.message_created(F.message.body.text.startswith("Отклонить авторизацию"))
async def decline_auth_message(
        event: MessageCreated,
        notification_service: INotificationService
):
    token = (event.message.body.text or "").strip().split()[-1]
    answer = await decline_auth(token, event.from_user.user_id, Sources.MAX, notification_service)
    await event.message.answer(answer)
