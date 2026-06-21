from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def get_quiz_keyboard(options: list[str]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.row(MessageButton(text=opt))
    builder.row(MessageButton(text="Отмена"))
    return builder
