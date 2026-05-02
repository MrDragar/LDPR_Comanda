from aiogram import Bot as TgBot
from vkbottle import PhotoMessageUploader
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.handlers.finish_registration import finish_registration
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService

router = BotLabeler()


@router.message(state=RegistrationStates.NEWS_SUBSCRIPTION)
async def get_news_sub(
        message: Message, user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
        photo_uploader: PhotoMessageUploader,
        log_chat: str,
        tg_bot: TgBot
):
    text = message.text.lower().strip() if message.text else ""
    if text not in ['да', 'нет']:
        await message.answer("Хотели бы вы получать новости? (Да/Нет)")
        return
    state = await state_dispenser.get(message.from_id)
    new_payload = {**state.payload, 'news_subscription': text == 'да'}
    await finish_registration(
        user_service=user_service,
        peer_id=message.peer_id,
        state_payload=new_payload,
        ctx_api=message.ctx_api,
        log_chat=log_chat,
        state_dispenser=state_dispenser,
        tg_bot=tg_bot,
        photo_uploader=photo_uploader
    )
    await state_dispenser.delete(message.from_id)

