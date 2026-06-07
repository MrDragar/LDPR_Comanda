from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback
from maxapi.context import MemoryContext

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates
from src.application.keyboards.region_keyboard import get_region_keyboard
from src.services.interfaces import IUserService

router = Router()


@router.message_created(RegistrationStates.REGION_BY_TEXT)
@router.message_created(RegistrationStates.REGION_BY_BUTTON)
async def search_region(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    regions = await user_service.get_similar_regions(event.message.body.text)
    if not regions:
        await event.message.answer("Регион не найден. Попробуйте ввести название иначе.")
        return
    await context.set_state(RegistrationStates.REGION_BY_BUTTON)
    await event.message.answer("Выберите ваш регион:", attachments=[get_region_keyboard(regions).as_markup()])


@router.message_callback(F.callback.payload.startswith("retry_reg:"))
async def retry_region_callback(event: MessageCallback, context: MemoryContext):
    if await context.get_state() not in [RegistrationStates.REGION_BY_TEXT, RegistrationStates.REGION_BY_BUTTON]:
        return
    await context.set_state(RegistrationStates.REGION_BY_TEXT)
    await event.message.answer("Введите название региона заново:")
    await event.callback.answer()


@router.message_callback(F.callback.payload.startswith("region:"))
async def select_region_callback(event: MessageCallback, context: MemoryContext, user_service: IUserService):
    if await context.get_state() != RegistrationStates.REGION_BY_BUTTON:
        return
    region_prefix = event.callback.payload.split(":", 1)[1]
    region_full = await user_service.get_region_by_prefix(region_prefix)
    await context.update_data(region=region_full)
    await context.set_state(RegistrationStates.NEWS_SUBSCRIPTION)
    await event.message.answer(
        f"Вы выбрали: {region_full}\n"
        "Хотели бы вы получать информацию о инициативах и мероприятиях ЛДПР? (Да/Нет)",
        attachments=[get_boolean_keyboard().as_markup()]
    )
    await event.callback.answer()
