import logging

import aiohttp
from vkbottle import Keyboard, Callback, GroupEventType, GroupTypes
from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.filters import check_role, CMDRule
from src.application.states import AdminShopStates
from src.domain.entities.user import UserRole
from src.domain.exceptions import DomainError
from src.services.interfaces import IProductService, IUserService

logger = logging.getLogger(__name__)
router = BotLabeler()


async def download_file_bytes(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
            raise DomainError("Не удалось скачать файл")

def _hide_kb(prods, page, total):
    kb = Keyboard(inline=True)
    for p in prods:
        kb.add(Callback(f"- {p.name} (ост: {p.quantity})", {"cmd": "view_hide", "pid": p.id}))
        kb.row()
    kb.row()
    if total > 1:
        if page > 1: kb.add(Callback("⬅️", {"cmd": "prev_hide"}))
        if page < total: kb.add(Callback("➡️", {"cmd": "next_hide"}))
    kb.add(Callback("🔙 В меню", {"cmd": "back_to_menu"}))
    return kb.get_json()


@router.message(text=["Добавить товар"])
async def start_add(message: Message, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    if not await check_role(user_service, message.from_id, [UserRole.STAFF_CA]):
        return await message.answer("Недостаточно прав")
    await state_dispenser.set(message.from_id, AdminShopStates.ADD_NAME)
    await message.answer("📝 Введите название товара:")


@router.message(state=AdminShopStates.ADD_NAME)
async def add_desc(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    await state_dispenser.set(message.from_id, AdminShopStates.ADD_DESC, **state.payload, name=message.text.strip())
    await message.answer("📄 Введите описание товара:")


@router.message(state=AdminShopStates.ADD_DESC)
async def add_qty(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    await state_dispenser.set(message.from_id, AdminShopStates.ADD_QTY, **state.payload, desc=message.text.strip())
    await message.answer("📦 Введите количество:")


@router.message(state=AdminShopStates.ADD_QTY)
async def add_price(message: Message, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    try:
        qty = int(message.text.strip())
        if qty <= 0: raise ValueError
        await state_dispenser.set(message.from_id, AdminShopStates.ADD_PRICE, **state.payload, qty=qty)
        await message.answer("💰 Введите цену в баллах:")
    except ValueError:
        return await message.answer("⚠️ Введите корректное число > 0")


@router.message(state=AdminShopStates.ADD_PRICE)
async def finish_add(message: Message, prod_svc: IProductService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(message.from_id)
    if not state: return
    try:
        price = int(message.text.strip())
        if price <= 0: raise ValueError

        # Сохраняем цену в стейт перед запросом файла
        await state_dispenser.set(message.from_id, AdminShopStates.ADD_PHOTO, **state.payload, price=price)
        await message.answer("🖼 Отправьте фотографию товара (документом):")
    except ValueError:
        return await message.answer("⚠️ Введите корректное число > 0")


@router.message(state=AdminShopStates.ADD_PHOTO)
async def upload_photo(message: Message, prod_svc: IProductService, state_dispenser: BuiltinStateDispenser):
    if not message.docs:
        return await message.answer("⚠️ Пожалуйста, отправьте файл документом.")

    state = await state_dispenser.get(message.from_id)
    if not state: return

    p = state.payload
    try:
        doc_url = message.docs[0].url
        file_bytes = await download_file_bytes(doc_url)

        # Вызов сервиса, который сам загрузит фото в S3 и сохранит в БД
        await prod_svc.create_product(
            name=p["name"],
            desc=p["desc"],
            price=p["price"],
            qty=p["qty"],
            photo_bytes=file_bytes
        )

        await state_dispenser.delete(message.from_id)
        await message.answer("✅ Товар успешно добавлен в магазин!")
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.error(f"Critical error in shop creation: {e}")
        await message.answer("❌ Произошла ошибка при создании товара.")


@router.message(text=["Скрыть товар"])
async def start_hide(message: Message, prod_svc: IProductService, user_service: IUserService, state_dispenser: BuiltinStateDispenser):
    if not await check_role(user_service, message.from_id, [UserRole.STAFF_CA]): return await message.answer("Недостаточно прав")
    prods, total = await prod_svc.list_products(1)
    if not prods: return await message.answer("Нет активных товаров.")
    await state_dispenser.set(message.from_id, AdminShopStates.HIDE_BROWSE, page=1, total=total)
    await message.answer("📦 Выберите товар для скрытия:", keyboard=_hide_kb(prods, 1, total))


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("next_hide"))
async def next_hide(event: GroupTypes.MessageEvent, prod_svc: IProductService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    np = state.payload.get("page", 1) + 1
    prods, total = await prod_svc.list_products(np)
    await state_dispenser.set(event.object.peer_id, AdminShopStates.HIDE_BROWSE, page=np, total=total)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="📦 Выберите товар для скрытия:", keyboard=_hide_kb(prods, np, total), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("prev_hide"))
async def prev_hide(event: GroupTypes.MessageEvent, prod_svc: IProductService, state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    np = max(1, state.payload.get("page", 1) - 1)
    prods, total = await prod_svc.list_products(np)
    await state_dispenser.set(event.object.peer_id, AdminShopStates.HIDE_BROWSE, page=np, total=total)
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="📦 Выберите товар для скрытия:", keyboard=_hide_kb(prods, np, total), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("view_hide"))
async def confirm_hide(event: GroupTypes.MessageEvent, state_dispenser: BuiltinStateDispenser):
    pid = event.object.payload["pid"]
    kb = Keyboard(inline=True).add(Callback("✅ Скрыть товар", {"cmd": "execute_hide", "pid": pid})).row().add(Callback("⬅️ Назад", {"cmd": "back_hide"}))
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="Вы уверены, что хотите скрыть этот товар?", keyboard=kb.get_json(), random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent, CMDRule("execute_hide"))
async def execute_hide(event: GroupTypes.MessageEvent, prod_svc: IProductService, state_dispenser: BuiltinStateDispenser):
    await prod_svc.hide_product(event.object.payload["pid"])
    await event.ctx_api.messages.send(peer_id=event.object.peer_id, message="✅ Товар успешно скрыт.", random_id=0)
    await event.ctx_api.messages.send_message_event_answer(event_id=event.object.event_id, user_id=event.object.user_id, peer_id=event.object.peer_id)
    await start_hide(event, prod_svc, None, state_dispenser)
