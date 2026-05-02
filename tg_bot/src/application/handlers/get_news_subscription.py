import logging

from aiogram import types, Router
from aiogram.fsm.context import FSMContext

from src.application.handlers.finish_registration import finish_registration
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates

from src.services.interfaces import IUserService

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.news_subscription)
async def get_news_subscription(
        message: types.Message, state: FSMContext, user_service: IUserService,
        log_chat: str
):
    answer = message.text.lower().strip()
    if not answer:
        return
    if answer not in ['да', 'нет']:
        await message.reply(
            "Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР?",
            reply_markup=get_boolean_keyboard()
        )
    await state.update_data(news_subscription=(answer == 'да'))
    logger.debug(f"Got news_subscription: {answer}")
    await finish_registration(user_service, state, message, log_chat)
