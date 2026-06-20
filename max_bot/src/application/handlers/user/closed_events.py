from maxapi import F, Router
from maxapi.types import CallbackButton, MessageCallback, MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities import Sources
from src.domain.entities.user import UserGrade
from src.services.interfaces import IClosedEventService, IUserService

router = Router()
PAGE_LIMIT = 5


def _uid(event) -> int:
    if hasattr(event, "from_user") and event.from_user:
        return event.from_user.user_id
    return event.callback.user.user_id


def _keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*[CallbackButton(text=text, payload=payload) for text, payload in row])
    return builder


async def _main_menu(event, user_service: IUserService, user_id: int):
    role = await user_service.get_user_role(user_id, Sources.MAX)
    await event.message.answer("Главное меню", attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(F.message.body.text == "Закрытые мероприятия")
async def open_closed_events(event: MessageCreated, user_service: IUserService,
                             closed_event_service: IClosedEventService):
    user = await user_service.get_user(_uid(event), Sources.MAX)
    if user.grade != UserGrade.RESERVE:
        await event.message.answer(
            "Для разблокировки этого раздела необходим ранг \"Кадровый резерв ЛДПР\". "
            "Для его достижения выполните 40 офлайн заданий.",
            attachments=[get_role_menu_keyboard(user.role).as_markup()]
        )
        return

    events, total_count = await closed_event_service.list_events(user.region, 1)
    if not events:
        await event.message.answer("В вашем регионе пока нет закрытых мероприятий.",
                                   attachments=[get_role_menu_keyboard(user.role).as_markup()])
        return
    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await render_events(event, events, 1, pages)


async def render_events(event, events, page: int, total_pages: int):
    rows = []
    for item in events:
        rows.append([(f"{item.title[:24]} ({item.date.strftime('%d.%m')})", f"max_ce_view:{item.id}")])
    nav = []
    if page > 1:
        nav.append(("Назад", f"max_ce_page:{page - 1}"))
    if page < total_pages:
        nav.append(("Вперёд", f"max_ce_page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("В меню", "max_ce_menu")])
    await event.message.answer(
        f"Актуальные мероприятия (стр. {page}/{total_pages}):",
        attachments=[_keyboard(rows).as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_ce_page:"))
async def event_page(event: MessageCallback, user_service: IUserService,
                     closed_event_service: IClosedEventService):
    page = int(event.callback.payload.split(":", 1)[1])
    user = await user_service.get_user(_uid(event), Sources.MAX)
    events, total_count = await closed_event_service.list_events(user.region, page)
    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await event.callback.answer()
    await render_events(event, events, page, pages)


@router.message_callback(F.callback.payload.startswith("max_ce_view:"))
async def view_event(event: MessageCallback, closed_event_service: IClosedEventService):
    event_id = int(event.callback.payload.split(":", 1)[1])
    item = await closed_event_service.get_event(event_id)
    await event.callback.answer()
    if not item:
        return await event.message.answer("Мероприятие не найдено.")
    keyboard = _keyboard([
        [("Записаться", f"max_ce_register:{item.id}")],
        [("К списку", "max_ce_back")]
    ])
    await event.message.answer(
        f"{item.title}\n"
        f"{item.description}\n"
        f"Место: {item.location}\n"
        f"Дата: {item.date.strftime('%d.%m.%Y')} в {item.time.strftime('%H:%M')}",
        attachments=[keyboard.as_markup()]
    )


@router.message_callback(F.callback.payload.startswith("max_ce_register:"))
async def register_event(event: MessageCallback, closed_event_service: IClosedEventService):
    event_id = int(event.callback.payload.split(":", 1)[1])
    await event.callback.answer()
    try:
        await closed_event_service.register(_uid(event), Sources.MAX, event_id)
        await event.message.answer("Вы успешно записались на мероприятие.")
    except Exception as e:
        await event.message.answer(str(e))


@router.message_callback(F.callback.payload == "max_ce_back")
async def back_events(event: MessageCallback, user_service: IUserService,
                      closed_event_service: IClosedEventService):
    user = await user_service.get_user(_uid(event), Sources.MAX)
    events, total_count = await closed_event_service.list_events(user.region, 1)
    await event.callback.answer()
    if not events:
        return await event.message.answer("В вашем регионе пока нет закрытых мероприятий.")
    pages = (total_count + PAGE_LIMIT - 1) // PAGE_LIMIT
    await render_events(event, events, 1, pages)


@router.message_callback(F.callback.payload == "max_ce_menu")
async def closed_events_menu(event: MessageCallback, user_service: IUserService):
    await event.callback.answer()
    await _main_menu(event, user_service, _uid(event))
