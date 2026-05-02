from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_personal_data_keyboard() -> InlineKeyboardMarkup:
    keyword = InlineKeyboardBuilder()
    keyword.button(text="Согласиться", callback_data="pd_agree")
    keyword.button(text="Отказаться", callback_data="pd_disagree")
    keyword.button(text="Прочитать условие соглашения", callback_data="pd_read")
    return keyword.as_markup()
