import logging
from datetime import datetime

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.states import RegistrationStates

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.birth_date)
async def get_birth_date(message: types.Message, state: FSMContext):
    if not message.text:
        return
    birth_date_str = message.text.strip()

    try:
        birth_date = datetime.strptime(birth_date_str, "%d.%m.%Y").date()
    except ValueError:
        await message.reply(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n(например, 15.05.1990)")
        return

    if birth_date > datetime.now().date():
        await message.reply(
            "Дата рождения не может быть в будущем. Попробуйте еще раз.")
        return

    age = datetime.now().date().year - birth_date.year
    if age < 18:
        await message.reply(
            "Вам должно быть не менее 18 лет. Попробуйте еще раз.")
        return
    if age > 120:
        await message.reply(
            "Пожалуйста, введите корректную дату рождения. Попробуйте еще раз.")
        return

    logger.debug(f"Got birth date: {birth_date}")
    await state.update_data(birth_date=birth_date)
    await state.set_state(RegistrationStates.phone)
    await message.reply(
        f"Введите ваш номер телефона"
    )
