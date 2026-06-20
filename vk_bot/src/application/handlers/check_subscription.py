import logging

from aiogram import Bot as TgBot
from vkbottle import PhotoMessageUploader, API, Keyboard, Text
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from vkbottle_types import GroupTypes
from vkbottle_types.events import GroupEventType

from src.application.handlers.finish_registration import finish_registration
from src.application.keyboards.check_keyboard import get_check_keyboard
from src.application.states import RegistrationStates
from src.services.interfaces import IHeadlinerService, INotificationService, IUserService


logger = logging.getLogger(__name__)
router = BotLabeler()


@router.message(state=RegistrationStates.CHECK_SUBSCRIPTION)
async def check_sub(
        message: Message, user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
        photo_uploader: PhotoMessageUploader,
        log_chat: str,
        tg_bot: TgBot,
        group_id: int,
        service_token: str,
        notification_service: INotificationService,
        headliner_service: IHeadlinerService
):
    text = message.text.lower().strip() if message.text else ""
    if text == 'проверить' or text:
        try:
            api = API(token=service_token)
            await api.groups.approve_request(group_id=group_id, user_id=message.from_id)
        except:
            ...
        if not await message.ctx_api.groups.is_member(group_id=group_id, user_id=message.from_id):
            await message.answer(
                "Для завершения регистрации подпишитесь на сообщество Большой команды ЛДПР\n"
                f"https://vk.com/club{group_id}\n"
            )
            await message.answer('Нажмите кнопку "Проверить", когда отправите заявку на '
                                 'вступление в сообщество.\nБот автоматически её одобрит',
                                 keyboard=get_check_keyboard())
            return
    else:
        await message.answer(
            "Для завершения регистрации подпишитесь на сообщество Большой команды ЛДПР\n"
            f"https://vk.com/club{group_id}\n"
        )
        await message.answer('Напишите "Проверить", когда отправите заявку на '
                             'вступление в сообщество.\nБот автоматически её одобрит',
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
        photo_uploader=photo_uploader,
        notification_service=notification_service,
        headliner_service=headliner_service
    )
    await state_dispenser.delete(message.from_id)


@router.raw_event(GroupEventType.GROUP_JOIN, GroupTypes.GroupJoin)
async def handle_group_join(
        event: GroupTypes.GroupJoin,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser,
        photo_uploader: PhotoMessageUploader,
        log_chat: str,
        tg_bot: TgBot,
        group_id: int,
        service_token: str,
        notification_service: INotificationService,
        headliner_service: IHeadlinerService
):
    if event.object.join_type != "request":
        return

    user_id = event.object.user_id
    state = await state_dispenser.get(user_id)

    if state and state.state == str(RegistrationStates.CHECK_SUBSCRIPTION):
        try:
            api = API(token=service_token)
            await api.groups.approve_request(group_id=group_id, user_id=user_id)
            logger.info(f"Auto-approved group join request for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to approve request for {user_id}: {e}")
            return
        try:
            await finish_registration(
                user_service=user_service,
                peer_id=user_id,
                state_payload=state.payload,
                ctx_api=event.ctx_api,
                log_chat=log_chat,
                state_dispenser=state_dispenser,
                tg_bot=tg_bot,
                photo_uploader=photo_uploader,
                notification_service=notification_service,
                headliner_service=headliner_service
            )
            await state_dispenser.delete(user_id)
        except Exception as e:
            logger.error(f"Error finishing registration for user {user_id}: {e}")
    else:
        kb = Keyboard(one_time=True).add(Text("Начать"))
        try:
            await event.ctx_api.messages.send(
                user_id=user_id,
                message=(
                    "Для вступления в группу необходимо пройти регистрацию в боте.\n"
                    "Нажмите кнопку ниже, чтобы начать."
                ),
                keyboard=kb.get_json(),
                random_id=0
            )
        except Exception as e:
            logger.error(f"Failed to send registration prompt to user {user_id}: {e}")
