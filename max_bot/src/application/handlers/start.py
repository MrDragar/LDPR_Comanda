import logging
import re
from maxapi import Router, Bot, F
from maxapi.types import MessageCreated, Command, BotStarted, InputMedia
from maxapi.context import MemoryContext
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.application.keyboards.personal_data_keyboard import get_personal_data_keyboard
from src.application.states import RegistrationStates
from src.domain.entities import Sources
from src.services.interfaces import IUserService, IReferralService, IActiveUserService, \
    IHeadlinerService

router = Router()
catch_all_router = Router()
logger = logging.getLogger(__name__)


async def _handle_start_payload(event, context: MemoryContext, bot: Bot, payload: str | None,
                                user_service: IUserService, referral_service: IReferralService,
                                active_user_service: IActiveUserService,
                                headliner_service: IHeadlinerService):
    user_id = event.from_user.user_id if hasattr(event, 'from_user') else getattr(event.user,
                                                                                  'user_id', None)
    if not user_id: return

    await context.clear()
    await active_user_service.log_active_user(user_id, Sources.MAX)

    headliner_id = None
    if payload:
        # Проверка на реферальную ссылку
        match_ref = re.search(r'^(\d+)_(tg|vk|max)$', payload)
        if match_ref:
            try:
                await referral_service.activate_referral(int(match_ref.group(1)),
                                                         Sources(match_ref.group(2)), user_id,
                                                         Sources.MAX)
            except Exception as e:
                logger.error(f"Referral error: {e}")

        # Проверка на хедлайнера
        match_hl = re.search(r'^hl_(\d+)_(tg|vk|max)$', payload)
        if match_hl:
            headliner_id = int(match_hl.group(1))

    if headliner_id:
        await context.update_data(headliner_id=headliner_id)

    if await user_service.is_user_exists(user_id, Sources.MAX):
        role = await user_service.get_user_role(user_id, Sources.MAX)
        await event.message.answer("Главное меню:",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])
        return

    try:
        media = InputMedia("docs/sokol_stay.webp")
        attachment = await bot.upload_media(media)
        await event.message.answer(attachments=[attachment])
    except Exception as e:
        logger.error(f"Media upload error: {e}")

    await event.message.answer(
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
    await event.message.answer(
        "Для начала дайте согласие на обработку персональных данных",
        attachments=[get_personal_data_keyboard().as_markup()]
    )
    await context.set_state(RegistrationStates.PERSONAL_DATA)


@router.bot_started()
async def on_bot_started(event: BotStarted, context: MemoryContext, bot: Bot,
                         user_service: IUserService, referral_service: IReferralService,
                         active_user_service: IActiveUserService,
                         headliner_service: IHeadlinerService):
    payload = getattr(event, 'payload', None)
    await _handle_start_payload(event, context, bot, payload, user_service, referral_service,
                                active_user_service, headliner_service)


@router.message_created(Command('start'))
async def on_start_message(event: MessageCreated, context: MemoryContext, bot: Bot,
                           user_service: IUserService, referral_service: IReferralService,
                           active_user_service: IActiveUserService,
                           headliner_service: IHeadlinerService):
    payload = event.command.payload if (hasattr(event, 'command') and
                                        hasattr(event.command,'payload')) else None
    await _handle_start_payload(event, context, bot, payload, user_service, referral_service,
                                active_user_service, headliner_service)


@router.message_created(F.message.body.text.lower().in_(["отмена", "на главную"]))
async def cancel_handler(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    await context.clear()
    if await user_service.is_user_exists(event.from_user.user_id, Sources.MAX):
        role = await user_service.get_user_role(event.from_user.user_id, Sources.MAX)
        await event.message.answer("Главное меню:",
                                   attachments=[get_role_menu_keyboard(role).as_markup()])


@catch_all_router.message_created()
async def catch_all_handler(event: MessageCreated, context: MemoryContext, bot: Bot,
                            user_service: IUserService, referral_service: IReferralService,
                            active_user_service: IActiveUserService, headliner_service: IHeadlinerService):
    state = await context.get_state()
    if state is not None:
        return
    await on_start_message(event, context, bot, user_service, referral_service, active_user_service, headliner_service)
    