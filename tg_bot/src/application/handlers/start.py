import logging

from aiogram import Router, types, filters, F
from aiogram.fsm.context import FSMContext

from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.application.keyboards.personal_data_keyboard import \
    get_personal_data_keyboard
from src.application.states import RegistrationStates

from src.application.filters import IsParticipantFilter, IsRegisteredFilter, ValidatedStartFilter
from src.domain.entities import Sources
from src.services.interfaces import IReferralService

router = Router(name=__name__)
start_command_router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(IsRegisteredFilter())
@start_command_router.message(filters.CommandStart(), IsRegisteredFilter())
@start_command_router.message(F.text == 'Отмена', IsParticipantFilter())
async def participant_start(
        message: types.Message,
):
    if message.chat.id <= 0:
        return
    await message.reply(
        f"Бот находится на стадии разработки"
    )
    await message.answer("Меню", reply_markup=get_menu_keyboard())


@start_command_router.message(ValidatedStartFilter())
async def cmd_start(
        message: types.Message, user_id: int, platform: str,
        referral_service: IReferralService,
        state: FSMContext
):
    if message.chat.id <= 0:
        return
    logging.debug(f"Got referral: {user_id}, {platform}")
    await referral_service.activate_referral(
        user_id, Sources(platform),
        message.from_user.id, Sources.TG
    )
    await start(message, state)


@router.message()
@start_command_router.message(filters.CommandStart())
@start_command_router.message(F.text == 'Отмена')
async def start(message: types.Message,
                state: FSMContext):
    if message.chat.id <= 0:
        return
    logging.debug(f"User {message.from_user.id} Start conversation")

    await message.answer_sticker(types.FSInputFile('docs/sokol_stay.webp'))
    await message.reply(
        "Здравствуйте! Я — Соколёнок Русик, ваш цифровой помощник команды ЛДПР. 🦅\n"
        "Вы на шаг ближе к тому, чтобы стать частью большой команды, "
        "которая меняет страну к лучшему.\n\n"
        "Чтобы начать путь активиста, получать баллы за задания и "
        "участвовать в розыгрышах партии, нужно:\n"
        "✅ дать согласие на обработку данных\n"
        "✅ ответить на несколько простых вопросов о себе\n\n"
        "Это займёт не больше 2 минут. После регистрации вам откроются онлайн-задания, "
        "обучение и доступ в магазин подарков.\n\n"
        "Готовы? Давайте знакомиться!"
    )

    await message.reply(
        "Для начала дайте согласие на обработку персональных данных",
        reply_markup=get_personal_data_keyboard())
    await state.set_state(RegistrationStates.personal_data)
