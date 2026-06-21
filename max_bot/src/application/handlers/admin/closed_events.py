import logging
from datetime import datetime
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.states import ClosedEventStates
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IClosedEventService, IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()
PAGE_LIMIT = 5


# ==================== СОЗДАНИЕ МЕРОПРИЯТИЯ ====================
@router.message_created(F.message.body.text == "Создать закрытое мероприятие")
async def start_create_ce(event: MessageCreated, context: MemoryContext,
                          user_service: IUserService):
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    if role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]:
        return await event.message.answer("Недостаточно прав.")

    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    await context.update_data(step="title",
                              region=u.region if role == UserRole.COORDINATOR_RO else None)
    await context.set_state(ClosedEventStates.CREATE)
    await event.message.answer("📝 Введите название мероприятия:",
                               attachments=[get_cancel_keyboard().as_markup()])


@router.message_created(ClosedEventStates.CREATE)
async def create_ce_steps(event: MessageCreated, context: MemoryContext,
                          closed_event_service: IClosedEventService, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        return await event.message.answer("Создание отменено.",
                                          attachments=[get_role_menu_keyboard(role).as_markup()])

    data = await context.get_data()
    step = data.get("step")
    txt = event.message.body.text.strip()

    try:
        if step == "title":
            await context.update_data(title=txt, step="desc")
            return await event.message.answer("📄 Введите описание:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "desc":
            await context.update_data(desc=txt, step="loc")
            return await event.message.answer("📍 Введите место проведения:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "loc":
            await context.update_data(loc=txt, step="dt")
            return await event.message.answer("📅 Введите дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "dt":
            dt = datetime.strptime(txt, "%d.%m.%Y %H:%M")
            await context.update_data(date=dt.date(), time=dt.time(), step="region")
            if data.get("region"):
                return await _finish_create_ce(event, context, closed_event_service, data["region"],
                                               user_service)
            return await event.message.answer("🌍 Введите регион проведения:",
                                              attachments=[get_cancel_keyboard().as_markup()])
        elif step == "region":
            similar = await user_service.get_similar_regions(txt.strip())
            if txt.strip() != similar[0]:
                hint = f"Регион не найден. Возможно: {', '.join(similar[:3])}" if similar else "Регион не найден."
                return await event.message.answer(f"⚠️ {hint}",
                                                  attachments=[get_cancel_keyboard().as_markup()])
            return await _finish_create_ce(event, context, closed_event_service, txt.strip(),
                                           user_service)
    except ValueError:
        return await event.message.answer("⚠️ Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ",
                                          attachments=[get_cancel_keyboard().as_markup()])
    except Exception as e:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        return await event.message.answer("❌ Ошибка.",
                                          attachments=[get_role_menu_keyboard(role).as_markup()])


async def _finish_create_ce(event: MessageCreated, context: MemoryContext, svc: IClosedEventService,
                            region: str, user_service: IUserService):
    data = await context.get_data()
    try:
        ev = await svc.create_event(data["title"], data["desc"], data["loc"], data["date"],
                                    data["time"], region)
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer(f"✅ Мероприятие '{ev.title}' создано!",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
    except Exception as e:
        await context.clear()
        await event.message.answer(f"❌ Ошибка: {e}")


# ==================== СПИСОК МЕРОПРИЯТИЙ (АДМИН) ====================
@router.message_created(F.message.body.text == "Список участников мероприятия")
async def start_list_ce(event: MessageCreated, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await event.message.answer("Недостаточно прав")

    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=1)
    if not evs:
        return await event.message.answer("Нет активных мероприятий.")

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(event, evs, 1, pages)


async def _render_admin_events(event, evs, page, total_pages):
    builder = InlineKeyboardBuilder()
    for e in evs:
        builder.row(
            CallbackButton(text=f"📅 {e.title[:30]} ({e.region})", payload=f"cea_view_{e.id}"))
    if page > 1: builder.row(CallbackButton(text="⬅️", payload=f"cea_prev_{page}"))
    if page < total_pages: builder.row(CallbackButton(text="➡️", payload=f"cea_next_{page}"))
    builder.row(CallbackButton(text="🔙 В меню", payload="cea_cancel"))

    text = f"📅 Выберите мероприятие (стр. {page}/{total_pages}):"
    await event.message.answer(text, attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("cea_next_"))
async def next_ce_admin(event: MessageCallback, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    await event.answer()
    page = int(event.callback.payload.split("_")[-1])
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(event, evs, page, total_pages)


@router.message_callback(F.callback.payload.startswith("cea_prev_"))
async def prev_ce_admin(event: MessageCallback, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    await event.answer()
    page = int(event.callback.payload.split("_")[-1])
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(event, evs, page, total_pages)


# ==================== ПРОСМОТР МЕРОПРИЯТИЯ -> УЧАСТНИКИ ====================
@router.message_callback(F.callback.payload.startswith("cea_view_"))
async def view_ce_admin(event: MessageCallback, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    await event.answer()
    eid = int(event.callback.payload.split("_")[-1])
    regs, total_count = await closed_event_service.list_participants(eid, page=1)
    if not regs:
        return await event.message.answer("Участников пока нет.")

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_participants(event, regs, eid, 1, pages, user_service)


async def _render_participants(event, regs, eid, page, total_pages, user_service: IUserService):
    builder = InlineKeyboardBuilder()
    for r in regs:
        try:
            p = await user_service.get_user(r.user_id, r.user_source)
            name_text = f"{p.surname} {p.name}"
        except Exception:
            name_text = f"Участник #{r.user_id}"

        # Передаем eid, page, user_id и source в payload
        builder.row(CallbackButton(text=name_text[:40],
                                   payload=f"cep_view_{eid}_{page}_{r.user_id}_{r.user_source.value}"))

    if page > 1: builder.row(CallbackButton(text="⬅️", payload=f"cep_prev_{eid}_{page}"))
    if page < total_pages: builder.row(CallbackButton(text="➡️", payload=f"cep_next_{eid}_{page}"))
    builder.row(CallbackButton(text="🔙 К мероприятиям", payload="cea_back"))

    text = f"👥 Участники (стр. {page}/{total_pages}):"
    await event.message.answer(text, attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("cep_next_"))
async def next_part(event: MessageCallback, user_service: IUserService,
                    closed_event_service: IClosedEventService):
    await event.answer()
    parts = event.callback.payload.split("_")
    eid, page = int(parts[2]), int(parts[3])
    regs, total_count = await closed_event_service.list_participants(eid, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_participants(event, regs, eid, page, total_pages, user_service)


@router.message_callback(F.callback.payload.startswith("cep_prev_"))
async def prev_part(event: MessageCallback, user_service: IUserService,
                    closed_event_service: IClosedEventService):
    await event.answer()
    parts = event.callback.payload.split("_")
    eid, page = int(parts[2]), int(parts[3])
    regs, total_count = await closed_event_service.list_participants(eid, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_participants(event, regs, eid, page, total_pages, user_service)


# ==================== ПРОСМОТР УЧАСТНИКА ====================
@router.message_callback(F.callback.payload.startswith("cep_view_"))
async def view_part(event: MessageCallback, user_service: IUserService):
    await event.answer()
    parts = event.callback.payload.split("_")
    eid = int(parts[2])
    page = int(parts[3])
    uid = int(parts[4])
    source = Sources(parts[5])

    u = await user_service.get_user(uid, source)
    text = (f"👤 {u.surname} {u.name} {u.patronymic or ''}\n"
            f"📞 {u.phone_number}\n"
            f"📧 {u.email or 'нет'}\n"
            f"🌍 {u.region}, {u.city or 'нет'}")

    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🔙 Назад к списку", payload=f"cep_back_{eid}_{page}"))
    await event.message.answer(text, attachments=[builder.as_markup()])


# ==================== ВОЗВРАТ К СПИСКУ УЧАСТНИКОВ ====================
@router.message_callback(F.callback.payload.startswith("cep_back_"))
async def back_parts(event: MessageCallback, user_service: IUserService,
                     closed_event_service: IClosedEventService):
    await event.answer()
    parts = event.callback.payload.split("_")
    eid = int(parts[2])
    page = int(parts[3])
    regs, total_count = await closed_event_service.list_participants(eid, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_participants(event, regs, eid, page, total_pages, user_service)


# ==================== НАВИГАЦИЯ НАЗАД К МЕРОПРИЯТИЯМ ====================
@router.message_callback(F.callback.payload == "cea_back")
async def back_ce_admin(event: MessageCallback, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    await event.answer()
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=1)
    if not evs:
        return await event.message.answer("Нет активных мероприятий.")

    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(event, evs, 1, total_pages)


@router.message_callback(F.callback.payload == "cea_cancel")
async def cancel_admin_ce(event: MessageCallback, context: MemoryContext,
                          user_service: IUserService):
    await event.answer()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Главное меню",
                               attachments=[get_role_menu_keyboard(role).as_markup()])
    await context.clear()
