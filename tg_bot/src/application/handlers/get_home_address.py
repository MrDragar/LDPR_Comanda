import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.handlers.finish_registration import finish_registration
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.home_address)
async def get_home_address(
        message: types.Message, state: FSMContext,
        user_service: IUserService, log_chat: str
):
    home_address = message.text.strip()
    if not home_address:
        return
    logger.debug(f"Got home address: {home_address}")
    await state.update_data(home_address=home_address)
    await message.reply(
        "Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР?",
        reply_markup=get_boolean_keyboard()
    )
    await state.set_state(RegistrationStates.news_subscription)
