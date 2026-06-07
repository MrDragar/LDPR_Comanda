from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton


def get_personal_data_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Согласиться", payload="pd_agree"),
        CallbackButton(text="Отказаться", payload="pd_disagree")
    )
    builder.row(CallbackButton(text="Условия", payload="pd_read"))
    return builder
