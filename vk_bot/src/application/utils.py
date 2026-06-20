from vkbottle import Keyboard, Text
from vkbottle.bot import Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.domain.entities.user import Sources, UserRole
from src.services.interfaces import IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard


def get_cancel_kb() -> str:
    """Генерирует клавиатуру с кнопкой возврата в главное меню."""
    return (Keyboard(one_time=False)
            .add(Text("На главную"))
            .get_json())


async def handle_cancel(message: Message, state_dispenser: BuiltinStateDispenser,
                        user_service: IUserService) -> bool:
    """
    Проверяет, нажал ли пользователь кнопку отмены ('Назад', 'На главную' или 'Отмена').
    Если да - сбрасывает стейт, отправляет главное меню и возвращает True.
    Если нет - возвращает False.
    """
    # Защита от None, если пользователь отправил стикер или фото без текста
    text = (message.text or "").strip()

    if text in ["Назад", "На главную", "Отмена"]:
        await state_dispenser.delete(message.from_id)

        try:
            role = await user_service.get_user_role(message.from_id, Sources.VK)
        except Exception:
            role = UserRole.USER

        kb = get_role_menu_keyboard(role)
        await message.answer("Действие отменено. Возврат в главное меню.", keyboard=kb)
        return True

    return False