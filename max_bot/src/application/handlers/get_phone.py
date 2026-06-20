import logging
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService
from src.domain import exceptions

router = Router()


@router.message_created(RegistrationStates.PHONE)
async def get_phone(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    try:
        phone = await user_service.validate_phone(event.message.body.text.strip())
        await context.update_data(phone=phone)
        await context.set_state(RegistrationStates.EMAIL)
        await event.message.answer("Введите адрес вашей электронной почты (если нет почты, отправьте прочерк '-' или слово 'нет'):")
    except exceptions.PhoneBadFormatError:
        await event.message.answer("Некорректный формат. Пример: +79991234567")
    except exceptions.PhoneBadCountryError:
        await event.message.answer("К сожалению, мы поддерживаем работу только с российскими номерами. Попробуйте ввести другой номер телефона")
    except exceptions.PhoneAlreadyExistsError:
        await event.message.answer("Пользователь с данным номером телефона уже существует")
    except Exception:
        await event.message.answer("Неизвестная ошибка")
