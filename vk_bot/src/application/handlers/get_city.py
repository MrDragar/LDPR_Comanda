import logging

from aiogram import Bot as TgBot
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

router = BotLabeler()


@router.message(state=RegistrationStates.CITY)
async def get_city(
        message: Message, state_dispenser: BuiltinStateDispenser,
):
    city = message.text.strip() if message.text else ""
    if len(city) < 2:
        return "Введите корректное название города."

    state = await state_dispenser.get(message.from_id)
    new_payload = {**state.payload, "city": city}
    logging.debug(new_payload)
    if new_payload['is_member']:
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.HOME_ADDRESS,
                                  **new_payload)
        await message.answer(
            "Укажите ваш домашний адрес:"
        )
    else:
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.WISH_TO_JOIN,
                                  **new_payload)
        await message.answer("Хотите ли Вы присоединиться к команде ЛДПР?",
                             keyboard=get_boolean_keyboard())
