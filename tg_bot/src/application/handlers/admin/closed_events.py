import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.states import ClosedEventStates
from src.domain.entities.user import UserRole, Sources
from src.services.interfaces import IClosedEventService, IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)

PAGE_LIMIT = 5


# ==================== СОЗДАНИЕ МЕРОПРИЯТИЯ ====================
@router.message(F.text == "Создать закрытое мероприятие")
async def start_create_ce(message: types.Message, state: FSMContext, user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    if role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO]: return await message.answer(
        "Недостаточно прав.")
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    await state.update_data(step="title",
                            region=u.region if role == UserRole.COORDINATOR_RO else None)
    await state.set_state(ClosedEventStates.create)
    await message.answer("📝 Введите название мероприятия:", reply_markup=get_cancel_keyboard())


@router.message(ClosedEventStates.create)
async def create_ce_steps(message: types.Message, state: FSMContext,
                          closed_event_service: IClosedEventService, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]:
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        return await message.answer("Создание отменено.", reply_markup=get_role_menu_keyboard(role))

    data = await state.get_data()
    step = data.get("step")
    txt = message.text.strip()

    try:
        if step == "title":
            await state.update_data(title=txt, step="desc")
            return await message.answer("📄 Введите описание:", reply_markup=get_cancel_keyboard())
        elif step == "desc":
            await state.update_data(desc=txt, step="loc")
            return await message.answer("📍 Введите место проведения:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "loc":
            await state.update_data(loc=txt, step="dt")
            return await message.answer("📅 Введите дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):",
                                        reply_markup=get_cancel_keyboard())
        elif step == "dt":
            dt = datetime.strptime(txt, "%d.%m.%Y %H:%M")
            await state.update_data(date=dt.date(), time=dt.time(), step="region")
            if data.get("region"): return await _finish_create_ce(message, state,
                                                                  closed_event_service,
                                                                  data["region"], user_service)
            return await message.answer("🌍 Введите регион проведения:",
                                        reply_markup=get_cancel_keyboard())
        elif step == "region":
            similar = await user_service.get_similar_regions(txt.strip())
            if txt.strip() != similar[0]:
                hint = f"Регион не найден. Возможно: {', '.join(similar[:3])}" if similar else "Регион не найден."
                return await message.answer(f"⚠️ {hint}", reply_markup=get_cancel_keyboard())
            return await _finish_create_ce(message, state, closed_event_service, txt.strip(),
                                           user_service)
    except ValueError:
        return await message.answer("⚠️ Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ",
                                    reply_markup=get_cancel_keyboard())
    except Exception as e:
        await state.clear()
        return await message.answer("❌ Ошибка.", reply_markup=get_role_menu_keyboard(
            await user_service.get_user_role(message.from_user.id, Sources.TG)))


async def _finish_create_ce(message: types.Message, state: FSMContext, svc: IClosedEventService,
                            region: str, user_service: IUserService):
    data = await state.get_data()
    try:
        ev = await svc.create_event(data["title"], data["desc"], data["loc"], data["date"],
                                    data["time"], region)
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        await message.answer(f"✅ Мероприятие '{ev.title}' создано!",
                             reply_markup=get_role_menu_keyboard(role))
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ Ошибка: {e}")


# ==================== СПИСОК МЕРОПРИЯТИЙ (АДМИН) ====================
@router.message(F.text == "Список участников мероприятия")
async def start_list_ce(message: types.Message, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    if u.role not in [UserRole.STAFF_CA, UserRole.COORDINATOR_RO, UserRole.STAFF_RO]:
        return await message.answer("Недостаточно прав")

    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=1)

    if not evs:
        return await message.answer("Нет активных мероприятий.")

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(message, evs, 1, pages)


async def _render_admin_events(event: types.Message | types.CallbackQuery, evs, page, total_pages,
                               is_callback=False):
    builder = InlineKeyboardBuilder()
    for e in evs:
        builder.button(text=f"📅 {e.title[:30]} ({e.region})", callback_data=f"cea_view_{e.id}")
    builder.adjust(1)

    if page > 1: builder.button(text="⬅️", callback_data=f"cea_prev_{page}")
    if page < total_pages: builder.button(text="➡️", callback_data=f"cea_next_{page}")
    builder.button(text="🔙 В меню", callback_data="cea_cancel")

    text = f"📅 Выберите мероприятие (стр. {page}/{total_pages}):"
    if is_callback:
        await event.message.answer(text, reply_markup=builder.as_markup())
    else:
        await event.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("cea_next_"))
async def next_ce_admin(query: types.CallbackQuery, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    page = int(query.data.split("_")[-1])
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(query, evs, page, total_pages, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("cea_prev_"))
async def prev_ce_admin(query: types.CallbackQuery, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    page = int(query.data.split("_")[-1])
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(query, evs, page, total_pages, is_callback=True)
    await query.answer()


# ==================== ПРОСМОТР МЕРОПРИЯТИЯ -> УЧАСТНИКИ ====================
@router.callback_query(F.data.startswith("cea_view_"))
async def view_ce_admin(query: types.CallbackQuery, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    eid = int(query.data.split("_")[-1])
    regs, total_count = await closed_event_service.list_participants(eid, page=1)
    if not regs:
        await query.answer()
        return await query.message.answer("Участников пока нет.")

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_participants(query, regs, eid, 1, pages, user_service, is_callback=True)
    await query.answer()


async def _render_participants(event: types.Message | types.CallbackQuery, regs, eid, page,
                               total_pages, user_service: IUserService, is_callback=False):
    builder = InlineKeyboardBuilder()
    for r in regs:
        try:
            p = await user_service.get_user(r.user_id, r.user_source)
            name_text = f"{p.surname} {p.name}"
        except Exception:
            name_text = f"Участник #{r.user_id}"

        # Передаем eid и page в callback_data, чтобы корректно вернуться назад
        builder.button(text=name_text[:40], callback_data=f"cep_view_{eid}_{page}_{r.user_id}")
    builder.adjust(1)

    if page > 1: builder.button(text="⬅️", callback_data=f"cep_prev_{eid}_{page}")
    if page < total_pages: builder.button(text="➡️", callback_data=f"cep_next_{eid}_{page}")
    builder.button(text="🔙 К мероприятиям", callback_data="cea_back")

    text = f"👥 Участники (стр. {page}/{total_pages}):"
    if is_callback:
        await event.message.answer(text, reply_markup=builder.as_markup())
    else:
        await event.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("cep_next_"))
async def next_part(query: types.CallbackQuery, user_service: IUserService,
                    closed_event_service: IClosedEventService):
    parts = query.data.split("_")
    eid, page = int(parts[2]), int(parts[3])
    regs, total_count = await closed_event_service.list_participants(eid, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_participants(query, regs, eid, page, total_pages, user_service, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("cep_prev_"))
async def prev_part(query: types.CallbackQuery, user_service: IUserService,
                    closed_event_service: IClosedEventService):
    parts = query.data.split("_")
    eid, page = int(parts[2]), int(parts[3])
    regs, total_count = await closed_event_service.list_participants(eid, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_participants(query, regs, eid, page, total_pages, user_service, is_callback=True)
    await query.answer()


# ==================== ПРОСМОТР УЧАСТНИКА ====================
@router.callback_query(F.data.startswith("cep_view_"))
async def view_part(query: types.CallbackQuery, user_service: IUserService):
    parts = query.data.split("_")
    eid = int(parts[2])
    page = int(parts[3])
    uid = int(parts[4])

    u = await user_service.get_user(uid, Sources.TG)
    text = (f"👤 {u.surname} {u.name} {u.patronymic or ''}\n"
            f"📞 {u.phone_number}\n"
            f"📧 {u.email or 'нет'}\n"
            f"🌍 {u.region}, {u.city or 'нет'}")

    builder = InlineKeyboardBuilder()
    # Возвращаемся ровно к тому списку и странице, откуда зашли
    builder.button(text="🔙 Назад к списку", callback_data=f"cep_back_{eid}_{page}")

    await query.message.answer(text, reply_markup=builder.as_markup())
    await query.answer()


# ==================== ВОЗВРАТ К СПИСКУ УЧАСТНИКОВ (ИСПРАВЛЕНО) ====================
@router.callback_query(F.data.startswith("cep_back_"))
async def back_parts(query: types.CallbackQuery, user_service: IUserService,
                     closed_event_service: IClosedEventService):
    """Возврат к списку участников из просмотра конкретного участника"""
    parts = query.data.split("_")
    eid = int(parts[2])
    page = int(parts[3])

    regs, total_count = await closed_event_service.list_participants(eid, page=page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT

    await _render_participants(query, regs, eid, page, total_pages, user_service, is_callback=True)
    await query.answer()


# ==================== НАВИГАЦИЯ НАЗАД К МЕРОПРИЯТИЯМ ====================
@router.callback_query(F.data == "cea_back")
async def back_ce_admin(query: types.CallbackQuery, user_service: IUserService,
                        closed_event_service: IClosedEventService):
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    admin_region = u.region if u.role != UserRole.STAFF_CA else None
    evs, total_count = await closed_event_service.list_events(admin_region, page=1)
    if not evs:
        await query.answer()
        return await query.message.answer("Нет активных мероприятий.")
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_admin_events(query, evs, 1, total_pages, is_callback=True)
    await query.answer()


@router.callback_query(F.data == "cea_cancel")
async def cancel_admin_ce(query: types.CallbackQuery, state: FSMContext,
                          user_service: IUserService):
    role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    await query.message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
    await state.clear()
    await query.answer()