import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.membership)
async def get_membership(message: types.Message, state: FSMContext):
    membership = message.text.lower().strip()
    if not membership:
        return
    if membership not in ['да', 'нет']:
        await message.reply('Вы являетесь членом ЛДПР?', reply_markup=get_boolean_keyboard())
        return
    logger.debug(f"Got membership: {membership}")
    await state.update_data(is_member=(membership == 'да'))
    await message.reply("Введите вашу фамилию", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(RegistrationStates.surname)
    return
