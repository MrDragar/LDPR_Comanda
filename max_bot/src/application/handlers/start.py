import logging
import re
from maxapi import Router, Bot, F
from maxapi.types import MessageCreated, Command, BotStarted, InputMedia
from maxapi.context import MemoryContext
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.keyboards.personal_data_keyboard import get_personal_data_keyboard
from src.application.states import RegistrationStates
from src.domain.entities import Sources
from src.services.interfaces import IUserService, IReferralService, IActiveUserService

router = Router()
catch_all_router = Router()
logger = logging.getLogger(__name__)


def parse_start_payload(payload: str | None) -> tuple[int, Sources] | None:
    if not payload: return None
    match = re.search(r'(\d+)_(tg|vk|max)', str(payload))
    if match:
        return int(match.group(1)), Sources(match.group(2))
    return None


async def _start_logic(
        event, context: MemoryContext, bot: Bot, user_service: IUserService,
        referral_service: IReferralService, active_user_service: IActiveUserService,
        ref_payload: tuple[int, Sources] | None = None
):
    user_id = event.from_user.user_id if hasattr(event, 'from_user') else getattr(event.user,
                                                                                  'user_id', None)
    if not user_id: return

    try:
        await context.clear()
    except:
        pass

    await active_user_service.log_active_user(user_id, Sources.MAX)

    if ref_payload:
        try:
            await referral_service.activate_referral(ref_payload[0], ref_payload[1], user_id,
                                                     Sources.MAX)
        except Exception as e:
            logger.error(f"Referral error: {e}")

    if await user_service.is_user_exists(user_id, Sources.MAX):
        try:
            role = await user_service.get_user_role(user_id, Sources.MAX)
        except Exception:
            role = None
        await event.send("Главное меню:", attachments=[get_role_menu_keyboard(role).as_markup()])
        return

    try:
        media = InputMedia("docs/sokol_stay.webp")
        attachment = await bot.upload_media(media)
        await event.send(attachments=[attachment])
    except Exception as e:
        logger.error(f"Media upload error: {e}")

    await event.send(
        "Здравствуйте!\n"
        "Я — Соколёнок Русик, ваш цифровой помощник команды ЛДПР. 🦅\n"
        "Вы на шаг ближе к тому, чтобы стать частью большой команды, "
        "которая меняет страну к лучшему.\n"
        "Чтобы начать путь активиста, получать баллы за задания и "
        "участвовать в розыгрышах партии, нужно:\n"
        "✅ дать согласие на обработку данных\n"
        "✅ ответить на несколько простых вопросов о себе\n"
        "Это займёт не больше 2 минут. После регистрации вам откроются онлайн-задания, "
        "обучение и доступ в магазин подарков.\n"
        "Готовы? Давайте знакомиться!"
    )
    await event.send(
        "Для начала дайте согласие на обработку персональных данных",
        attachments=[get_personal_data_keyboard().as_markup()]
    )
    await context.set_state(RegistrationStates.PERSONAL_DATA)


@router.bot_started()
async def on_bot_started(event: BotStarted, context: MemoryContext, bot: Bot,
                         user_service: IUserService, referral_service: IReferralService,
                         active_user_service: IActiveUserService):
    payload = parse_start_payload(getattr(event, 'payload', None))
    await _start_logic(event, context, bot, user_service, referral_service, active_user_service,
                       payload)


@router.message_created(Command('start'))
@router.message_created(F.message.body.text.lower().in_(["начать", "заново"]))
async def on_start_message(event: MessageCreated, context: MemoryContext, bot: Bot,
                           user_service: IUserService, referral_service: IReferralService,
                           active_user_service: IActiveUserService):
    payload = None
    if hasattr(event, 'command') and hasattr(event.command, 'payload'):
        payload = parse_start_payload(event.command.payload)
    elif hasattr(event.message, 'payload'):
        payload = parse_start_payload(event.message.payload)
    await _start_logic(event, context, bot, user_service, referral_service, active_user_service,
                       payload)


@catch_all_router.message_created(lambda msg: True)
async def catch_all_handler(event: MessageCreated, context: MemoryContext, bot: Bot,
                            user_service: IUserService, referral_service: IReferralService,
                            active_user_service: IActiveUserService):
    state = await context.get_state()
    if state is not None:
        return
    await on_start_message(event, context, bot, user_service, referral_service, active_user_service)