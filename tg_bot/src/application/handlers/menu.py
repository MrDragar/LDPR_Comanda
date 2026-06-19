import logging
from aiogram import Router, types, F
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities.user import Sources
from src.services.interfaces import IUserService

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(F.text.in_(["Меню", "На главную", "Вернуться на главную страницу"]))
async def show_menu(message: types.Message, user_service: IUserService):
    try:
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    except Exception as e:
        logger.error(f"Failed to get user role for menu display: {e}")
        role = None
    await message.answer("Главное меню:", reply_markup=get_role_menu_keyboard(role))