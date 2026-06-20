import logging
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard

router = Router()


@router.message_created(RegistrationStates.WISH_TO_JOIN)
async def get_wish_to_join(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text.lower().strip() if event.message.body.text else ""
    if text not in ['да', 'нет']:
        return await event.message.answer("Хотите ли Вы присоединиться к команде ЛДПР?",
                                          attachments=[get_boolean_keyboard().as_markup()])

    await context.update_data(wish_to_join=(text == 'да'))

    if text == 'нет':
        await context.set_state(RegistrationStates.NEWS_SUBSCRIPTION)
        await event.message.answer(
            "Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР?",
            attachments=[get_boolean_keyboard().as_markup()])
    else:
        await context.set_state(RegistrationStates.HOME_ADDRESS)
        await event.message.answer(
            "Для возможности направления документов укажите свой домашний адрес:")
