from vkbottle.bot import BotLabeler, Message
from vkbottle import GroupEventType, GroupTypes
from vkbottle.dispatch.rules.base import PayloadRule, PayloadContainsRule
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.filters import CMDRule
from src.application.states import RegistrationStates
from src.application.keyboards.region_keyborad import get_region_keyboard
from src.services.interfaces import IUserService

router = BotLabeler()


@router.message(state=[RegistrationStates.REGION_BY_TEXT,
                       RegistrationStates.REGION_BY_BUTTON])
async def search_region(message: Message, user_service: IUserService,
                        state_dispenser: BuiltinStateDispenser):
    if not message.text: return

    regions = await user_service.get_similar_regions(message.text)
    if not regions:
        return "Регион не найден. Попробуйте ввести название иначе."

    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(message.from_id,
                              RegistrationStates.REGION_BY_BUTTON, **state.payload)
    await message.answer("Выберите ваш регион:",
                         keyboard=get_region_keyboard(regions))


@router.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    CMDRule("retry_reg"),
)
async def retry_region_callback(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    state_peer = await state_dispenser.get(event.object.peer_id)
    if not state_peer or state_peer.state not in [str(RegistrationStates.REGION_BY_TEXT), str(RegistrationStates.REGION_BY_BUTTON)]:
        return

    state = await state_dispenser.get(event.object.peer_id)
    await state_dispenser.set(event.object.peer_id, RegistrationStates.REGION_BY_TEXT, **state.payload)
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message="Введите название региона заново:",
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id
    )


# 3. Хендлер выбора конкретного региона
@router.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    CMDRule("region"),
)
async def select_region_callback(
        event: GroupTypes.MessageEvent,
        user_service: IUserService,
        state_dispenser: BuiltinStateDispenser
):
    payload = event.object.payload
    state_peer = await state_dispenser.get(event.object.peer_id)
    if not state_peer or state_peer.state != str(RegistrationStates.REGION_BY_BUTTON):
        return

    region_full = await user_service.get_region_by_prefix(payload["region"])
    current_payload = state_peer.payload or {}

    await state_dispenser.set(
        event.object.peer_id,
        RegistrationStates.CITY,
        **current_payload,
        region=region_full
    )

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=f"Вы выбрали: {region_full}\nТеперь укажите ваш город или населённый пункт:",
        random_id=0
    )

    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id
    )