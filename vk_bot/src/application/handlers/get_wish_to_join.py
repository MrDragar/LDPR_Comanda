from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

router = BotLabeler()


@router.message(state=RegistrationStates.WISH_TO_JOIN)
async def get_wish(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
):
    text = message.text.lower().strip() if message.text else ""
    if text not in ['да', 'нет']:
        await message.answer("Выберите вариант 'Да' или 'Нет':",
                             keyboard=get_boolean_keyboard())
        return

    state = await state_dispenser.get(message.from_id)
    new_payload = {**state.payload, "wish_to_join": (text == 'да')}

    if text == 'нет':
        await message.answer(
            message="Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР?",
            keyboard=get_boolean_keyboard(),
        )
        await state_dispenser.set(message.peer_id, RegistrationStates.NEWS_SUBSCRIPTION, **new_payload)

    else:
        await state_dispenser.set(
            message.from_id,
            RegistrationStates.HOME_ADDRESS,
            **new_payload
        )
        await message.answer(
            "Для возможности направления документов укажите свой домашний адрес")
