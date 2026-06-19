from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_quiz_keyboard(options: list[str]) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for opt in options:
        builder.button(text=opt)
    builder.button(text="Отмена")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
