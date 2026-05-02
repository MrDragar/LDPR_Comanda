from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Отмена")
    return keyword.as_markup(one_time_keyboard=True)
