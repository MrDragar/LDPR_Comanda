import logging
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService
from src.domain import exceptions

router = Router()


@router.message_created(RegistrationStates.EMAIL)
async def get_email(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    val = event.message.body.text.strip()
    email = None
    if val.lower() not in ['-', 'нет', 'нету', 'отсутствует', '']:
        try:
            email = await user_service.validate_email(val)
        except exceptions.EmailBadFormatError:
            return await event.message.answer("Некорректный формат почты. Введите почту заново")
        except exceptions.EmailAlreadyExistsError:
            return await event.message.answer(
                "Пользователь с данной почтой уже существует. Введите почту заново")
        except Exception:
            return await event.message.answer("Произошла неизвестная ошибка")

    await context.update_data(email=email)
    await context.set_state(RegistrationStates.REGION_BY_TEXT)
    await event.message.answer("Укажите регион вашего проживания (начните вводить название):")
