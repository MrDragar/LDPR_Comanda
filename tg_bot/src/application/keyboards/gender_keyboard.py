from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_gender_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Мужской")
    keyword.button(text="Женский")
    return keyword.as_markup(one_time_keyboard=True)
