import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.states import RegistrationStates
from src.domain import exceptions
from src.services.interfaces import IUserService

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.email)
async def get_email(message: types.Message, state: FSMContext, user_service: IUserService):
    email = message.text
    if not email:
        return
    logger.debug(f"Got email {email}")
    try:
        email = await user_service.validate_email(email)
    except exceptions.EmailBadFormatError:
        return message.reply("Некорректный формат почты. Введите почту заново")
    except exceptions.EmailAlreadyExistsError:
        return message.reply("Пользователь с данной почтой уже существует уже существует. Введите почту заново")
    except Exception as e:
        logger.debug(f"Ошибка {e}")
        return message.reply("Произошла неизвестная ошибка")
    await state.update_data(email=email)
    await message.reply("Укажите регион вашего проживания")
    await state.set_state(RegistrationStates.region_by_text)
