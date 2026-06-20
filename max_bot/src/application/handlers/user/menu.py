import logging

from maxapi import F, Router
from maxapi.types import MessageCreated

from src.application.keyboards.menu_keyboard import (
    get_headliner_menu_keyboard,
    get_role_entry_keyboard,
    get_role_menu_keyboard,
    get_role_tools_keyboard,
    get_staff_ca_headliners_keyboard,
    get_staff_ca_shop_keyboard,
    get_staff_ca_tasks_keyboard,
    get_user_menu_keyboard,
)
from src.domain.entities import Sources
from src.domain.entities.user import UserRole
from src.services.interfaces import IUserService

router = Router()
logger = logging.getLogger(__name__)


async def _get_user_role(event: MessageCreated, user_service: IUserService) -> UserRole | None:
    try:
        return await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    except Exception as e:
        logger.error(f"Failed to get user role for menu display: {e}")
        return None


async def _answer(event: MessageCreated, text: str, keyboard):
    await event.message.answer(text, attachments=[keyboard.as_markup()])


@router.message_created(F.message.body.text.lower().in_([
    "меню",
    "назад",
    "на главную",
    "вернуться на главную страницу",
]))
async def show_menu(event: MessageCreated, user_service: IUserService):
    role = await _get_user_role(event, user_service)
    await _answer(event, "Меню", get_role_menu_keyboard(role))


@router.message_created(F.message.body.text == "Пользователь")
async def show_user_interface(event: MessageCreated):
    await _answer(event, "Пользовательский интерфейс:", get_user_menu_keyboard())


@router.message_created(F.message.body.text.in_([
    "Сотрудник ЦА",
    "Координатор РО",
    "Сотрудник РО",
    "Хэдлайнер",
    "Хедлайнер",
]))
async def show_role_interface(event: MessageCreated, user_service: IUserService):
    role = await _get_user_role(event, user_service)
    if role is None or role == UserRole.USER:
        await event.message.answer("Этот интерфейс недоступен для вашей роли.")
        return

    headliner_names = ("Хэдлайнер", "Хедлайнер")
    if role == UserRole.HEADLINER:
        is_current_role = event.message.body.text in headliner_names
    else:
        is_current_role = event.message.body.text == role.value
    if not is_current_role:
        await event.message.answer("Этот интерфейс недоступен для вашей роли.")
        return

    await _answer(event, f"Интерфейс роли: {role.value}", get_role_tools_keyboard(role))


async def _require_staff_ca(event: MessageCreated, user_service: IUserService) -> bool:
    role = await _get_user_role(event, user_service)
    if role != UserRole.STAFF_CA:
        await event.message.answer("Этот раздел доступен только сотруднику ЦА.")
        return False
    return True


@router.message_created(F.message.body.text == "Магазин ЦА")
async def show_staff_ca_shop(event: MessageCreated, user_service: IUserService):
    if not await _require_staff_ca(event, user_service):
        return
    await _answer(event, "Раздел: магазин", get_staff_ca_shop_keyboard())


@router.message_created(F.message.body.text.in_(["Хедлайнеры", "Хэдлайнеры"]))
async def show_staff_ca_headliners(event: MessageCreated, user_service: IUserService):
    if not await _require_staff_ca(event, user_service):
        return
    await _answer(event, "Раздел: хэдлайнеры", get_staff_ca_headliners_keyboard())


@router.message_created(F.message.body.text == "Задачи")
async def show_staff_ca_tasks(event: MessageCreated, user_service: IUserService):
    if not await _require_staff_ca(event, user_service):
        return
    await _answer(event, "Раздел: задачи", get_staff_ca_tasks_keyboard())


@router.message_created(F.message.body.text.in_(["Назад", "Назад к роли"]))
async def back_to_role_interface(event: MessageCreated, user_service: IUserService):
    role = await _get_user_role(event, user_service)
    if role is None or role == UserRole.USER:
        await _answer(event, "Пользовательский интерфейс:", get_user_menu_keyboard())
        return
    await _answer(event, f"Интерфейс роли: {role.value}", get_role_tools_keyboard(role))
