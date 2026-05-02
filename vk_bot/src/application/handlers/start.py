import logging
from vkbottle.bot import BotLabeler, Message
from vkbottle import PhotoMessageUploader
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.keyboards.personal_data_keyboard import get_personal_data_keyboard
from src.application.keyboards.miniapp_keyboard import get_miniapp_keyboard
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService

router = BotLabeler()
start_command_router = BotLabeler()
logger = logging.getLogger(__name__)


@router.message()
@start_command_router.message(text=["Начать", "/start", "start", "начать", "Заново", "заново"])
async def start(
        message: Message, user_service: IUserService, 
        state_dispenser: BuiltinStateDispenser, photo_uploader: PhotoMessageUploader
):
    if message.peer_id < 0:
        return

    if await user_service.is_user_exists(message.from_id):
        await message.answer(
            "Здравствуйте. Я, соколёнок Русик, интернет-помощник ЛДПР. "
            "Добро пожаловать в ЛДПР! Вы уже зарегистрированы."
        )
        await message.answer(
            "Используйте кнопку ниже, чтобы открыть наш сайт",
            keyboard=get_miniapp_keyboard()
        )
        return
    photo = await photo_uploader.upload('docs/sokol_stay.webp', peer_id=message.peer_id)
    await message.answer(attachment=photo)
    await message.answer("Здравствуйте. Я, соколёнок Русик, интернет-помощник ЛДПР. Добро пожаловать в ЛДПР!")
    await message.answer("Если вы допустили ошибку при заполнении анкеты, напишите мне 'Заново' или 'Начать'")
    await message.answer(
        "Для начала дайте согласие на обработку персональных данных",
        keyboard=get_personal_data_keyboard()
    )
    await state_dispenser.set(message.from_id, RegistrationStates.PERSONAL_DATA)
