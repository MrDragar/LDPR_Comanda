from aiogram.utils.keyboard import ReplyKeyboardMarkup, ReplyKeyboardBuilder


def get_post_keyboard() -> ReplyKeyboardMarkup:
    keyword = ReplyKeyboardBuilder()
    keyword.button(text="Подтвердить")
    keyword.button(text="Отменить")
    return keyword.as_markup()
