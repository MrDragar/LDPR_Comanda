import logging
import aiohttp
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.states import ShopStates
from src.domain.entities.user import Sources
from src.domain.exceptions import DomainError
from src.services.interfaces import IProductService, IOrderService, IBalanceService, IUserService, INotificationService
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)

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


def get_delivery_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="По почте"), KeyboardButton(text="Заберу лично")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def _render_shop(event: types.Message | types.CallbackQuery, prods, page, total, balance, is_callback=False):
    builder = InlineKeyboardBuilder()
    for p in prods:
        builder.button(text=f"- {p.name} - {p.price}б", callback_data=f"shop_view_{p.id}")
    builder.adjust(1)

    if total > 1:
        if page > 1: builder.button(text="⬅️", callback_data=f"shop_prev_{page}")
        if page < total: builder.button(text="➡️", callback_data=f"shop_next_{page}")

    text = f"💳 Ваш баланс: {balance} баллов.\n📦 Список доступных товаров (стр. {page}/{total}):"
    if is_callback:
        await event.message.answer(text, reply_markup=builder.as_markup())
    else:
        await event.answer(text, reply_markup=builder.as_markup())


# @router.message(F.text == "Магазин")
async def open_shop(message: types.Message, product_service: IProductService, balance_service: IBalanceService, state: FSMContext):
    bal = await balance_service.get_balance(message.from_user.id, Sources.TG)
    prods, total = await product_service.list_products(1)
    if not prods:
        return await message.answer("Магазин временно пуст.")

    await state.update_data(page=1, total=total)
    await state.set_state(ShopStates.browse)
    await _render_shop(message, prods, 1, total, bal)


@router.callback_query(F.data.startswith("shop_next_"), ShopStates.browse)
async def next_shop(query: types.CallbackQuery, state: FSMContext, product_service: IProductService, balance_service: IBalanceService):
    page = int(query.data.split("_")[-1])
    prods, total = await product_service.list_products(page)
    bal = await balance_service.get_balance(query.from_user.id, Sources.TG)
    await state.update_data(page=page, total=total)
    await _render_shop(query, prods, page, total, bal, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("shop_prev_"), ShopStates.browse)
async def prev_shop(query: types.CallbackQuery, state: FSMContext, product_service: IProductService, balance_service: IBalanceService):
    page = int(query.data.split("_")[-1])
    prods, total = await product_service.list_products(page)
    bal = await balance_service.get_balance(query.from_user.id, Sources.TG)
    await state.update_data(page=page, total=total)
    await _render_shop(query, prods, page, total, bal, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("shop_view_"), ShopStates.browse)
async def view_prod(query: types.CallbackQuery, product_service: IProductService, state: FSMContext, bot: Bot):
    pid = int(query.data.split("_")[-1])
    p = await product_service.get_product(pid)
    if not p:
        return await query.answer("Товар не найден", show_alert=True)

    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить", callback_data=f"shop_buy_{pid}")
    builder.button(text="Назад", callback_data="shop_back_list")
    builder.adjust(1)

    caption = f"📌 {p.name}\n💰 {p.price} баллов\n📝 {p.description}"

    # ИСПРАВЛЕНО: скачиваем картинку в память и отправляем как файл
    if p.image_url:
        image_bytes = await download_image(p.image_url)
        if image_bytes:
            # Оборачиваем байты в BufferedInputFile, чтобы aiogram отправил их как загруженный файл
            photo_file = BufferedInputFile(image_bytes, filename="product.jpg")
            await query.message.answer_photo(
                photo=photo_file,
                caption=caption,
                reply_markup=builder.as_markup()
            )
        else:
            # Если скачать не удалось (например, отвалился интернет или VK Cloud недоступен),
            # отправляем хотя бы текст, чтобы не ломать UX
            await query.message.answer(
                caption + "\n\n⚠️ Не удалось загрузить изображение товара.",
                reply_markup=builder.as_markup()
            )
    else:
        await query.message.answer(caption, reply_markup=builder.as_markup())

    await query.answer()


@router.callback_query(F.data == "shop_back_list", ShopStates.browse)
async def back_shop_list(query: types.CallbackQuery, state: FSMContext, product_service: IProductService, balance_service: IBalanceService):
    data = await state.get_data()
    page = data.get("page", 1)
    prods, total = await product_service.list_products(page)
    bal = await balance_service.get_balance(query.from_user.id, Sources.TG)
    await _render_shop(query, prods, page, total, bal, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("shop_buy_"))
async def start_buy(query: types.CallbackQuery, balance_service: IBalanceService, product_service: IProductService, state: FSMContext):
    pid = int(query.data.split("_")[-1])
    p = await product_service.get_product(pid)
    bal = await balance_service.get_balance(query.from_user.id, Sources.TG)

    if bal < p.price:
        await query.message.answer("⚠️ Вам не хватает средств для покупки этого товара.")
        return await query.answer()

    await state.update_data(pid=pid, price=p.price)
    await state.set_state(ShopStates.delivery_choice)
    await query.message.answer("🚚 Как вы хотите получить товар?", reply_markup=get_delivery_keyboard())
    await query.answer()


@router.message(ShopStates.delivery_choice, F.text == "По почте")
async def mail_addr(message: types.Message, state: FSMContext):
    await message.answer("📍 Укажите адрес и индекс почтового отделения:", reply_markup=get_cancel_keyboard())
    await state.set_state(ShopStates.mail_addr)


@router.message(ShopStates.mail_addr)
async def mail_fio(message: types.Message, state: FSMContext, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]:
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        return await message.answer("Оформление отменено.", reply_markup=get_role_menu_keyboard(role))
    await state.update_data(addr=message.text.strip())
    await message.answer("👤 Укажите ваше ФИО как в паспорте:", reply_markup=get_cancel_keyboard())
    await state.set_state(ShopStates.mail_fio)

@router.message(ShopStates.mail_fio)
async def finalize_mail(message: types.Message, state: FSMContext, order_service: IOrderService, notification_service: INotificationService, balance_service: IBalanceService, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]:
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        return await message.answer("Оформление отменено.", reply_markup=get_role_menu_keyboard(role))

    data = await state.get_data()
    try:
        order = await order_service.create_order(message.from_user.id, Sources.TG, data["pid"], "mail", data["addr"], message.text.strip())
        await notification_service.notify_user(message.from_user.id, Sources.TG, f"✅ Заказ #{order.id} оформлен.")
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        await message.answer("📦 Отлично, начинаем оформлять посылку!", reply_markup=get_role_menu_keyboard(role))
        await state.clear()
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(ShopStates.delivery_choice, F.text == "Заберу лично")
async def pickup(message: types.Message, state: FSMContext, user_service: IUserService, order_service: IOrderService, notification_service: INotificationService, ):
    data = await state.get_data()
    u = await user_service.get_user(message.from_user.id, Sources.TG)
    addr = await user_service.get_region_address(u.region)

    try:
        order = await order_service.create_order(message.from_user.id, Sources.TG, data["pid"], "pickup", addr, None)
        await notification_service.notify_user(message.from_user.id, Sources.TG, f"✅ Заказ #{order.id} оформлен. Заберите товар по адресу: {addr}")
        await message.answer(f"📍 Отлично, забрать товар можете на {addr} (Заказ #{order.id}).", reply_markup=get_role_menu_keyboard(u.role))
        await state.clear()
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(ShopStates.delivery_choice, F.text == "Отмена")
async def cancel_buy(message: types.Message, state: FSMContext, user_service: IUserService):
    await state.clear()
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Покупка отменена.", reply_markup=get_role_menu_keyboard(role))