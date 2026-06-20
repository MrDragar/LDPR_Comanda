from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton, LinkButton


def get_personal_data_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Согласиться", payload="pd_agree"))
    builder.row(LinkButton(
        text="Политика конфиденциальности",
        url="https://командалдпр.рф/privacypolitic"
    ))
    return builder
