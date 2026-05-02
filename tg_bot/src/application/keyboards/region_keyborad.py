from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.application.callbacks import RegionCallback, RetryRegionCallback


def get_region_keyboard(regions: list[str]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for region in regions:
        keyboard.button(text=region, callback_data=RegionCallback(region=region[:min(30, len(region))]).pack())
    keyboard.button(text="Ввести регион заново", callback_data=RetryRegionCallback().pack())
    keyboard.adjust(1, repeat=True)
    return keyboard.as_markup()
