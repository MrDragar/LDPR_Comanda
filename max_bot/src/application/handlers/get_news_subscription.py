from aiogram import Bot as TgBot
from maxapi import Router, Bot
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.handlers.finish_registration import finish_registration
from src.services.interfaces import IHeadlinerService, INotificationService, IUserService

router = Router()


@router.message_created(RegistrationStates.NEWS_SUBSCRIPTION)
async def get_news_sub(
        event: MessageCreated,
        context: MemoryContext,
        bot: Bot,
        user_service: IUserService,
        headliner_service: IHeadlinerService,
        notification_service: INotificationService,
        tg_bot: TgBot,
        log_chat: str
):
    text = event.message.body.text.lower().strip() if event.message.body.text else ""
    if text not in ['да', 'нет']:
        await event.message.answer("Хотели бы вы получать новости? (Да/Нет)")
        return

    await context.update_data(news_subscription=(text == 'да'))
    await finish_registration(
        event, context, bot, user_service, headliner_service, notification_service, tg_bot, log_chat
    )
