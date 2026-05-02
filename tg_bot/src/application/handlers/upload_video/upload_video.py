import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.application.keyboards.cancel_keyboard import get_cancel_keyboard
from src.application.keyboards.location_keyboard import get_location_keyboard
from src.application.states import UploadVideoStates

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.message(UploadVideoStates.video, F.video)
async def upload_video(message: types.Message, state: FSMContext):
    if message.video.file_size > 5 * 1024 * 1024:
        await message.answer(
            "❌ Видео слишком большое. Максимальный размер - 5 МБ.\n"
            "Пожалуйста, отправьте другое видео."
        )
        return
    if message.video.duration > 45:
        await message.answer(
            f"❌ Длительность видео слишком большая: {message.video.duration} секунд.\n"
            "Максимальная длительность - 45 секунд.\n"
            "Пожалуйста, отправьте другое видео."
        )
        return
    data = await state.get_data()
    location: types.Location = data['location']
    file_info = await message.bot.get_file(message.video.file_id)
    file_content = await message.bot.download_file(file_info.file_path)
    video_bytes = file_content.read()

    await state.set_state(UploadVideoStates.location)


@router.message(UploadVideoStates.video)
async def wrong_input(message: types.Message, state: FSMContext):
    await message.reply("Отправьте, пожалуйста, видео", reply_markup=get_cancel_keyboard())
