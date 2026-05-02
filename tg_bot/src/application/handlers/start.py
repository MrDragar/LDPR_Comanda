import logging

from aiogram import Router, types, filters, F
from aiogram.fsm.context import FSMContext

from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.application.keyboards.personal_data_keyboard import \
    get_personal_data_keyboard
from src.application.states import RegistrationStates

from src.application.keyboards.miniapp_keyboard import get_miniapp_keyboard
from src.services.interfaces import IUserService

router = Router(name=__name__)
start_command_router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message()
@start_command_router.message(filters.CommandStart())
@start_command_router.message(F.text == 'Отмена')
async def start(message: types.Message, user_service: IUserService,
                state: FSMContext):
    if message.chat.id <= 0:
        return
    if await user_service.is_user_exists(message.from_user.id):
        logging.debug(f"User {message.from_user.id} already exists")
        await message.reply(
            "Здравствуйте. Я, соколёнок Русик, интернет-помощник ЛДПР. Добро пожаловать в ЛДПР!"
        )
        await message.answer(
            'Используйте кнопку ниже, чтобы открыть наш сайт',
            reply_markup=get_miniapp_keyboard()
        )
        await message.answer("Меню", reply_markup=get_menu_keyboard())
        return

    logging.debug(f"User {message.from_user.id} Start conversation")

    await message.answer_sticker(types.FSInputFile('docs/sokol_stay.webp'))
    await message.reply(
        "Здравствуйте. Я, соколёнок Русик, интернет-помощник ЛДПР. Добро пожаловать в ЛДПР!"
    )

    await message.reply(
        "Для начала дайте согласие на обработку персональных данных",
        reply_markup=get_personal_data_keyboard())
    await state.set_state(RegistrationStates.personal_data)
