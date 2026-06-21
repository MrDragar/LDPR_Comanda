import logging
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.domain.entities import Sources
from src.domain.entities.user import UserGrade
from src.services.interfaces import IClosedEventService, IUserService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()
PAGE_LIMIT = 5


@router.message_created(F.message.body.text == "Закрытые мероприятия")
async def open_ce(event: MessageCreated, user_service: IUserService,
                  closed_event_service: IClosedEventService):
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    if u.grade != UserGrade.RESERVE:
        return await event.message.answer(
            "Для разблокировки этого раздела необходим ранг \"Кадровый резерв ЛДПР\". "
            "Для его достижения выполните 40 офлайн заданий.",
            attachments=[get_role_menu_keyboard(u.role).as_markup()]
        )

    evs, total_count = await closed_event_service.list_events(u.region, 1)
    if not evs:
        return await event.message.answer("В вашем регионе пока нет закрытых мероприятий.",
                                          attachments=[get_role_menu_keyboard(u.role).as_markup()])

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(event, evs, 1, pages)


async def _render_user_events(event, evs, page, total_pages):
    builder = InlineKeyboardBuilder()
    for e in evs:
        builder.row(CallbackButton(text=f"📅 {e.title[:20]} ({e.date.strftime('%d.%m')})",
                                   payload=f"ceu_view_{e.id}"))
    if page > 1: builder.row(CallbackButton(text="⬅️ Назад", payload=f"ceu_prev_{page}"))
    if page < total_pages: builder.row(CallbackButton(text="Вперёд ➡️", payload=f"ceu_next_{page}"))
    builder.row(CallbackButton(text="🔙 В меню", payload="ceu_cancel"))

    text = f"📍 Актуальные мероприятия (стр. {page}/{total_pages}):"
    await event.message.answer(text, attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("ceu_next_"))
async def next_user_ce(event: MessageCallback, user_service: IUserService,
                       closed_event_service: IClosedEventService):
    await event.answer()
    page = int(event.callback.payload.split("_")[-1])
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    evs, total_count = await closed_event_service.list_events(u.region, page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(event, evs, page, total_pages)


@router.message_callback(F.callback.payload.startswith("ceu_prev_"))
async def prev_user_ce(event: MessageCallback, user_service: IUserService,
                       closed_event_service: IClosedEventService):
    await event.answer()
    page = int(event.callback.payload.split("_")[-1])
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    evs, total_count = await closed_event_service.list_events(u.region, page)
    total_pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(event, evs, page, total_pages)


@router.message_callback(F.callback.payload.startswith("ceu_view_"))
async def view_user_ce(event: MessageCallback, closed_event_service: IClosedEventService):
    await event.answer()
    eid = int(event.callback.payload.split("_")[-1])
    ev = await closed_event_service.get_event(eid)
    if not ev:
        return await event.message.answer("Мероприятие не найдено")

    txt = (f"📌 {ev.title}\n"
           f"📝 {ev.description}\n"
           f"📍 {ev.location}\n"
           f"📅 {ev.date.strftime('%d.%m.%Y')} в {ev.time.strftime('%H:%M')}")

    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="✅ Записаться", payload=f"ceu_reg_{eid}"))
    builder.row(CallbackButton(text="🔙 Назад", payload="ceu_back"))
    await event.message.answer(txt, attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("ceu_reg_"))
async def register_ce(event: MessageCallback, closed_event_service: IClosedEventService):
    await event.answer()
    eid = int(event.callback.payload.split("_")[-1])
    try:
        await closed_event_service.register(event.from_user.user_id, Sources.MAX, eid)
        await event.message.answer("✅ Вы успешно записались на мероприятие!")
    except Exception as e:
        await event.message.answer(f"❌ {e}")


@router.message_callback(F.callback.payload == "ceu_back")
async def back_to_user_ce(event: MessageCallback, user_service: IUserService,
                          closed_event_service: IClosedEventService):
    await event.answer()
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    evs, total_count = await closed_event_service.list_events(u.region, page=1)
    if not evs:
        return await event.message.answer("В вашем регионе пока нет закрытых мероприятий.")

    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await _render_user_events(event, evs, 1, pages)


@router.message_callback(F.callback.payload == "ceu_cancel")
async def cancel_user_ce(event: MessageCallback, user_service: IUserService):
    await event.answer()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Главное меню",
                               attachments=[get_role_menu_keyboard(role).as_markup()])
