from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def get_boolean_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Да"), MessageButton(text="Нет"))
    return builder
