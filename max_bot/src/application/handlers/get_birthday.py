from datetime import datetime
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates

router = Router()


@router.message_created(RegistrationStates.BIRTH_DATE)
async def get_birth_date(event: MessageCreated, context: MemoryContext):
    if not event.message.body.text: return
    try:
        birth_date = datetime.strptime(event.message.body.text.strip(), "%d.%m.%Y").date()
        now = datetime.now().date()
        age = now.year - birth_date.year - (
                    (now.month, now.day) < (birth_date.month, birth_date.day))

        if birth_date > now:
            return await event.message.answer("Дата рождения не может быть в будущем.")
        if age > 120:
            return await event.message.answer("Введите корректную дату рождения.")
        if age < 14:
            return await event.message.answer("Вам должно быть не менее 14 лет")

        await context.update_data(birth_date=birth_date)
        await context.set_state(RegistrationStates.PHONE)
        await event.message.answer("Введите ваш номер телефона (например, +79001234567):")
    except ValueError:
        await event.message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ")
