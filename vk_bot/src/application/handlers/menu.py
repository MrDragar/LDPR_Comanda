from vkbottle.bot import BotLabeler, Message

from src.application.keyboards.menu_keyboard import get_menu_keyboard

router = BotLabeler()


@router.message(text=['Посмотреть свои номера'])
async def show_numbers(
        message: Message,
):
    if message.peer_id <= 0:
        return
    await message.answer("Меню", keyboard=get_menu_keyboard())

