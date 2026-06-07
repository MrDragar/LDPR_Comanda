from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def get_region_keyboard(regions: list[str]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for r in regions[:5]:
        builder.row(CallbackButton(text=r[:40], payload=f"region:{r}"))
    builder.row(CallbackButton(text="Ввести заново", payload="retry_reg"))
    return builder
