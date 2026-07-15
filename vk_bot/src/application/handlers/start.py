import logging
import re

from vkbottle.bot import BotLabeler, Message
from vkbottle import PhotoMessageUploader
from vkbottle.dispatch import BuiltinStateDispenser
from vkbottle_types import GroupTypes
from vkbottle_types.events import GroupEventType

from src.application.filters import CMDRule
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.keyboards.personal_data_keyboard import get_personal_data_keyboard
from src.application.keyboards.start_choice_keyboard import get_start_choice_keyboard
from src.application.states import RegistrationStates
from src.domain.entities import Sources
from src.services.interfaces import IUserService, IReferralService, IActiveUserService, IHeadlinerService

router = BotLabeler()
start_command_router = BotLabeler()
logger = logging.getLogger(__name__)


def parse_ref(ref: str) -> tuple[int, Sources] | None:
    pattern = re.compile(r'^(\d+)_(tg|vk|max)$')
    match = pattern.match(ref)
    if match:
            return int(match.group(1)), Sources(match.group(2))


def parse_headliner_ref(ref: str) -> tuple[int, Sources] | None:
    pattern = re.compile(r'^hl_(\d+)_(tg|vk|max)$')
    match = pattern.match(ref)
    if match:
        return int(match.group(1)), Sources(match.group(2))


@router.message(from_chat=True)
async def hello_handler(message: Message):
    ...


@router.message()
@start_command_router.message(text=["Начать", "/start", "start", "начать", "Заново", "заново"])
async def start(
        message: Message, user_service: IUserService, 
        state_dispenser: BuiltinStateDispenser, photo_uploader: PhotoMessageUploader,
        referral_service: IReferralService, active_user_service: IActiveUserService,
        headliner_service: IHeadlinerService
):
    if message.peer_id < 0:
        return
    try:
        await state_dispenser.delete(message.from_id)
    except:
        ...
    await active_user_service.log_active_user(message.from_id, Sources.VK)
    if await user_service.is_user_exists(message.from_id):
        try:
            role = await user_service.get_user_role(message.from_id, Sources.VK)
        except Exception:
            role = None
        await message.answer("Главное меню:", keyboard=get_role_menu_keyboard(role))
        return
    headliner_ref = None
    if message.ref:
        headliner_ref = parse_headliner_ref(message.ref)
        if headliner_ref is not None:
            headliner = await headliner_service.get_by_id(headliner_ref[0])
            if headliner is None:
                headliner_ref = None

    if message.ref and headliner_ref is None:
        parsed_ref = parse_ref(message.ref)
        if parsed_ref is not None:
            await referral_service.activate_referral(
                parsed_ref[0], parsed_ref[1],
                message.peer_id, Sources.VK
            )
    try:
        photo = await photo_uploader.upload('docs/sokol_stay.webp', peer_id=message.peer_id)
        await message.answer(attachment=photo)
    except:
        ...
    await message.answer(
        "Здравствуйте!\nЯ — Соколёнок Русик, ваш цифровой помощник команды ЛДПР. 🦅\n"
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
    await message.answer(
        "Если вы допустили ошибку при заполнении анкеты, напишите мне 'Заново' или 'Начать'")

    payload = {}
    if headliner_ref is not None:
        payload = {
            "headliner_id": headliner_ref[0],
            "headliner_source": headliner_ref[1].value
        }

    await state_dispenser.set(message.from_id, RegistrationStates.REGISTRATION_CHOICE, **payload)

    await message.answer(
        "👇 Выберите удобный способ регистрации:",
        keyboard=get_start_choice_keyboard()
    )


@router.raw_event(GroupEventType.MESSAGE_EVENT, GroupTypes.MessageEvent,
                  CMDRule("start_text_reg"))
async def handle_start_text_reg(event: GroupTypes.MessageEvent,
                                state_dispenser: BuiltinStateDispenser):
    state = await state_dispenser.get(event.object.peer_id)
    if not state or state.state != str(RegistrationStates.REGISTRATION_CHOICE):
        await event.ctx_api.messages.send_message_event_answer(
            event_id=event.object.event_id, user_id=event.object.user_id,
            peer_id=event.object.peer_id
        )
        return

    await state_dispenser.set(event.object.peer_id, RegistrationStates.PERSONAL_DATA,
                              **state.payload)
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message="Если вы допустили ошибку при заполнении анкеты, напишите мне 'Заново' или 'Начать'",
        random_id=0
    )
    await event.ctx_api.messages.send(
        peer_id=event.object.peer_id,
        message="Для начала дайте согласие на обработку персональных данных",
        keyboard=get_personal_data_keyboard(),
        random_id=0
    )

    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id, user_id=event.object.user_id,
        peer_id=event.object.peer_id
    )

