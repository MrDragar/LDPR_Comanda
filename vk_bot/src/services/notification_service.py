import logging
from vkbottle import API, Bot
from aiogram import Bot as TgBot
from maxapi import Bot as MaxBot

from src.domain.entities import Sources
from src.services.interfaces import INotificationService

logger = logging.getLogger(__name__)


class NotificationService(INotificationService):
    def __init__(self, vk_bot: Bot, tg_bot: TgBot, max_bot: MaxBot):
        self.vk_bot = vk_bot
        self.tg_bot = tg_bot
        self.max_bot = max_bot

    async def notify_user_vk(self, peer_id: int, text: str, keyboard=None) -> None:
        try:
            kwargs = {"peer_id": peer_id, "message": text, "random_id": 0}
            if keyboard:
                kwargs["keyboard"] = keyboard
            await self.vk_bot.api.messages.send(**kwargs)
            logger.info(f"VK notification sent to {peer_id}")
        except Exception as e:
            logger.error(f"Failed to send VK notification to {peer_id}: {e}")

    async def notify_user_tg(self, chat_id: int, text: str) -> None:
        try:
            await self.tg_bot.send_message(chat_id=chat_id, text=text)
            logger.info(f"TG notification sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send TG notification to {chat_id}: {e}")

    async def notify_user_max(self, user_id: int, text: str) -> None:
        try:
            await self.max_bot.send_message(user_id=user_id, text=text)
            logger.info(f"MAX notification sent to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send MAX notification to {user_id}: {e}")

    async def notify_user(self, user_id: int, source: Sources, text: str) -> None:
        """Общий метод для отправки уведомлений во все поддерживаемые источники."""
        if source == Sources.VK:
            await self.notify_user_vk(user_id, text)
        elif source == Sources.TG:
            await self.notify_user_tg(user_id, text)
        elif source == Sources.MAX:
            await self.notify_user_max(user_id, text)
        else:
            logger.error(f"Unknown source: {source}")