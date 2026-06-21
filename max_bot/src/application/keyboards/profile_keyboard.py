from maxapi.types import MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def get_profile_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Реферальная ссылка"))
    builder.row(MessageButton(text="Список покупок"))
    builder.row(MessageButton(text="Список мероприятий"))
    builder.row(MessageButton(text="Посмотреть рейтинг"))
    builder.row(MessageButton(text="На главную"))
    return builder


def get_back_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Назад"), MessageButton(text="На главную"))
    return builder
