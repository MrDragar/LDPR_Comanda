import logging
from typing import Any, Union, Dict

from aiogram.filters import BaseFilter
from aiogram.types import Message, Update

logger = logging.getLogger(__name__)


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, admin_ids: list[int]) -> Union[bool, Dict[str, Any]]:
        logger.debug(f"Checking user {message.from_user.id} privileges in {admin_ids}: {str(message.from_user.id) in admin_ids}")
        return str(message.from_user.id) in admin_ids
