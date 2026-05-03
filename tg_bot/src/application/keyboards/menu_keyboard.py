from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_menu_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Реферальная ссылка")
    keyword.button(text="Посмотреть свои номера")
    keyword.adjust(2, 1)
    return keyword.as_markup(one_time_keyboard=False)
