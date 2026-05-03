import logging
import re

from vkbottle.bot import BotLabeler, Message
from vkbottle import PhotoMessageUploader
from vkbottle.dispatch import BuiltinStateDispenser

from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.application.keyboards.personal_data_keyboard import get_personal_data_keyboard
from src.application.states import RegistrationStates
from src.domain.entities import Sources
from src.services.interfaces import IUserService, IReferralService, IParticipationService

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
        participation_service: IParticipationService, referral_service: IReferralService
):
    if message.peer_id < 0:
        return
    if await participation_service.is_participant(message.peer_id, Sources.VK):
        id_count = len(await participation_service.get_all_participation_ids(
            message.peer_id, Sources.VK
        ))
        referral_count = await referral_service.get_count_invitees(
            message.peer_id, Sources.VK
        )
        await message.answer(
            f"Вы уже участвуете в нашем конкурсе.\n"
            f"Количество ваших номеров: {id_count}\n"
            f"Количество ваших рефералов: {referral_count}\n"
        )
        await message.answer("Меню", keyboard=get_menu_keyboard())
        return

    if await user_service.is_user_exists(message.from_id):
        await message.answer(
            f"Вы уже прошли анкетирование.\n"
            f"Хотите ли вы принять участие в конкурсе?",
            keyboard=get_boolean_keyboard()
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
        "Здравствуйте. Я, соколёнок Русик, интернет-помощник ЛДПР.\n"
        "Вы регистрируетесь в Новогоднем розыгрыше партии.\n"
        "Чтобы получить подарок, дайте согласие на обработку персональных данных и "
        "ответьте на несколько простых вопросов.\n\n"
        "Желаю удачи!"
    )
    await message.answer("Если вы допустили ошибку при заполнении анкеты, напишите мне 'Заново' или 'Начать'")
    await message.answer(
        "Для начала дайте согласие на обработку персональных данных",
        keyboard=get_personal_data_keyboard()
    )
    await state_dispenser.set(message.from_id, RegistrationStates.PERSONAL_DATA)
