from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.core.di import DeclarativeContainer


class DIProvideMiddleware(BaseMiddleware):
    __container: DeclarativeContainer

    def __init__(self, container: DeclarativeContainer):
        self.__container = container

    async def __call__(self, handler: Callable[
        [TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: Dict[str, Any]) -> Any:
        return await handler(event, data | self.__container.providers)
