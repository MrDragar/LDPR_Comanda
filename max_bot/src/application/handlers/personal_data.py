import logging

from maxapi import Router, Bot, F
from maxapi.types import MessageCallback, InputMedia
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates

router = Router()


@router.message_callback(F.callback.payload == "pd_agree")
async def handle_pd_agree(event: MessageCallback, context: MemoryContext):
    if await context.get_state() != RegistrationStates.PERSONAL_DATA:
        return
    await context.set_state(RegistrationStates.PHONE)
    await event.message.answer("Введите ваш номер телефона (например, +79001234567):")
    # await safe_ack(event)


@router.message_callback(F.callback.payload == "pd_disagree")
async def handle_pd_disagree(event: MessageCallback, context: MemoryContext):
    if await context.get_state() != RegistrationStates.PERSONAL_DATA:
        return
    await context.clear()
    await event.message.answer(
        "Для регистрации необходимо согласие. Напишите любое сообщение, чтобы начать заново.")
    # await safe_ack(event)


@router.message_callback(F.callback.payload == "pd_read")
async def handle_pd_read(event: MessageCallback, context: MemoryContext, bot: Bot):
    if await context.get_state() != RegistrationStates.PERSONAL_DATA:
        return
    try:
        media = InputMedia("docs/Согласие.docx")
        attachment = await bot.upload_media(media)
        await event.message.answer(attachments=[attachment])
    except Exception as e:
        await event.message.answer(f"Не удалось загрузить файл: {e}")

