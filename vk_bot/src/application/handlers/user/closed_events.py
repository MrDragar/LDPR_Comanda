import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, Text, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import ClosedEventStates
from src.domain.entities import Sources
from src.domain.entities.user import UserGrade
from src.services.interfaces import IClosedEventService, IUserService
from src.application.filters import CMDRule
from datetime import time as py_time

logger = logging.getLogger(__name__)
router = BotLabeler()
PAGE_LIMIT = 5


def _event_kb(events, page, total, prefix="user"):
    kb = Keyboard(inline=True)
    for e in events:
        kb.add(Callback(f"📅 {e.title[:20]} ({e.date.strftime('%d.%m')})", {"cmd": f"view_{prefix}", "eid": e.id}))
        kb.row()
    kb.row()
    if total > 1:
        if page > 1: kb.add(Callback("⬅️ Назад", {"cmd": f"prev_{prefix}"}))
        if page < total: kb.add(Callback("Вперёд ➡️", {"cmd": f"next_{prefix}"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))
    return kb.get_json()


@router.message(text=["Закрытые мероприятия"])
async def open_ce(message: Message, user_service: IUserService, event_service: IClosedEventService, state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    if u.grade != UserGrade.RESERVE:
        kb = Keyboard(one_time=True).add(Text("На главную"))
        return await message.answer("Для разблокировки этого раздела необходим ранг \"Кадровый резерв ЛДПР\". Для его достижения выполните 40 оффлайн заданий", keyboard=kb.get_json())

    evs, total = await event_service.list_events(u.region, 1)
    if not evs: return await message.answer("В вашем регионе пока нет закрытых мероприятий.")
    pages = (total + PAGE_LIMIT - 1) // PAGE_LIMIT
    await state_dispenser.set(message.from_id, ClosedEventStates.BROWSE_USER, page=1, region=u.region, total=pages)
    await message.answer(f"📍 Актуальные мероприятия в {u.region} (стр. 1/{pages}):", keyboard=_event_kb(evs, 1, pages))


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_user"))
async def next_user_ce(event: GroupTypes.MessageEvent, user_service: IUserService, event_service: IClosedEventService, state_dispenser: BuiltinStateDispenser):
    await _navigate_ce(event, 1, user_service, event_service, state_dispenser)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_user"))
async def prev_user_ce(event: GroupTypes.MessageEvent, user_service: IUserService, event_service: IClosedEventService, state_dispenser: BuiltinStateDispenser):
    await _navigate_ce(event, -1, user_service, event_service, state_dispenser)


async def _navigate_ce(event, delta, user_service, event_service, state_dispenser):
    state = await state_dispenser.get(event.object.peer_id)
    np = max(1, min(state.payload.get("page", 1) + delta, state.payload.get("total", 1)))
    evs, total = await event_service.list_events(state.payload.get("region"), np)
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.BROWSE_USER, page=np, **state.payload)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"📍 Мероприятия (стр. {np}/{state.payload['total']}):", keyboard=_event_kb(evs, np, state.payload['total']), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_user"))
async def view_user_ce(event: GroupTypes.MessageEvent, event_service: IClosedEventService, state_dispenser: BuiltinStateDispenser):
    eid = event.object.payload["eid"]
    ev = await event_service.get_event(eid)
    if not ev: 
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Мероприятие не найдено", random_id=0)
    kb = Keyboard(inline=True).add(Callback("✅ Записаться", {"cmd": "register_ce", "eid": eid})).row().add(Callback("🔙 Назад", {"cmd": "back_ce_user"}))
    txt = f"📌 {ev.title}\n📝 {ev.description}\n📍 {ev.location}\n📅 {ev.date.strftime('%d.%m.%Y')} в {ev.time.strftime('%H:%M')}"
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.BROWSE_USER, eid=eid)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=txt, keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("register_ce"))
async def register_ce(event: GroupTypes.MessageEvent, event_service: IClosedEventService, state_dispenser: BuiltinStateDispenser):
    try:
        await event_service.register(event.object.user_id, Sources.VK, event.object.payload["eid"])
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="✅ Вы успешно записались на мероприятие!", random_id=0)
    except Exception as e:
        await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=f"❌ {e}", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)
