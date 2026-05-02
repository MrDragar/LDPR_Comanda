import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.keyboards.location_keyboard import get_location_keyboard
from src.application.states import UploadVideoStates

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(F.text == 'Загрузить видео')
async def ask_location(message: types.Message, state: FSMContext):
    await message.reply(
        "Для начала предоставьте вашу геолокацию",
        reply_markup=get_location_keyboard())
    await state.set_state(UploadVideoStates.location)


@router.message(UploadVideoStates.location, F.location)
async def get_location(message: types.Message, state: FSMContext):
    location = await message.location
    logger.debug(f"Got location {location}")
    await state.update_data(location=location)
    await state.set_state(UploadVideoStates.video)
    await message.reply(
        "Теперь отправьте ваше видео. Оно не может превышать 45 секунд и весить более 5 МБ",
        reply_markup=get_cancel_keyboard()
    )


@router.message(UploadVideoStates.location)
async def retry_location(message: types.Message, state: FSMContext):
    await message.reply(
        "Нажмите на кнопку на клавиатуре, чтобы предоставить нам вышу геолокацию",
        reply_markup=get_location_keyboard())
    await state.set_state(UploadVideoStates.location)
