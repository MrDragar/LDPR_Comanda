from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_menu_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Личный кабинет")
    return keyword.as_markup(one_time_keyboard=False, resize_keyboard=True)
