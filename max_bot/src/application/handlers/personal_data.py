import logging
from maxapi import Router, Bot, F
from maxapi.types import MessageCallback, InputMedia
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard

router = Router()


@router.message_callback(F.callback.payload == "pd_agree")
async def handle_pd_agree(event: MessageCallback, context: MemoryContext):
    if await context.get_state() != RegistrationStates.PERSONAL_DATA: return
    await context.set_state(RegistrationStates.MEMBERSHIP)
    await event.message.answer('Вы являетесь членом ЛДПР?', attachments=[get_boolean_keyboard().as_markup()])


@router.message_callback(F.callback.payload == "pd_disagree")
async def handle_pd_disagree(event: MessageCallback, context: MemoryContext):
    if await context.get_state() != RegistrationStates.PERSONAL_DATA: return
    await context.clear()
    await event.message.answer("Для регистрации необходимо согласие. Напишите любое сообщение, чтобы начать заново.")


@router.message_callback(F.callback.payload == "pd_read")
async def handle_pd_read(event: MessageCallback, context: MemoryContext, bot: Bot):
    if await context.get_state() != RegistrationStates.PERSONAL_DATA: return
    try:
        media = InputMedia("docs/Согласие.docx")
        attachment = await bot.upload_media(media)
        await event.message.answer(attachments=[attachment])
    except Exception as e:
        await event.message.answer(f"Не удалось загрузить файл: {e}")