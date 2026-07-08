import logging
import aiohttp
from maxapi import Router, F, Bot
from maxapi.types import MessageCreated, MessageCallback, CallbackButton, InputMedia, InputMediaBuffer
from maxapi.context import MemoryContext
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.keyboards.shop_keyboard import get_delivery_keyboard
from src.application.states import ShopStates
from src.domain.entities.user import Sources
from src.domain.exceptions import DomainError
from src.services.interfaces import IProductService, IOrderService, IBalanceService, IUserService, \
    INotificationService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()
ITEMS_PER_PAGE = 5


async def download_image(url: str) -> bytes | None:
    """Скачивает изображение по URL в байты."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning(f"Failed to download image {url}, status: {resp.status}")
    except Exception as e:
        logger.error(f"Error downloading image {url}: {e}")
    return None


async def _render_shop(event, prods, page, total, balance):
    builder = InlineKeyboardBuilder()
    for p in prods:
        builder.row(CallbackButton(text=f"- {p.name} - {p.price}б", payload=f"shop_view_{p.id}"))
    if total > 1:
        if page > 1: builder.row(CallbackButton(text="⬅️", payload=f"shop_prev_{page}"))
        if page < total: builder.row(CallbackButton(text="➡️", payload=f"shop_next_{page}"))
    text = f"💳 Ваш баланс: {balance} баллов.\n📦 Список доступных товаров (стр. {page}/{total}):"
    await event.message.answer(text, attachments=[builder.as_markup()])


# @router.message_created(F.message.body.text == "Магазин")
async def open_shop(event: MessageCreated, product_service: IProductService,
                    balance_service: IBalanceService, context: MemoryContext):
    bal = await balance_service.get_balance(event.from_user.user_id, Sources.MAX)
    prods, total = await product_service.list_products(1)
    if not prods:
        return await event.message.answer("Магазин временно пуст.")
    await context.update_data(page=1, total=total)
    await context.set_state(ShopStates.BROWSE)
    await _render_shop(event, prods, 1, total, bal)


@router.message_callback(F.callback.payload.startswith("shop_next_"))
async def next_shop(event: MessageCallback, context: MemoryContext,
                    product_service: IProductService, balance_service: IBalanceService):
    page = int(event.callback.payload.split("_")[-1])
    prods, total = await product_service.list_products(page)
    bal = await balance_service.get_balance(event.from_user.user_id, Sources.MAX)
    await context.update_data(page=page, total=total)
    await _render_shop(event, prods, page, total, bal)


@router.message_callback(F.callback.payload.startswith("shop_prev_"))
async def prev_shop(event: MessageCallback, context: MemoryContext,
                    product_service: IProductService, balance_service: IBalanceService):
    page = int(event.callback.payload.split("_")[-1])
    prods, total = await product_service.list_products(page)
    bal = await balance_service.get_balance(event.from_user.user_id, Sources.MAX)
    await context.update_data(page=page, total=total)
    await _render_shop(event, prods, page, total, bal)


@router.message_callback(F.callback.payload.startswith("shop_view_"))
async def view_prod(event: MessageCallback, product_service: IProductService,
                    context: MemoryContext, bot: Bot):
    pid = int(event.callback.payload.split("_")[-1])
    p = await product_service.get_product(pid)
    if not p:
        return await event.callback.answer("Товар не найден", show_alert=True)

    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🛒 Купить", payload=f"shop_buy_{pid}"))
    builder.row(CallbackButton(text="Назад", payload="shop_back_list"))
    caption = f"📌 {p.name}\n💰 {p.price} баллов\n📝 {p.description}"

    if p.image_url:
        try:
            image_bytes = await download_image(p.image_url)
            if image_bytes:
                media = InputMediaBuffer(image_bytes, filename="product.jpg")
                attachment = await bot.upload_media(media)
                await event.message.answer(text=caption,
                                           attachments=[attachment, builder.as_markup()])
            else:
                await event.message.answer(
                    caption + "\n⚠️ Не удалось загрузить изображение товара.",
                    attachments=[builder.as_markup()])
        except Exception as e:
            logger.error(f"Failed to upload product image: {e}")
            await event.message.answer(caption + "\n⚠️ Не удалось загрузить изображение товара.",
                                       attachments=[builder.as_markup()])
    else:
        await event.message.answer(caption, attachments=[builder.as_markup()])

    await event.callback.answer()


@router.message_callback(F.callback.payload == "shop_back_list")
async def back_shop_list(event: MessageCallback, context: MemoryContext,
                         product_service: IProductService, balance_service: IBalanceService):
    data = await context.get_data()
    page = data.get("page", 1)
    prods, total = await product_service.list_products(page)
    bal = await balance_service.get_balance(event.from_user.user_id, Sources.MAX)
    await _render_shop(event, prods, page, total, bal)


@router.message_callback(F.callback.payload.startswith("shop_buy_"))
async def start_buy(event: MessageCallback, balance_service: IBalanceService,
                    product_service: IProductService, context: MemoryContext):
    pid = int(event.callback.payload.split("_")[-1])
    p = await product_service.get_product(pid)
    bal = await balance_service.get_balance(event.from_user.user_id, Sources.MAX)
    if bal < p.price:
        await event.message.answer("⚠️ Вам не хватает средств для покупки этого товара.")
        return
    await context.update_data(pid=pid, price=p.price)
    await context.set_state(ShopStates.DELIVERY_CHOICE)
    await event.message.answer("🚚 Как вы хотите получить товар?",
                               attachments=[get_delivery_keyboard().as_markup()])


@router.message_created(ShopStates.DELIVERY_CHOICE, F.message.body.text == "По почте")
async def mail_addr(event: MessageCreated, context: MemoryContext):
    await event.message.answer("📍 Укажите адрес и индекс почтового отделения:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(ShopStates.MAIL_ADDR)


@router.message_created(ShopStates.MAIL_ADDR)
async def mail_fio(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        return await event.message.answer("Оформление отменено.",
                                          attachments=[get_role_menu_keyboard(role).as_markup()])
    await context.update_data(addr=event.message.body.text.strip())
    await event.message.answer("👤 Укажите ваше ФИО как в паспорте:",
                               attachments=[get_cancel_keyboard().as_markup()])
    await context.set_state(ShopStates.MAIL_FIO)


@router.message_created(ShopStates.MAIL_FIO)
async def finalize_mail(event: MessageCreated, context: MemoryContext, order_service: IOrderService,
                        notification_service: INotificationService,
                        balance_service: IBalanceService, user_service: IUserService):
    if event.message.body.text and event.message.body.text in ["Отмена", "На главную"]:
        await context.clear()
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        return await event.message.answer("Оформление отменено.",
                                          attachments=[get_role_menu_keyboard(role).as_markup()])
    data = await context.get_data()
    try:
        order = await order_service.create_order(event.from_user.user_id, Sources.MAX, data["pid"],
                                                 "mail", data["addr"],
                                                 event.message.body.text.strip())
        await notification_service.notify_user(event.from_user.user_id, Sources.MAX,
                                               f"✅ Заказ #{order.id} оформлен.")
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("📦 Отлично, начинаем оформлять посылку!",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        await context.clear()
    except DomainError as e:
        await event.message.answer(f"❌ Ошибка: {e}")


@router.message_created(ShopStates.DELIVERY_CHOICE, F.message.body.text == "Заберу лично")
async def pickup(event: MessageCreated, context: MemoryContext, user_service: IUserService,
                 order_service: IOrderService, notification_service: INotificationService):
    data = await context.get_data()
    u = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    addr = await user_service.get_region_address(u.region)
    try:
        order = await order_service.create_order(event.from_user.user_id, Sources.MAX, data["pid"],
                                                 "pickup", addr, None)
        await notification_service.notify_user(event.from_user.user_id, Sources.MAX,
                                               f"✅ Заказ #{order.id} оформлен. Заберите товар по адресу: {addr}")
        await event.message.answer(
            f"📍 Отлично, забрать товар можете на {addr} (Заказ #{order.id}).",
            attachments=[get_role_menu_keyboard(u.role).as_markup()])
        await context.clear()
    except DomainError as e:
        await event.message.answer(f"❌ Ошибка: {e}")


@router.message_created(ShopStates.DELIVERY_CHOICE, F.message.body.text == "Отмена")
async def cancel_buy(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    await context.clear()
    role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
    await event.message.answer("Покупка отменена.",
                               attachments=[get_role_menu_keyboard(role).as_markup()])
