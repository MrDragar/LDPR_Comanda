import logging
from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.handlers.finish_registration import finish_registration
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.services.interfaces import IUserService, IHeadlinerService
from aiogram import Bot as TgBot
from maxapi import Bot

router = Router()


@router.message_created(RegistrationStates.NEWS_SUBSCRIPTION)
async def get_news_sub(
        event: MessageCreated, context: MemoryContext, bot: Bot,
        user_service: IUserService, tg_bot: TgBot, log_chat: str,
        headliner_service: IHeadlinerService, group_link: str
):
    text = event.message.body.text.lower().strip() if event.message.body.text else ""
    if text not in ['да', 'нет']:
        return await event.message.answer("Хотели бы вы получать новости? (Да/Нет)",
                                          attachments=[get_boolean_keyboard().as_markup()])

    await context.update_data(news_subscription=(text == 'да'))
    await finish_registration(event, context, bot, user_service, tg_bot, log_chat, group_link,
                              headliner_service)