from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_location_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Предоставить геолокацию", request_location=True)
    keyword.button(text="Отмена")
    return keyword.as_markup(one_time_keyboard=True)
