from datetime import datetime
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import RegistrationStates

router = BotLabeler()


@router.message(state=RegistrationStates.BIRTH_DATE)
async def get_birth_date(message: Message, state_dispenser: BuiltinStateDispenser):
    if not message.text: return

    try:
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        now = datetime.now().date()
        age = now.year - birth_date.year - (
                    (now.month, now.day) < (birth_date.month, birth_date.day))

        if birth_date > now:
            return "Дата рождения не может быть в будущем."
        if age < 18:
            return "Регистрация доступна только лицам старше 18 лет."
        if age > 120:
            return "Введите корректную дату рождения."

        state = await state_dispenser.get(message.from_id)
        await state_dispenser.set(message.from_id,
                                          RegistrationStates.PHONE,
                                          **state.payload,
                                          birth_date=birth_date)
        await message.answer(
            "Введите ваш номер телефона (например, +79001234567):")
    except ValueError:
        return "Неверный формат. Пожалуйста, используйте ДД.ММ.ГГГГ"
