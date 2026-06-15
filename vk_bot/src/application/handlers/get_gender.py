from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.keyboards.gender_keyboard import get_gender_keyboard
from src.application.states import RegistrationStates

router = BotLabeler()


@router.message(state=RegistrationStates.GENDER)
async def get_gender(message: Message, state_dispenser: BuiltinStateDispenser):
    gender = message.text.strip().lower() if message.text else ""
    if gender not in ["мужской", "женский"]:
        await message.answer("Пожалуйста, выберите пол на клавиатуре:",
                             keyboard=get_gender_keyboard())
        return

    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(message.from_id,
                              RegistrationStates.BIRTH_DATE,
                              **state.payload, gender=message.text)
    await message.answer(
        "Введите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 15.05.1995):")
