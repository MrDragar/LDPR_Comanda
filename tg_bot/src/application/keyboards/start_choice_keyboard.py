from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

MINI_APP_URL = "https://миниапп.командалдпр.рф/app"


def get_start_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Регистрация через приложение", web_app=WebAppInfo(url=MINI_APP_URL))
    builder.button(text="Регистрация через бота", callback_data="start_text_reg")
    builder.adjust(1)
    return builder.as_markup()
