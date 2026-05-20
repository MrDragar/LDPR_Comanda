import logging
from vkbottle.bot import Message
from vkbottle import GroupEventType, GroupTypes
from vkbottle.dispatch.rules import ABCRule

from src.domain.entities import Sources

logger = logging.getLogger(__name__)


class AdminFilter(ABCRule[Message]):
    async def check(self, event: Message, **kwargs) -> bool:
        # admin_ids прокидывается через middleware или ctx
        admin_ids = event.ctx_api.admin_ids 
        is_admin = str(event.from_id) in admin_ids
        logger.debug(f"Checking user {event.from_id} privileges: {is_admin}")
        return is_admin


class CMDRule(ABCRule[GroupTypes.MessageEvent]):
    def __init__(self, cmd):
        self.cmd = cmd

    async def check(self, event: GroupTypes.MessageEvent, **kwargs) -> bool:
        payload = event.object.payload
        if 'cmd' not in payload:
            return False
        return payload['cmd'] == self.cmd


async def check_role(user_service, user_id: int, allowed_roles: list) -> bool:
    try:
        role = await user_service.get_user_role(user_id, Sources.VK)
        return role in allowed_roles
    except:
        return False
