import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from src.application.states import RegistrationStates
from src.services.interfaces import IUserService
from src.application.keyboards.gender_keyboard import get_gender_keyboard

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.gender)
async def get_gender(message: types.Message, state: FSMContext, user_service: IUserService):
    gender = message.text
    if not gender:
        return
    logger.debug(f"Got gender {gender}")
    if gender.strip().lower() not in ["мужской", "женский"]:
        await message.reply("Выберите пол", reply_markup=get_gender_keyboard())
        return
    await state.update_data(gender=gender)

    await message.reply(
        "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\n(например, 15.05.1990)",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationStates.birth_date)

