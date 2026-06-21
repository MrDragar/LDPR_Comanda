import logging
import aiohttp
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageCallback, CallbackButton
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.application.states import AdminShopStates
from src.domain.entities.user import UserRole, Sources
from src.domain.exceptions import DomainError
from src.services.interfaces import IProductService, IUserService
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def download_image(url: str) -> bytes | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        logger.error(f"Error downloading image {url}: {e}")
    return None


async def _cancel_shop(event, context: MemoryContext, user_service: IUserService):
    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Добавление товара отменено.",
                               attachments=[get_role_menu_keyboard(role).as_markup()])


@router.message_created(F.message.body.text == "Добавить товар")
async def start_add(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    if role != UserRole.STAFF_CA: return await event.message.answer("Недостаточно прав")
    await event.message.answer("📝 Введите название товара:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(AdminShopStates.ADD_NAME)


@router.message_created(AdminShopStates.ADD_NAME)
async def add_desc(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена",
                                                               "На главную"]: return await _cancel_shop(
        event, context, user_service)
    await context.update_data(name=event.message.body.text.strip())
    await event.message.answer("📄 Введите описание товара:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(AdminShopStates.ADD_DESC)


@router.message_created(AdminShopStates.ADD_DESC)
async def add_qty(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена",
                                                               "На главную"]: return await _cancel_shop(
        event, context, user_service)
    await context.update_data(desc=event.message.body.text.strip())
    await event.message.answer("📦 Введите количество:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(AdminShopStates.ADD_QTY)


@router.message_created(AdminShopStates.ADD_QTY)
async def add_price(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена",
                                                               "На главную"]: return await _cancel_shop(
        event, context, user_service)
    try:
        qty = int(event.message.body.text.strip())
        if qty <= 0: raise ValueError
        await context.update_data(qty=qty)
        await event.message.answer("💰 Введите цену в баллах:",
                                   attachments=[get_cancel_keyboard().as_markup()])
        await context.set_state(AdminShopStates.ADD_PRICE)
    except ValueError:
        await event.message.answer("⚠️ Введите корректное число > 0",
                                   attachments=[get_cancel_keyboard().as_markup()])


@router.message_created(AdminShopStates.ADD_PRICE)
async def add_photo_prompt(event: MessageCreated, context: MemoryContext,
                           user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена",
                                                               "На главную"]: return await _cancel_shop(
        event, context, user_service)
    try:
        price = int(event.message.body.text.strip())
        if price <= 0: raise ValueError
        await context.update_data(price=price)
        await event.message.answer("🖼 Отправьте фотографию товара (или URL изображения):",
                                   attachments=[get_cancel_keyboard().as_markup()])
        await context.set_state(AdminShopStates.ADD_PHOTO)
    except ValueError:
        await event.message.answer("⚠️ Введите корректное число > 0",
                                   attachments=[get_cancel_keyboard().as_markup()])


@router.message_created(AdminShopStates.ADD_PHOTO)
async def upload_photo(event: MessageCreated, context: MemoryContext,
                       product_service: IProductService, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        return await _cancel_shop(event, context, user_service)

    data = await context.get_data()
    photo_bytes = None

    # Пытаемся получить фото из вложений MAX API
    if hasattr(event.message, 'attachments') and event.message.attachments:
        att = event.message.attachments[0]
        url = getattr(att, 'url', None) or getattr(getattr(att, 'payload', None), 'url', None)
        if url:
            photo_bytes = await download_image(url)

    # Если вложений нет, но есть текст (URL)
    if not photo_bytes and event.message.body.text and event.message.body.text.startswith("http"):
        photo_bytes = await download_image(event.message.body.text.strip())

    if not photo_bytes:
        return await event.message.answer(
            "⚠️ Не удалось получить изображение. Отправьте фото или корректный URL.",
            attachments=[get_cancel_keyboard().as_markup()])

    try:
        await product_service.create_product(
            name=data["name"], desc=data["desc"],
            price=data["price"], qty=data["qty"],
            photo_bytes=photo_bytes
        )
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("✅ Товар успешно добавлен в магазин!",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
    except DomainError as e:
        await event.message.answer(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.error(f"Critical error in shop creation: {e}")
        await event.message.answer("❌ Произошла ошибка при создании товара.")


async def _render_hide_list(event, prods, page, total):
    builder = InlineKeyboardBuilder()
    for p in prods:
        builder.row(
            CallbackButton(text=f"- {p.name} (ост: {p.quantity})", payload=f"hide_view_{p.id}"))
    if total > 1:
        if page > 1: builder.row(CallbackButton(text="⬅️", payload=f"hide_prev_{page}"))
        if page < total: builder.row(CallbackButton(text="➡️", payload=f"hide_next_{page}"))
    text = "📦 Выберите товар для скрытия:"
    await event.message.answer(text, attachments=[builder.as_markup()])


@router.message_created(F.message.body.text == "Скрыть товар")
async def start_hide(event: MessageCreated, product_service: IProductService,
                     user_service: IUserService, context: MemoryContext):
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    if role != UserRole.STAFF_CA:
        return await event.message.answer("Недостаточно прав")
    prods, total = await product_service.list_products(1)
    if not prods:
        return await event.message.answer("Нет активных товаров.")
    await context.update_data(page=1, total=total)
    await context.set_state(AdminShopStates.HIDE_BROWSE)
    await _render_hide_list(event, prods, 1, total)


@router.message_callback(F.callback.payload.startswith("hide_next_"))
async def next_hide(event: MessageCallback, context: MemoryContext,
                    product_service: IProductService):
    page = int(event.callback.payload.split("_")[-1])
    prods, total = await product_service.list_products(page)
    await context.update_data(page=page, total=total)
    await _render_hide_list(event, prods, page, total)


@router.message_callback(F.callback.payload.startswith("hide_prev_"))
async def prev_hide(event: MessageCallback, context: MemoryContext,
                    product_service: IProductService):
    page = int(event.callback.payload.split("_")[-1])
    prods, total = await product_service.list_products(page)
    await context.update_data(page=page, total=total)
    await _render_hide_list(event, prods, page, total)


@router.message_callback(F.callback.payload.startswith("hide_view_"))
async def confirm_hide(event: MessageCallback):
    pid = int(event.callback.payload.split("_")[-1])
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="✅ Скрыть товар", payload=f"hide_execute_{pid}"))
    builder.row(CallbackButton(text="⬅️ Назад", payload="hide_back_list"))
    await event.message.answer("Вы уверены, что хотите скрыть этот товар?",
                               attachments=[builder.as_markup()])


@router.message_callback(F.callback.payload.startswith("hide_execute_"))
async def execute_hide(event: MessageCallback, product_service: IProductService,
                       context: MemoryContext):
    pid = int(event.callback.payload.split("_")[-1])
    await product_service.hide_product(pid)
    await event.message.answer("✅ Товар успешно скрыт.")
    prods, total = await product_service.list_products(1)
    await context.update_data(page=1, total=total)
    await _render_hide_list(event, prods, 1, total)


@router.message_callback(F.callback.payload == "hide_back_list")
async def back_hide_list(event: MessageCallback, context: MemoryContext,
                         product_service: IProductService):
    data = await context.get_data()
    page = data.get("page", 1)
    prods, total = await product_service.list_products(page)
    await _render_hide_list(event, prods, page, total)
