from aiogram import Bot as TgBot
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.handlers.finish_registration import finish_registration
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService

router = BotLabeler()


@router.message(state=RegistrationStates.HOME_ADDRESS)
async def get_home_address(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
):
    if not message.text: return

    state = await state_dispenser.get(message.from_id)
    new_payload = {**state.payload, "home_address": message.text.strip()}

    await message.answer(
        message="Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР?",
        keyboard=get_boolean_keyboard(),
    )
    await state_dispenser.set(message.peer_id, RegistrationStates.NEWS_SUBSCRIPTION, **new_payload)
