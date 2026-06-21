from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def get_delivery_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="По почте"), MessageButton(text="Заберу лично"))
    builder.row(MessageButton(text="Отмена"))
    return builder
