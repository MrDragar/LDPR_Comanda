from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService
from src.domain import exceptions
from src.application.keyboards.gender_keyboard import get_gender_keyboard

router = Router()


@router.message_created(RegistrationStates.SURNAME)
async def get_surname(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    try:
        surname = await user_service.validate_fio_part(event.message.body.text.strip(), 'Фамилия')
        await context.update_data(surname=surname)
        await context.set_state(RegistrationStates.NAME)
        await event.message.answer("Теперь введите ваше имя:")
    except exceptions.FioFormatError as e:
        await event.message.answer(str(e))


@router.message_created(RegistrationStates.NAME)
async def get_name(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    try:
        name = await user_service.validate_fio_part(event.message.body.text.strip(), 'Имя')
        await context.update_data(name=name)
        await context.set_state(RegistrationStates.PATRONYMIC)
        await event.message.answer("Введите ваше отчество (если нет, отправьте '-' или 'нет'):")
    except exceptions.FioFormatError as e:
        await event.message.answer(str(e))


@router.message_created(RegistrationStates.PATRONYMIC)
async def get_patronymic(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    val = event.message.body.text.strip()
    patronymic = None if val.lower() in ['-', 'нет', 'нету'] else val
    try:
        if patronymic:
            patronymic = await user_service.validate_fio_part(patronymic, 'Отчество')
        await context.update_data(patronymic=patronymic)
        await context.set_state(RegistrationStates.GENDER)
        await event.message.answer("Укажите ваш пол:", attachments=[get_gender_keyboard().as_markup()])
    except exceptions.FioFormatError as e:
        await event.message.answer(str(e))
