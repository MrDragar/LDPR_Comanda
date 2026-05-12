from aiogram import Bot as TgBot
from vkbottle import PhotoMessageUploader
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.handlers.finish_registration import finish_registration
from src.application.keyboards.check_keyboard import get_check_keyboard
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService

router = BotLabeler()


@router.message(state=RegistrationStates.CHECK_SUBSCRIPTION)
async def check_sub(
        message: Message, user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
        photo_uploader: PhotoMessageUploader,
        log_chat: str,
        tg_bot: TgBot,
        group_id: int
):
    text = message.text.lower().strip() if message.text else ""
    if text == 'проверить':
        if not await message.ctx_api.groups.is_member(group_id=group_id, user_id=message.from_id):
            await message.answer(
                "Для работы бота вам необходимо подписаться на наше сообщество "
                f"https://vk.com/club{group_id}\n"
            )
            await message.answer('Нажмите кнопку "ПРОВЕРИТЬ", когда подпишитесь на сообщество',
                                 keyboard=get_check_keyboard())
            return

    else:
        await message.answer(
            "Для работы бота вам необходимо подписаться на наше сообщество "
            f"https://vk.com/club{group_id}\n"
        )
        await message.answer('Нажмите кнопку "ПРОВЕРИТЬ", когда подпишитесь на сообщество',
                             keyboard=get_check_keyboard())
        return 
    state = await state_dispenser.get(message.from_id)
    await finish_registration(
        user_service=user_service,
        peer_id=message.peer_id,
        state_payload=state.payload,
        ctx_api=message.ctx_api,
        log_chat=log_chat,
        state_dispenser=state_dispenser,
        tg_bot=tg_bot,
        photo_uploader=photo_uploader
    )
    await state_dispenser.delete(message.from_id)
