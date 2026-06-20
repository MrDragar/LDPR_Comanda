import logging
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.keyboards.gender_keyboard import get_gender_keyboard

router = Router()


@router.message_created(RegistrationStates.GENDER)
async def get_gender(event: MessageCreated, context: MemoryContext):
    gender = event.message.body.text.strip().lower() if event.message.body.text else ""
    if gender not in ["мужской", "женский"]:
        return await event.message.answer("Выберите пол на клавиатуре:",
                                          attachments=[get_gender_keyboard().as_markup()])

    await context.update_data(gender=event.message.body.text.strip())
    await context.set_state(RegistrationStates.BIRTH_DATE)
    await event.message.answer("Введите вашу дату рождения в формате ДД.ММ.ГГГГ:")
