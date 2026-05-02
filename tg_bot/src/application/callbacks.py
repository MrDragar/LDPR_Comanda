from aiogram.filters.callback_data import CallbackData


class RegionCallback(CallbackData, prefix="reg"):
    region: str


class RetryRegionCallback(CallbackData, prefix="retry_reg"):
    ...
