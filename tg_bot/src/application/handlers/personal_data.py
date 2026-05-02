import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.keyboards.personal_data_keyboard import \
    get_personal_data_keyboard
from src.application.states import RegistrationStates

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "pd_agree")
async def pd_agree(query: types.CallbackQuery, state: FSMContext):
    await query.message.reply('Вы являетесь членом ЛДПР?',
                              reply_markup=get_boolean_keyboard())
    await state.set_state(RegistrationStates.membership)


@router.callback_query(F.data == "pd_disagree")
async def pd_disagree(query: types.CallbackQuery, state: FSMContext):
    await query.message.reply(
        "Напишите любое сообщение для перезапуска разговора")
    await state.clear()


@router.callback_query(F.data == "pd_read")
async def pd_disagree(query: types.CallbackQuery, state: FSMContext):
    await query.message.reply_document(
        document=types.FSInputFile("docs/Согласие.docx"))
    await query.message.reply(
        "Для начала дайте согласие на обработку персональных данных",
        reply_markup=get_personal_data_keyboard()
    )
