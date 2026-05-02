import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.wish_to_join)
async def get_wish_to_join(
        message: types.Message, state: FSMContext
):
    answer = message.text.lower().strip()
    if not answer:
        return
    if answer not in ['да', 'нет']:
        await message.reply(
            "Хотите ли Вы присоединиться к команде ЛДПР?",
            reply_markup=get_boolean_keyboard()
        )
    logger.debug(f"Got wish to join: {answer}")
    await state.update_data(wish_to_join=(answer == 'да'))
    if answer == 'нет':
        await message.reply(
            "Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР?",
            reply_markup=get_boolean_keyboard()
        )
        await state.set_state(RegistrationStates.news_subscription)
        return

    await message.reply('Для возможности направления документов укажите свой домашний адрес')
    await state.set_state(RegistrationStates.home_address)
