from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.domain.entities.user import UserRole


def get_role_menu_keyboard(role: UserRole | None) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Личный кабинет"))
    builder.row(MessageButton(text="Меню"))
    return builder
