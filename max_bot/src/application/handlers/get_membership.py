import logging
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard

router = Router()


@router.message_created(RegistrationStates.MEMBERSHIP)
async def get_membership(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text.lower().strip() if event.message.body.text else ""
    if text not in ['да', 'нет']:
        return await event.message.answer("Вы являетесь членом ЛДПР?",
                                          attachments=[get_boolean_keyboard().as_markup()])

    await context.update_data(is_member=(text == 'да'))
    await context.set_state(RegistrationStates.SURNAME)
    await event.message.answer("Введите вашу фамилию:")
