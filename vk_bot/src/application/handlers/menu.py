import logging
from vkbottle.bot import BotLabeler, Message
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.services.interfaces import IUserService
from src.domain.entities.user import Sources

logger = logging.getLogger(__name__)
router = BotLabeler()


@router.message(text=['Меню', 'На главную'])
async def show_menu(message: Message, user_service: IUserService) -> None:
    try:
        role = await user_service.get_user_role(message.from_id, Sources.VK)
    except Exception as e:
        logger.error(f"Failed to get user role for menu display: {e}")
        role = None
    await message.answer("Главное меню:", keyboard=get_role_menu_keyboard(role))
