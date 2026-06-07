import logging
from vkbottle import API, Bot
from aiogram import Bot as TgBot
from src.services.interfaces import INotificationService

logger = logging.getLogger(__name__)


class NotificationService(INotificationService):
    def __init__(self, vk_bot: Bot, tg_bot: TgBot):
        self.vk_bot = vk_bot
        self.tg_bot = tg_bot

    async def notify_user_vk(self, peer_id: int, text: str, keyboard: str | None = None) -> None:
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
