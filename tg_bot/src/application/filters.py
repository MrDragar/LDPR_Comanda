import logging
import re
from typing import Any, Union, Dict

from aiogram import types, Bot
from aiogram.filters import BaseFilter, CommandStart
from aiogram.types import Message

from src.domain.entities import Sources
from src.services.interfaces import IParticipationService, IUserService

logger = logging.getLogger(__name__)


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, admin_ids: list[int]) -> Union[bool, Dict[str, Any]]:
        logger.debug(f"Checking user {message.from_user.id} privileges in {admin_ids}: {str(message.from_user.id) in admin_ids}")
        return str(message.from_user.id) in admin_ids


class IsRegisteredFilter(BaseFilter):
    """Проверяет, завершил ли пользователь регистрацию в БД."""
    async def __call__(self, message: Message, user_service: IUserService) -> bool:
        return await user_service.is_user_exists(message.from_user.id)


class ValidatedStartFilter(CommandStart):
    """Кастомный фильтр, наследующий CommandStart с валидацией формата"""
    def __init__(self, **kwargs):
        super().__init__(deep_link=True, **kwargs)
        self.pattern = re.compile(r'^(\d+)_(tg|vk|max)$')

    async def __call__(self, message: Message, bot: Bot) -> bool | dict[str, Any]:
        is_valid = await super().__call__(message, bot)
        logger.debug('Is valid: %s', is_valid)
        if not is_valid:
            return False
        text = message.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return False
        deep_link = parts[1]
        match = self.pattern.match(deep_link)
        logger.debug('Match: %s', match)
        if match:
            return {
                "user_id": int(match.group(1)),
                "platform": match.group(2),
                "raw_deep_link": deep_link
            }
        return False


class HeadlinerStartFilter(CommandStart):
    def __init__(self, **kwargs):
        super().__init__(deep_link=True, **kwargs)
        self.pattern = re.compile(r'^hl_(\d+)_(tg|vk|max)$')

    async def __call__(self, message: Message, bot: Bot) -> bool | dict[str, Any]:
        is_valid = await super().__call__(message, bot)
        logger.debug('Is valid: %s', is_valid)
        if not is_valid:
            return False
        text = message.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return False
        deep_link = parts[1]
        match = self.pattern.match(deep_link)
        logger.debug('Match: %s', match)
        if match:
            return {
                "user_id": int(match.group(1)),
                "platform": match.group(2),
                "raw_deep_link": deep_link
            }
        return False
