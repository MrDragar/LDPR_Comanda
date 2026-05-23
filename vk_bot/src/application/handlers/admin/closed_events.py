import logging
from datetime import datetime
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Callback, Text, GroupEventType, GroupTypes
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import ClosedEventStates
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IClosedEventService, IUserService
from src.application.filters import check_role, CMDRule

logger = logging.getLogger(__name__)
router = BotLabeler()
PAGE_LIMIT = 5


def _admin_ce_kb(events, page, total, admin_region=None):
    kb = Keyboard(inline=True)
    for e in events:
        kb.add(Callback(f"📅 {e.title[:20]} ({e.region})", {"cmd": "view_ce_admin", "eid": e.id}))
        kb.row()
    kb.row()
    if total > 1:
        if page > 1: kb.add(Callback("⬅️", {"cmd": "prev_ce_admin"}))
        if page < total: kb.add(Callback("➡️", {"cmd": "next_ce_admin"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))
    return kb.get_json()


@router.message(text=["Создать закрытое мероприятие"])
async def start_create_ce(message: Message, user_svc: IUserService,
                          state_dispenser: BuiltinStateDispenser):
    if not await check_role(user_svc, message.from_id,
                            [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]):
        return await message.answer("Недостаточно прав")
    u = await user_svc.get_user(message.from_id, Sources.VK)
    await state_dispenser.set(message.from_id, ClosedEventStates.CREATE, step="title",
                              region=u.region if u.role == UserRole.COORDINATOR_RO else None)
    await message.answer("📝 Введите название мероприятия:")


@router.message(state=ClosedEventStates.CREATE)
async def create_ce_steps(message: Message, event_svc: IClosedEventService, user_svc: IUserService,
                          state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    step = state.payload.get("step")
    p = {k: v for k, v in state.payload.items() if k != 'step'}
    txt = message.text.strip()

    if step == "title":
        await state_dispenser.set(message.from_id, ClosedEventStates.CREATE, **p, title=txt,
                                  step="desc")
        return await message.answer("📄 Введите описание:")
    elif step == "desc":
        await state_dispenser.set(message.from_id, ClosedEventStates.CREATE, **p, desc=txt,
                                  step="loc")
        return await message.answer("📍 Введите место проведения:")
    elif step == "loc":
        await state_dispenser.set(message.from_id, ClosedEventStates.CREATE, **p, loc=txt,
                                  step="dt")
        return await message.answer("📅 Введите дату и время (формат: ДД.ММ.ГГГГ ЧЧ:ММ):")
    elif step == "dt":
        try:
            dt = datetime.strptime(txt, "%d.%m.%Y %H:%M")
            await state_dispenser.set(message.from_id, ClosedEventStates.CREATE, **p,
                                      date=dt.date(), time=dt.time(), step="region")
            if p.get("region"):  # Координатор
                await _finish_create_ce(message, event_svc, p["region"], dt.date(), dt.time(), p,
                                        state_dispenser)
                return
            return await message.answer("🌍 Введите регион проведения:")
        except ValueError:
            return await message.answer("⚠️ Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ")
    elif step == "region":
        await _finish_create_ce(message, event_svc, txt, state.payload.get("date"),
                                state.payload.get("time"), p, state_dispenser)


async def _finish_create_ce(msg, svc, region, date, time, payload, sd):
    try:
        ev = await svc.create_event(payload["title"], payload["desc"], payload["loc"], date, time,
                                    region)
        await sd.delete(msg.from_id)
        await msg.answer(f"✅ Мероприятие '{ev.title}' успешно создано!")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")


@router.message(text=["Список участников мероприятия"])
async def start_list_ce(message: Message, user_svc: IUserService, event_svc: IClosedEventService,
                        state_dispenser: BuiltinStateDispenser):
    u = await user_svc.get_user(message.from_id, Sources.VK)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await message.answer("Недостаточно прав")
    reg = u.region if u.role != UserRole.STAFF_CA else None
    evs, total = await event_svc.list_events(reg, 1)
    if not evs: return await message.answer("Нет активных мероприятий.")
    pages = (total + PAGE_LIMIT - 1) // PAGE_LIMIT
    await state_dispenser.set(message.from_id, ClosedEventStates.BROWSE_ADMIN, page=1, region=reg,
                              total=pages)
    await message.answer(f"📅 Выберите мероприятие (стр. 1/{pages}):",
                         keyboard=_admin_ce_kb(evs, 1, pages, reg))


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_ce_admin"))
async def view_ce_admin(event: GroupTypes.MessageEvent, event_svc: IClosedEventService,
                        user_svc: IUserService, state_dispenser: BuiltinStateDispenser):
    eid = event.object.payload["eid"]
    regs, total = await event_svc.list_participants(eid, 1)
    if not regs: return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                          message="Участников пока нет.",
                                                          random_id=0)
    pages = (total + PAGE_LIMIT - 1) // PAGE_LIMIT
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.PART_LIST, eid=eid, page=1,
                              total=pages)

    kb = Keyboard(inline=True)
    for r in regs:
        u = await user_svc.get_user(r.user_id, r.user_source)
        kb.add(Callback(f"{u.surname} {u.name}", {"cmd": "view_part", "uid": u.id}))
        kb.row()
    kb.row()
    if pages > 1: kb.add(Callback("Вперёд ➡️", {"cmd": "next_part"}))
    kb.add(Callback("🔙 Назад к мероприятиям", {"cmd": "back_ce_admin"}))

    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="👥 Список участников:",
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_part"))
async def view_part(event: GroupTypes.MessageEvent, user_svc: IUserService):
    u = await user_svc.get_user(event.object.payload["uid"], Sources.VK)
    txt = f"👤 {u.surname} {u.name} {u.patronymic or ''}\n📞 {u.phone_number}\n📧 {u.email}\n🌍 {u.region}, {u.city}"
    kb = Keyboard(inline=True).add(Callback("🔙 Назад", {"cmd": "back_parts"}))
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message=txt,
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id,
                                                           user_id=event.object.user_id,
                                                           peer_id=event.object.peer_id)
