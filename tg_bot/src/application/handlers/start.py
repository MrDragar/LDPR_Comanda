import logging

from aiogram import Router, types, filters, F
from aiogram.fsm.context import FSMContext

from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.application.keyboards.personal_data_keyboard import \
    get_personal_data_keyboard
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.states import RegistrationStates, ParticipateRegisteredStates

from src.application.filters import IsParticipantFilter, IsRegisteredFilter, ValidatedStartFilter
from src.domain.entities import Sources
from src.services.interfaces import IParticipationService, IReferralService

router = Router(name=__name__)
start_command_router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(IsParticipantFilter())
@start_command_router.message(filters.CommandStart(), IsParticipantFilter())
@start_command_router.message(F.text == 'Отмена', IsParticipantFilter())
async def participant_start(
        message: types.Message,
        participation_service: IParticipationService, referral_service: IReferralService,
):
    if message.chat.id <= 0:
        return
    id_count = len(await participation_service.get_all_participation_ids(
        message.from_user.id, Sources.TG
    ))
    referral_count = await referral_service.get_count_invitees(
        message.from_user.id, Sources.TG
    )
    await message.reply(
        f"Вы уже участвуете в нашем конкурсе.\n"
        f"Количество ваших номеров: {id_count}\n"
        f"Количество ваших рефералов: {referral_count}\n"
    )
    await message.answer("Меню", reply_markup=get_menu_keyboard())


@router.message(~IsParticipantFilter(), IsRegisteredFilter())
@start_command_router.message(filters.CommandStart(), ~IsParticipantFilter(), IsRegisteredFilter())
@start_command_router.message(F.text == 'Отмена', ~IsParticipantFilter(), IsRegisteredFilter())
async def registered_start(
        message: types.Message, state: FSMContext
):
    if message.chat.id <= 0:
        return
    await message.reply(
        f"Вы уже прошли анкетирование.\n"
        f"Хотите ли вы принять участие в конкурсе?",
        reply_markup=get_boolean_keyboard()
    )
    await state.set_state(ParticipateRegisteredStates.step)


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
        "Здравствуйте. Я, соколёнок Русик, интернет-помощник ЛДПР.\n"
        "Вы регистрируетесь в розыгрыше партии.\n"
        "Чтобы получить подарок, дайте согласие на обработку персональных данных и "
        "ответьте на несколько простых вопросов.\n\n"
        "Желаю удачи!"
    )

    await message.reply(
        "Для начала дайте согласие на обработку персональных данных",
        reply_markup=get_personal_data_keyboard())
    await state.set_state(RegistrationStates.personal_data)
