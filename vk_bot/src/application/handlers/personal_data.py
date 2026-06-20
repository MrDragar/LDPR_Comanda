from vkbottle.bot import BotLabeler
from vkbottle import GroupEventType, GroupTypes, DocMessagesUploader

from src.application.filters import CMDRule
from src.application.states import RegistrationStates
from vkbottle.dispatch import BuiltinStateDispenser

router = BotLabeler()


async def get_callback_user_state(
        state_dispenser: BuiltinStateDispenser,
        event: GroupTypes.MessageEvent
):
    state_peer = await state_dispenser.get(event.object.peer_id)
    if state_peer:
        return event.object.peer_id, state_peer

    state_user = await state_dispenser.get(event.object.user_id)
    if state_user:
        return event.object.user_id, state_user

    return event.object.peer_id, None


@router.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    CMDRule("pd_agree"),
)
async def handle_pd_agree(event: GroupTypes.MessageEvent,
                          state_dispenser: BuiltinStateDispenser):
    # Проверяем, находится ли пользователь на этапе ПД
    state_key, state_peer = await get_callback_user_state(state_dispenser, event)
    if not state_peer or state_peer.state != str(
            RegistrationStates.PERSONAL_DATA):
        return

    await state_dispenser.set(
        state_key,
        RegistrationStates.PHONE,
        **state_peer.payload
    )

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message="Введите ваш номер телефона (например, +79001234567):",
        random_id=0
    )

    # Отвечаем на callback (убираем "загрузку" на кнопке)
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


# --- ХЕНДЛЕР: ОТКАЗ (pd_disagree) ---
@router.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    CMDRule("pd_disagree"),
)
async def handle_pd_disagree(event: GroupTypes.MessageEvent,
                             state_dispenser: BuiltinStateDispenser):
    state_key, state_peer = await get_callback_user_state(state_dispenser, event)
    if not state_peer or state_peer.state != str(
            RegistrationStates.PERSONAL_DATA):
        return

    # Сбрасываем стейт
    await state_dispenser.delete(state_key)

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message="Для регистрации необходимо согласие. Напишите любое сообщение, чтобы начать заново.",
        random_id=0
    )

    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


# --- ХЕНДЛЕР: ЧТЕНИЕ ТЕКСТА (pd_read) ---
@router.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    CMDRule("pd_read"),
)
async def handle_pd_read(
        event: GroupTypes.MessageEvent,
        state_dispenser: BuiltinStateDispenser,
        doc_uploader: DocMessagesUploader
):
    _, state_peer = await get_callback_user_state(state_dispenser, event)
    if not state_peer or state_peer.state != str(
            RegistrationStates.PERSONAL_DATA):
        return
    doc = await doc_uploader.upload(
        file_source="docs/Согласие.docx",
        peer_id=event.object.peer_id,
    )
    await event.ctx_api.messages.send(
        user_id=event.object.user_id,
        peer_id=event.object.peer_id,
        attachment=doc,
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )
