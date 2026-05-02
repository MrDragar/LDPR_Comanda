from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_boolean_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Да")
    keyword.button(text="Нет")
    return keyword.as_markup(one_time_keyboard=True)
