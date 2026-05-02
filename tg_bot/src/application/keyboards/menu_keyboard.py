from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_menu_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Загрузить видео")
    return keyword.as_markup(one_time_keyboard=True)
