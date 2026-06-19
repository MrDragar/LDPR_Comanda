import logging
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.application.states import ClosedEventStates
from src.domain.entities import Sources
from src.domain.entities.user import UserGrade
from src.services.interfaces import IClosedEventService, IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)

PAGE_LIMIT = 5


@router.message(F.text == "Закрытые мероприятия")
async def open_ce(message: types.Message, user_service: IUserService,
                  closed_event_service: IClosedEventService):
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    if u.grade != UserGrade.RESERVE:
        return await message.answer(
            "Для разблокировки этого раздела необходим ранг \"Кадровый резерв ЛДПР\". "
            "Для его достижения выполните 40 офлайн заданий.",
            reply_markup=get_role_menu_keyboard(u.role)
        )

    evs, total_count = await closed_event_service.list_events(u.region, 1)
    if not evs:
        return await message.answer("В вашем регионе пока нет закрытых мероприятий.",
                                    reply_markup=get_role_menu_keyboard(u.role))

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(message, evs, 1, pages)


async def _render_user_events(event: types.Message | types.CallbackQuery, evs, page, total_pages,
                              is_callback=False):
    builder = InlineKeyboardBuilder()
    for e in evs:
        builder.button(text=f"📅 {e.title[:20]} ({e.date.strftime('%d.%m')})",
                       callback_data=f"ceu_view_{e.id}")
    builder.adjust(1)

    if page > 1: builder.button(text="⬅️ Назад", callback_data=f"ceu_prev_{page}")
    if page < total_pages: builder.button(text="Вперёд ➡️", callback_data=f"ceu_next_{page}")
    builder.button(text="🔙 В меню", callback_data="ceu_cancel")

    text = f"📍 Актуальные мероприятия (стр. {page}/{total_pages}):"
    if is_callback:
        await event.message.answer(text, reply_markup=builder.as_markup())
    else:
        await event.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("ceu_next_"))
async def next_user_ce(query: types.CallbackQuery, user_service: IUserService,
                       closed_event_service: IClosedEventService):
    page = int(query.data.split("_")[-1])
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    evs, total_count = await closed_event_service.list_events(u.region, page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(query, evs, page, total_pages, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("ceu_prev_"))
async def prev_user_ce(query: types.CallbackQuery, user_service: IUserService,
                       closed_event_service: IClosedEventService):
    page = int(query.data.split("_")[-1])
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    evs, total_count = await closed_event_service.list_events(u.region, page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(query, evs, page, total_pages, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("ceu_view_"))
async def view_user_ce(query: types.CallbackQuery, closed_event_service: IClosedEventService):
    eid = int(query.data.split("_")[-1])
    ev = await closed_event_service.get_event(eid)
    if not ev:
        return await query.answer("Мероприятие не найдено", show_alert=True)

    txt = (f"📌 {ev.title}\n"
           f"📝 {ev.description}\n"
           f"📍 {ev.location}\n"
           f"📅 {ev.date.strftime('%d.%m.%Y')} в {ev.time.strftime('%H:%M')}")

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Записаться", callback_data=f"ceu_reg_{eid}")
    builder.button(text="🔙 Назад", callback_data="ceu_back")
    builder.adjust(1)

    await query.message.answer(txt, reply_markup=builder.as_markup())
    await query.answer()


@router.callback_query(F.data.startswith("ceu_reg_"))
async def register_ce(query: types.CallbackQuery, closed_event_service: IClosedEventService):
    eid = int(query.data.split("_")[-1])
    try:
        await closed_event_service.register(query.from_user.id, Sources.TG, eid)
        await query.message.answer("✅ Вы успешно записались на мероприятие!")
    except Exception as e:
        await query.message.answer(f"❌ {e}")
    await query.answer()


@router.callback_query(F.data == "ceu_back")
async def back_to_user_ce(query: types.CallbackQuery, user_service: IUserService,
                          closed_event_service: IClosedEventService):
    u = await user_service.get_user(query.from_user.id, Sources.TG)
    evs, total_count = await closed_event_service.list_events(u.region, page=1)
    if not evs:
        return await query.message.answer("В вашем регионе пока нет закрытых мероприятий.")
    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(query, evs, 1, pages, is_callback=True)
    await query.answer()


@router.callback_query(F.data == "ceu_cancel")
async def cancel_user_ce(query: types.CallbackQuery, user_service: IUserService):
    role = await user_service.get_user_role(query.from_user.id, Sources.TG)
    await query.message.answer("Главное меню", reply_markup=get_role_menu_keyboard(role))
    await query.answer()
