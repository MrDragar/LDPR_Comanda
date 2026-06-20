import logging
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard

router = Router()


@router.message_created(RegistrationStates.HOME_ADDRESS)
async def get_home_address(event: MessageCreated, context: MemoryContext):
    if not event.message.body.text: return
    home_address = event.message.body.text.strip()

    await context.update_data(home_address=home_address)
    await context.set_state(RegistrationStates.NEWS_SUBSCRIPTION)
    await event.message.answer(
        "Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР?",
        attachments=[get_boolean_keyboard().as_markup()])