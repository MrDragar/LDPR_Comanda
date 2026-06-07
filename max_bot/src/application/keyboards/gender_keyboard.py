from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def get_gender_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Мужской"), MessageButton(text="Женский"))
    return builder
