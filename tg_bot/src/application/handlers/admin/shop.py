import io
import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.application.states import AdminShopStates
from src.domain.entities.user import UserRole, Sources
from src.domain.exceptions import DomainError
from src.services.interfaces import IProductService, IUserService
from src.application.filters import AdminFilter
from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name=__name__)


# ==================== ДОБАВИТЬ ТОВАР ====================
@router.message(F.text == "Добавить товар")
async def start_add(message: types.Message, state: FSMContext, user_service: IUserService):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    if role != UserRole.STAFF_CA: return await message.answer("Недостаточно прав")
    await message.answer("📝 Введите название товара:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminShopStates.add_name)

@router.message(AdminShopStates.add_name)
async def add_desc(message: types.Message, state: FSMContext, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]: return await _cancel_shop(message, state, user_service)
    await state.update_data(name=message.text.strip())
    await message.answer("📄 Введите описание товара:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminShopStates.add_desc)

@router.message(AdminShopStates.add_desc)
async def add_qty(message: types.Message, state: FSMContext, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]: return await _cancel_shop(message, state, user_service)
    await state.update_data(desc=message.text.strip())
    await message.answer("📦 Введите количество:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminShopStates.add_qty)

@router.message(AdminShopStates.add_qty)
async def add_price(message: types.Message, state: FSMContext, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]: return await _cancel_shop(message, state, user_service)
    try:
        qty = int(message.text.strip())
        if qty <= 0: raise ValueError
        await state.update_data(qty=qty)
        await message.answer("💰 Введите цену в баллах:", reply_markup=get_cancel_keyboard())
        await state.set_state(AdminShopStates.add_price)
    except ValueError:
        await message.answer("⚠️ Введите корректное число > 0", reply_markup=get_cancel_keyboard())


@router.message(AdminShopStates.add_price)
async def add_photo_prompt(message: types.Message, state: FSMContext, user_service: IUserService):
    if message.text and message.text in ["Отмена", "На главную"]: return await _cancel_shop(message, state, user_service)
    try:
        price = int(message.text.strip())
        if price <= 0: raise ValueError
        await state.update_data(price=price)
        await message.answer("🖼 Отправьте фотографию товара:", reply_markup=get_cancel_keyboard())
        await state.set_state(AdminShopStates.add_photo)
    except ValueError:
        await message.answer("⚠️ Введите корректное число > 0", reply_markup=get_cancel_keyboard())


async def _cancel_shop(message: types.Message, state: FSMContext, user_service: IUserService):
    await state.clear()
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    await message.answer("Добавление товара отменено.", reply_markup=get_role_menu_keyboard(role))


@router.message(AdminShopStates.add_photo, F.photo)
async def upload_photo(message: types.Message, state: FSMContext, product_service: IProductService,
                       bot: Bot, user_service: IUserService):
    data = await state.get_data()
    photo = message.photo[-1]

    try:
        # Скачиваем фото в байты
        file_info = await bot.get_file(photo.file_id)
        buffer = io.BytesIO()
        await bot.download_file(file_info.file_path, buffer)
        photo_bytes = buffer.getvalue()

        await product_service.create_product(
            name=data["name"], desc=data["desc"],
            price=data["price"], qty=data["qty"],
            photo_bytes=photo_bytes
        )
        await state.clear()
        role = await user_service.get_user_role(message.from_user.id, Sources.TG)
        await message.answer("✅ Товар успешно добавлен в магазин!",
                             reply_markup=get_role_menu_keyboard(role))
    except DomainError as e:
        await message.answer(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.error(f"Critical error in shop creation: {e}")
        await message.answer("❌ Произошла ошибка при создании товара.")


@router.message(AdminShopStates.add_photo, ~F.photo)
async def wait_photo(message: types.Message):
    if message.text and message.text in ["Отмена", "На главную"]: return await _cancel_shop(message, state, user_service)
    await message.answer("⚠️ Пожалуйста, отправьте именно фотографию.")


# ==================== СКРЫТЬ ТОВАР ====================
@router.message(F.text == "Скрыть товар")
async def start_hide(message: types.Message, product_service: IProductService,
                     user_service: IUserService, state: FSMContext):
    role = await user_service.get_user_role(message.from_user.id, Sources.TG)
    if role != UserRole.STAFF_CA:
        return await message.answer("Недостаточно прав")

    prods, total = await product_service.list_products(1)
    if not prods:
        return await message.answer("Нет активных товаров.")

    await state.update_data(page=1, total=total)
    await state.set_state(AdminShopStates.hide_browse)
    await _render_hide_list(message, prods, 1, total)


async def _render_hide_list(event: types.Message | types.CallbackQuery, prods, page, total,
                            is_callback=False):
    builder = InlineKeyboardBuilder()
    for p in prods:
        builder.button(text=f"- {p.name} (ост: {p.quantity})", callback_data=f"hide_view_{p.id}")
    builder.adjust(1)

    if total > 1:
        if page > 1: builder.button(text="⬅️", callback_data=f"hide_prev_{page}")
        if page < total: builder.button(text="➡️", callback_data=f"hide_next_{page}")

    text = "📦 Выберите товар для скрытия:"
    if is_callback:
        await event.message.answer(text, reply_markup=builder.as_markup())
    else:
        await event.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("hide_next_"), AdminShopStates.hide_browse)
async def next_hide(query: types.CallbackQuery, state: FSMContext,
                    product_service: IProductService):
    page = int(query.data.split("_")[-1])
    prods, total = await product_service.list_products(page)
    await state.update_data(page=page, total=total)
    await _render_hide_list(query, prods, page, total, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("hide_prev_"), AdminShopStates.hide_browse)
async def prev_hide(query: types.CallbackQuery, state: FSMContext,
                    product_service: IProductService):
    page = int(query.data.split("_")[-1])
    prods, total = await product_service.list_products(page)
    await state.update_data(page=page, total=total)
    await _render_hide_list(query, prods, page, total, is_callback=True)
    await query.answer()


@router.callback_query(F.data.startswith("hide_view_"), AdminShopStates.hide_browse)
async def confirm_hide(query: types.CallbackQuery):
    pid = int(query.data.split("_")[-1])
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Скрыть товар", callback_data=f"hide_execute_{pid}")
    builder.button(text="⬅️ Назад", callback_data="hide_back_list")
    builder.adjust(1)

    await query.message.answer("Вы уверены, что хотите скрыть этот товар?",
                               reply_markup=builder.as_markup())
    await query.answer()


@router.callback_query(F.data.startswith("hide_execute_"))
async def execute_hide(query: types.CallbackQuery, product_service: IProductService,
                       state: FSMContext):
    pid = int(query.data.split("_")[-1])
    await product_service.hide_product(pid)
    await query.message.answer("✅ Товар успешно скрыт.")

    # Возвращаем к списку
    prods, total = await product_service.list_products(1)
    await state.update_data(page=1, total=total)
    await _render_hide_list(query, prods, 1, total, is_callback=True)
    await query.answer()


@router.callback_query(F.data == "hide_back_list", AdminShopStates.hide_browse)
async def back_hide_list(query: types.CallbackQuery, state: FSMContext,
                         product_service: IProductService):
    data = await state.get_data()
    page = data.get("page", 1)
    prods, total = await product_service.list_products(page)
    await _render_hide_list(query, prods, page, total, is_callback=True)
    await query.answer()
