from vkbottle.bot import BotLabeler
from vkbottle import GroupEventType, GroupTypes, DocMessagesUploader

from src.application.filters import CMDRule
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.keyboards.personal_data_keyboard import \
    get_personal_data_keyboard
from src.application.states import RegistrationStates
from vkbottle.dispatch import BuiltinStateDispenser

router = BotLabeler()


@router.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    CMDRule("pd_agree"),
)
async def handle_pd_agree(event: GroupTypes.MessageEvent,
                          state_dispenser: BuiltinStateDispenser):
    # Проверяем, находится ли пользователь на этапе ПД
    state_peer = await state_dispenser.get(event.object.peer_id)
    if not state_peer or state_peer.state != str(
            RegistrationStates.PERSONAL_DATA):
        return

    # Переводим в следующий стейт
    await state_dispenser.set(event.object.peer_id,
                              RegistrationStates.MEMBERSHIP)

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message='Вы являетесь членом ЛДПР?',
        keyboard=get_boolean_keyboard(),
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
    state_peer = await state_dispenser.get(event.object.peer_id)
    if not state_peer or state_peer.state != str(
            RegistrationStates.PERSONAL_DATA):
        return

    # Сбрасываем стейт
    await state_dispenser.delete(event.object.peer_id)

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
    state_peer = await state_dispenser.get(event.object.peer_id)
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
