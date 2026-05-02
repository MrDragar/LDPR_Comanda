import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.city)
async def get_city(message: types.Message, state: FSMContext):
    city = message.text
    if not city:
        return
    logger.debug(f"Got city {city}")
    if not city or len(city) < 2:
        return await message.reply(
            "Введите название вашего города или населённого пункта")
    await state.update_data(city=city)
    data = await state.get_data()
    if data['is_member']:
        await message.reply(
            'Укажите свой домашний адрес'
        )
        return await state.set_state(RegistrationStates.home_address)
    await message.reply("Хотите ли Вы присоединиться к команде ЛДПР?", reply_markup=get_boolean_keyboard())
    await state.set_state(RegistrationStates.wish_to_join)
