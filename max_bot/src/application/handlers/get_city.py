from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard

router = Router()


@router.message_created(RegistrationStates.CITY)
async def get_city(event: MessageCreated, context: MemoryContext):
    if not event.message.body.text: return
    city = event.message.body.text.strip()
    if len(city) < 2:
        return await event.message.answer("Введите название вашего города или населённого пункта")

    await context.update_data(city=city)
    data = await context.get_data()

    if data.get('is_member'):
        await context.set_state(RegistrationStates.HOME_ADDRESS)
        await event.message.answer("Укажите свой домашний адрес:")
    else:
        await context.set_state(RegistrationStates.WISH_TO_JOIN)
        await event.message.answer("Хотите ли Вы присоединиться к команде ЛДПР?",
                                   attachments=[get_boolean_keyboard().as_markup()])
