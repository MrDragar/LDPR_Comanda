import logging
import re

from vkbottle.bot import BotLabeler, Message
from vkbottle import PhotoMessageUploader
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.keyboards.personal_data_keyboard import get_personal_data_keyboard
from src.application.states import RegistrationStates
from src.domain.entities import Sources
from src.services.interfaces import IUserService, IReferralService

router = BotLabeler()
start_command_router = BotLabeler()
logger = logging.getLogger(__name__)


def parse_ref(ref: str) -> tuple[int, Sources] | None:
    pattern = re.compile(r'^(\d+)_(tg|vk|max)$')
    match = pattern.match(ref)
    if match:
        return int(match.group(1)), Sources(match.group(2))


@router.message()
@start_command_router.message(text=["Начать", "/start", "start", "начать", "Заново", "заново"])
async def start(
        message: Message, user_service: IUserService, 
        state_dispenser: BuiltinStateDispenser, photo_uploader: PhotoMessageUploader,
        referral_service: IReferralService
):
    if message.peer_id < 0:
        return
    if await user_service.is_user_exists(message.from_id):
        await message.answer(
            "Бот находится на стадии разработки"
        )
        return
    if message.ref:
        parsed_ref = parse_ref(message.ref)
        if parsed_ref is not None:
            await referral_service.activate_referral(
                parsed_ref[0], parsed_ref[1],
                message.peer_id, Sources.VK
            )

    photo = await photo_uploader.upload('docs/sokol_stay.webp', peer_id=message.peer_id)
    await message.answer(attachment=photo)
    await message.answer(
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
    await message.answer("Если вы допустили ошибку при заполнении анкеты, напишите мне 'Заново' или 'Начать'")
    await message.answer(
        "Для начала дайте согласие на обработку персональных данных",
        keyboard=get_personal_data_keyboard()
    )
    await state_dispenser.set(message.from_id, RegistrationStates.PERSONAL_DATA)
