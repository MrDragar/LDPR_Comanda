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
    """Клавиатура для списка мероприятий (админ)"""
    kb = Keyboard(inline=True)
    for e in events:
        kb.add(Callback(f"📅 {e.title[:30]} ({e.region})"[:40], {"cmd": "view_ce_admin",
                                                                "eid": e.id}))
        kb.row()

    kb.row()
    if total > 1:
        if page > 1:
            kb.add(Callback("⬅️", {"cmd": "prev_ce_admin"}))
        if page < total:
            kb.add(Callback("➡️", {"cmd": "next_ce_admin"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))
    return kb.get_json()


def _participants_kb(regs, page, total, event_id, user_service: IUserService = None):
    """Клавиатура для списка участников (генерируется с подгрузкой ФИО через сервис)"""
    kb = Keyboard(inline=True)
    for r in regs:
        # ✅ ИСПРАВЛЕНО: используем user_service вместо прямого API-вызова
        if user_service:
            try:
                participant = user_service.get_user(r.user_id, r.user_source)
                name_text = f"{participant.surname} {participant.name}"
            except:
                name_text = f"Участник #{r.user_id}"
        else:
            name_text = f"Участник #{r.user_id}"

        kb.add(Callback(name_text[:40],
                        {"cmd": "view_part", "uid": r.user_id, "source": r.user_source.value}))
        kb.row()

    kb.row()
    if total > 1:
        if page > 1:
            kb.add(Callback("⬅️", {"cmd": "prev_part", "eid": event_id}))
        if page < total:
            kb.add(Callback("➡️", {"cmd": "next_part", "eid": event_id}))
    kb.add(Callback("🔙 Назад к мероприятиям", {"cmd": "back_ce_admin"}))
    return kb.get_json()


# ==================== СОЗДАНИЕ МЕРОПРИЯТИЯ ====================
@router.message(text=["Создать закрытое мероприятие"])
async def start_create_ce(message: Message, user_service: IUserService,
                          state_dispenser: BuiltinStateDispenser):
    if not await check_role(user_service, message.from_id,
                            [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]):
        return await message.answer("Недостаточно прав")

    u = await user_service.get_user(message.from_id, Sources.VK)
    await state_dispenser.set(message.from_id, ClosedEventStates.CREATE, step="title",
                              region=u.region if u.role == UserRole.COORDINATOR_RO else None)
    await message.answer("📝 Введите название мероприятия:")


@router.message(state=ClosedEventStates.CREATE)
async def create_ce_steps(message: Message, closed_event_service: IClosedEventService,
                          user_service: IUserService,
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
                region_to_check = p["region"]
                similar = await user_service.get_similar_regions(region_to_check)
                if region_to_check not in similar or similar[0] != region_to_check:
                    hint = f"Регион не найден. Возможно, вы имели в виду: {', '.join(similar[:3])}" if similar else "Регион не найден."
                    return await message.answer(
                        f"⚠️ {hint}\nВведите название региона точно как в списке субъектов РФ:")

                await _finish_create_ce(message, closed_event_service, region_to_check,
                                        dt.date(), dt.time(), p, state_dispenser)
                return
            return await message.answer("🌍 Введите регион проведения:")
        except ValueError:
            return await message.answer("⚠️ Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ")
    elif step == "region":
        region_input = txt.strip()
        similar = await user_service.get_similar_regions(region_input)
        if region_input not in similar or similar[0] != region_input:
            hint = f"Регион не найден. Возможно, вы имели в виду: {', '.join(similar[:3])}" if similar else "Регион не найден."
            return await message.answer(
                f"⚠️ {hint}\nВведите название региона точно как в списке субъектов РФ:")

        await _finish_create_ce(message, closed_event_service, region_input,
                                state.payload.get("date"), state.payload.get("time"),
                                p, state_dispenser)


async def _finish_create_ce(msg, svc, region, date, time, payload, sd):
    try:
        ev = await svc.create_event(payload["title"], payload["desc"], payload["loc"],
                                    date, time, region)
        await sd.delete(msg.from_id)
        await msg.answer(f"✅ Мероприятие '{ev.title}' успешно создано!")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")


# ==================== СПИСОК УЧАСТНИКОВ (ВХОД) ====================
@router.message(text=["Список участников мероприятия"])
async def start_list_ce(message: Message, user_service: IUserService,
                        closed_event_service: IClosedEventService,
                        state_dispenser: BuiltinStateDispenser):
    u = await user_service.get_user(message.from_id, Sources.VK)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await message.answer("Недостаточно прав")

    # ✅ РЕГИОН БЕРЁМ ИЗ USER_SERVICE, НЕ ИЗ СТЕЙТА
    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=1)

    if not evs: return await message.answer("Нет активных мероприятий.")

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await state_dispenser.set(message.from_id, ClosedEventStates.BROWSE_ADMIN, page=1,
                              region=admin_region, total=pages)
    await message.answer(f"📅 Выберите мероприятие (стр. 1/{pages}):",
                         keyboard=_admin_ce_kb(evs, 1, pages, admin_region))


# ==================== ПАГИНАЦИЯ МЕРОПРИЯТИЙ ====================
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_ce_admin"))
async def next_ce_admin(event: GroupTypes.MessageEvent, user_service: IUserService,
                        closed_event_service: IClosedEventService,
                        state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state: return

    # ✅ РЕГИОН ВСЕГДА БЕРЁМ ИЗ USER_SERVICE
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None

    current_page = state.payload.get("page", 1)
    total_pages = state.payload.get("total", 1)
    new_page = min(current_page + 1, total_pages)

    evs, total_count = await closed_event_service.list_events(admin_region, page=new_page)
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.BROWSE_ADMIN,
                              page=new_page, region=admin_region, total=total_pages)

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=f"📅 Выберите мероприятие (стр. {new_page}/{total_pages}):",
        keyboard=_admin_ce_kb(evs, new_page, total_pages, admin_region),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_ce_admin"))
async def prev_ce_admin(event: GroupTypes.MessageEvent, user_service: IUserService,
                        closed_event_service: IClosedEventService,
                        state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state: return

    u = await user_service.get_user(event.object.user_id, Sources.VK)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None

    current_page = state.payload.get("page", 1)
    total_pages = state.payload.get("total", 1)
    new_page = max(1, current_page - 1)

    evs, total_count = await closed_event_service.list_events(admin_region, page=new_page)
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.BROWSE_ADMIN,
                              page=new_page, region=admin_region, total=total_pages)

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=f"📅 Выберите мероприятие (стр. {new_page}/{total_pages}):",
        keyboard=_admin_ce_kb(evs, new_page, total_pages, admin_region),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


# ==================== ПРОСМОТР МЕРОПРИЯТИЯ -> УЧАСТНИКИ ====================
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_ce_admin"))
async def view_ce_admin(event: GroupTypes.MessageEvent, user_service: IUserService,
                        closed_event_service: IClosedEventService,
                        state_dispenser: BuiltinStateDispenser):
    eid = event.object.payload["eid"]
    regs, total_count = await closed_event_service.list_participants(eid, page=1)

    if not regs:
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                 message="Участников пока нет.",
                                                 random_id=0)

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.PART_LIST,
                              eid=eid, page=1, total=pages)

    # ✅ Генерируем клавиатуру с подгрузкой ФИО через user_service
    kb = Keyboard(inline=True)
    for r in regs:
        participant = await user_service.get_user(r.user_id, r.user_source)
        kb.add(Callback(f"{participant.surname} {participant.name}",
                        {"cmd": "view_part", "uid": participant.id,
                         "source": participant.source.value}))
        kb.row()

    kb.row()
    if pages > 1:
        kb.add(Callback("➡️", {"cmd": "next_part", "eid": eid}))
    kb.add(Callback("🔙 Назад к мероприятиям", {"cmd": "back_ce_admin"}))

    await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                      message="👥 Список участников:",
                                      keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


# ==================== ПАГИНАЦИЯ УЧАСТНИКОВ ====================
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_part"))
async def next_part(event: GroupTypes.MessageEvent, user_service: IUserService,
                    closed_event_service: IClosedEventService,
                    state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state: return

    eid = state.payload.get("eid")
    if not eid: return

    current_page = state.payload.get("page", 1)
    total_pages = state.payload.get("total", 1)
    new_page = min(current_page + 1, total_pages)

    regs, total_count = await closed_event_service.list_participants(eid, page=new_page)
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.PART_LIST,
                              eid=eid, page=new_page, total=total_pages)

    kb = Keyboard(inline=True)
    for r in regs:
        participant = await user_service.get_user(r.user_id, r.user_source)
        kb.add(Callback(f"{participant.surname} {participant.name}",
                        {"cmd": "view_part", "uid": participant.id,
                         "source": participant.source.value}))
        kb.row()

    kb.row()
    if new_page > 1:
        kb.add(Callback("⬅️", {"cmd": "prev_part", "eid": eid}))
    if new_page < total_pages:
        kb.add(Callback("➡️", {"cmd": "next_part", "eid": eid}))
    kb.add(Callback("🔙 Назад к мероприятиям", {"cmd": "back_ce_admin"}))

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=f"👥 Участники (стр. {new_page}/{total_pages}):",
        keyboard=kb.get_json(),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_part"))
async def prev_part(event: GroupTypes.MessageEvent, user_service: IUserService,
                    closed_event_service: IClosedEventService,
                    state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state: return

    eid = state.payload.get("eid")
    if not eid: return

    current_page = state.payload.get("page", 1)
    total_pages = state.payload.get("total", 1)
    new_page = max(1, current_page - 1)

    regs, total_count = await closed_event_service.list_participants(eid, page=new_page)
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.PART_LIST,
                              eid=eid, page=new_page, total=total_pages)

    kb = Keyboard(inline=True)
    for r in regs:
        participant = await user_service.get_user(r.user_id, r.user_source)
        kb.add(Callback(f"{participant.surname} {participant.name}",
                        {"cmd": "view_part", "uid": participant.id,
                         "source": participant.source.value}))
        kb.row()

    kb.row()
    if new_page > 1:
        kb.add(Callback("⬅️", {"cmd": "prev_part", "eid": eid}))
    if new_page < total_pages:
        kb.add(Callback("➡️", {"cmd": "next_part", "eid": eid}))
    kb.add(Callback("🔙 Назад к мероприятиям", {"cmd": "back_ce_admin"}))

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=f"👥 Участники (стр. {new_page}/{total_pages}):",
        keyboard=kb.get_json(),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


# ==================== ПРОСМОТР УЧАСТНИКА ====================
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_part"))
async def view_part(event: GroupTypes.MessageEvent, user_service: IUserService):
    uid = event.object.payload["uid"]
    source = Sources(event.object.payload["source"])

    u = await user_service.get_user(uid, source)
    txt = (f"👤 {u.surname} {u.name} {u.patronymic or ''}\n"
           f"📞 {u.phone_number}\n"
           f"📧 {u.email}\n"
           f"🌍 {u.region}, {u.city}")

    kb = Keyboard(inline=True).add(Callback("🔙 Назад", {"cmd": "back_parts"}))
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=txt,
        keyboard=kb.get_json(),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


# ==================== НАВИГАЦИЯ НАЗАД ====================
@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_ce_admin"))
async def back_ce_admin(event: GroupTypes.MessageEvent, user_service: IUserService,
                        closed_event_service: IClosedEventService,
                        state_dispenser: BuiltinStateDispenser):
    """Возврат к списку мероприятий из просмотра участников"""
    # ✅ РЕГИОН БЕРЁМ ИЗ USER_SERVICE
    u = await user_service.get_user(event.object.user_id, Sources.VK)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None

    evs, total_count = await closed_event_service.list_events(admin_region, page=1)
    if not evs:
        return await event.ctx_api.messages.send(peer_id=event.object.peer_id,
                                                 message="Нет активных мероприятий.",
                                                 random_id=0)

    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await state_dispenser.set(event.object.peer_id, ClosedEventStates.BROWSE_ADMIN,
                              page=1, region=admin_region, total=total_pages)

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=f"📅 Выберите мероприятие (стр. 1/{total_pages}):",
        keyboard=_admin_ce_kb(evs, 1, total_pages, admin_region),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("back_parts"))
async def back_parts(event: GroupTypes.MessageEvent, user_service: IUserService,
                     closed_event_service: IClosedEventService,
                     state_dispenser: BuiltinStateDispenser):
    """Возврат к списку участников из просмотра конкретного участника"""
    state = await state_dispenser.get(event.object.peer_id)
    if not state:
        return await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="Ошибка: состояние не найдено",
            random_id=0
        )

    eid = state.payload.get("eid")
    if not eid:
        return await event.ctx_api.messages.send(
            peer_id=event.object.peer_id,
            message="Ошибка: мероприятие не найдено",
            random_id=0
        )

    page = state.payload.get("page", 1)
    total_pages = state.payload.get("total", 1)
    regs, total_count = await closed_event_service.list_participants(eid, page=page)

    # ✅ ИСПРАВЛЕНО: используем user_service вместо event.ctx_api.users.get
    kb = Keyboard(inline=True)
    for r in regs:
        participant = await user_service.get_user(r.user_id, r.user_source)
        kb.add(Callback(f"{participant.surname} {participant.name}",
                        {"cmd": "view_part", "uid": participant.id,
                         "source": participant.source.value}))
        kb.row()

    kb.row()
    if page > 1:
        kb.add(Callback("⬅️", {"cmd": "prev_part", "eid": eid}))
    if page < total_pages:
        kb.add(Callback("➡️", {"cmd": "next_part", "eid": eid}))
    kb.add(Callback("🔙 Назад к мероприятиям", {"cmd": "back_ce_admin"}))

    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message=f"👥 Участники (стр. {page}/{total_pages}):",
        keyboard=kb.get_json(),
        random_id=0
    )
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )