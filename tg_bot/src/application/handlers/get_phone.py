import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.states import RegistrationStates
from src.domain import exceptions
from src.services.interfaces import IUserService

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(RegistrationStates.phone)
async def get_phone_number(message: types.Message, state: FSMContext, user_service: IUserService):
    phone = message.text
    if not phone:
        return
    logger.debug(f"Got phone number {phone}")
    try:
        phone = await user_service.validate_phone(phone)
    except exceptions.PhoneBadFormatError:
        return message.reply("Некорректный формат телефона. Введите номер телефона в следующем формате: +79876543210")
    except exceptions.PhoneBadCountryError:
        return message.reply("К сожалению, мы поддерживаем работу только с российскими номерами. Попробуйте ввести другой номер телефона")
    except exceptions.PhoneAlreadyExistsError:
        return message.reply("Пользователь с данным номером телефона уже существует")
    except:
        return message.reply("Произошла неизвестная ошибка")
    await state.update_data(phone=phone)
    await message.reply("Введите адрес вашей электронной почты")
    await state.set_state(RegistrationStates.email)

