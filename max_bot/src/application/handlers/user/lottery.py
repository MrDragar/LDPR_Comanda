import logging
from datetime import datetime
from maxapi import Router, F
from maxapi.types import MessageCreated, MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.context import MemoryContext
from src.application.states import LotteryStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.keyboards.gender_keyboard import get_gender_keyboard
from src.domain.entities.user import Sources
from src.domain import exceptions
from src.services.interfaces import IUserService, IParticipationService

logger = logging.getLogger(__name__)
router = Router()


def get_cancel_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="На главную"))
    return builder


def get_menu_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(MessageButton(text="Меню"))
    return builder


async def finish_lottery(
    event: MessageCreated, state_payload: dict, home_address: str | None,
    context: MemoryContext, user_service: IUserService, participation_service: IParticipationService
):
    try:
        await user_service.update_user_profile(
            user_id=event.from_user.user_id, source=Sources.MAX,
            birth_date=state_payload.get('birth_date'), email=state_payload.get('email'),
            gender=state_payload.get('gender'), city=state_payload.get('city'),
            wish_to_join=state_payload.get('wish_to_join', False),
            is_member=state_payload.get('is_member', False), home_address=home_address
        )
        p_id = await participation_service.activate_participation(event.from_user.user_id, Sources.MAX)
        await context.clear()
        await event.message.answer(
            f"🎉 Поздравляем! Вы успешно зарегистрированы для участия в розыгрыше!\n"
            f"Ваш уникальный номер: {p_id}Д\n"
            f"Сохраните его для проверки результатов.",
            attachments=[get_menu_kb().as_markup()]
        )
    except Exception as e:
        logger.error(f"Lottery finish error: {e}", exc_info=True)
        await event.message.answer(
            "❌ Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.",
            attachments=[get_menu_kb().as_markup()]
        )


@router.message_created(F.message.body.text == "Участие в розыгрыше")
async def lottery_intro(event: MessageCreated, participation_service: IParticipationService, user_service: IUserService):
    user = await user_service.get_user(event.from_user.user_id, Sources.MAX)
    is_participant = await participation_service.is_participant(event.from_user.user_id, Sources.MAX)
    if user.city and not is_participant:
        await participation_service.activate_participation(event.from_user.user_id, Sources.MAX)
        is_participant = True
    if is_participant:
        ids = await participation_service.get_all_participation_ids(event.from_user.user_id, Sources.MAX)
        nums = "\n".join([f"- {i}Д" for i in ids])
        return await event.message.answer(
            f"✅ Вы уже участвуете в розыгрыше!\nВаши уникальные номера:\n{nums}",
            attachments=[get_menu_kb().as_markup()]
        )
    kb = InlineKeyboardBuilder()
    kb.row(MessageButton(text="Пройти анкету"), MessageButton(text="На главную"))
    await event.message.answer(
        "🎁 Хотите принять участие в розыгрыше призов?\n"
        "Для этого нужно ответить на несколько дополнительных вопросов.\n"
        "Это займёт не больше минуты.",
        attachments=[kb.as_markup()]
    )


@router.message_created(F.message.body.text == "Пройти анкету")
async def start_lottery(event: MessageCreated, context: MemoryContext, participation_service: IParticipationService):
    is_participant = await participation_service.is_participant(event.from_user.user_id, Sources.MAX)
    if is_participant:
        return await event.message.answer("Вы уже приняли участие в розыгрыше", attachments=[get_menu_kb().as_markup()])
    await context.set_state(LotteryStates.IS_MEMBER)
    await event.message.answer("Вы являетесь членом ЛДПР?", attachments=[get_boolean_keyboard().as_markup()])


@router.message_created(LotteryStates.IS_MEMBER)
async def get_is_member(event: MessageCreated, context: MemoryContext):
    text = event.message.body.text.lower().strip() if event.message.body.text else ""
    if text == "на главную":
        await context.clear()
        return await event.message.answer("Главное меню", attachments=[get_menu_kb().as_markup()])
    if text not in ['да', 'нет']:
        return await event.message.answer("Пожалуйста, выберите вариант на клавиатуре:", attachments=[get_boolean_keyboard().as_markup()])
    await context.update_data(is_member=(text == 'да'))
    await context.set_state(LotteryStates.BIRTH_DATE)
    await event.message.answer("Введите вашу дату рождения в формате ДД.ММ.ГГГГ:", attachments=[get_cancel_kb().as_markup()])


@router.message_created(LotteryStates.BIRTH_DATE)
async def get_birth_date(event: MessageCreated, context: MemoryContext):
    if not event.message.body.text: return
    if event.message.body.text.strip().lower() == "на главную":
        await context.clear()
        return await event.message.answer("Главное меню", attachments=[get_menu_kb().as_markup()])
    try:
        birth_date = datetime.strptime(event.message.body.text.strip(), "%d.%m.%Y").date()
        now = datetime.now().date()
        age = now.year - birth_date.year - ((now.month, now.day) < (birth_date.month, birth_date.day))
        if birth_date > now: return await event.message.answer("Дата рождения не может быть в будущем.")
        if age > 120: return await event.message.answer("Введите корректную дату рождения.")
        await context.update_data(birth_date=birth_date)
        await context.set_state(LotteryStates.EMAIL)
        await event.message.answer("Введите адрес электронной почты (или '-' если нет):", attachments=[get_cancel_kb().as_markup()])
    except ValueError:
        await event.message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ", attachments=[get_cancel_kb().as_markup()])


@router.message_created(LotteryStates.EMAIL)
async def get_email(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    val = event.message.body.text.strip()
    if val.lower() == "на главную":
        await context.clear()
        return await event.message.answer("Главное меню", attachments=[get_menu_kb().as_markup()])
    email = None
    if val.lower() not in ['-', 'нет', 'нету', 'отсутствует']:
        try: email = await user_service.validate_email(val)
        except exceptions.EmailBadFormatError: return await event.message.answer("Некорректный формат email.", attachments=[get_cancel_kb().as_markup()])
        except exceptions.EmailAlreadyExistsError: return await event.message.answer("Почта уже зарегистрирована в системе.", attachments=[get_cancel_kb().as_markup()])
    await context.update_data(email=email)
    await context.set_state(LotteryStates.GENDER)
    await event.message.answer("Укажите ваш пол:", attachments=[get_gender_keyboard().as_markup()])


@router.message_created(LotteryStates.GENDER)
async def get_gender(event: MessageCreated, context: MemoryContext):
    gender = event.message.body.text.strip().lower() if event.message.body.text else ""
    if gender == "на главную":
        await context.clear()
        return await event.message.answer("Главное меню", attachments=[get_menu_kb().as_markup()])
    if gender not in ["мужской", "женский"]:
        return await event.message.answer("Выберите пол на клавиатуре:", attachments=[get_gender_keyboard().as_markup()])
    await context.update_data(gender=event.message.body.text)
    await context.set_state(LotteryStates.CITY)
    await event.message.answer("Укажите ваш город или населённый пункт:", attachments=[get_cancel_kb().as_markup()])


@router.message_created(LotteryStates.CITY)
async def get_city(event: MessageCreated, context: MemoryContext):
    if not event.message.body.text: return
    if event.message.body.text.strip().lower() == "на главную":
        await context.clear()
        return await event.message.answer("Главное меню", attachments=[get_menu_kb().as_markup()])
    city = event.message.body.text.strip()
    if len(city) < 2: return await event.message.answer("Введите корректное название города.", attachments=[get_cancel_kb().as_markup()])
    data = await context.get_data()
    p = data.copy()
    if p.get('is_member'):
        await context.update_data(city=city, wish_to_join=False)
        await context.set_state(LotteryStates.HOME_ADDRESS)
        await event.message.answer("Укажите свой домашний адрес:", attachments=[get_cancel_kb().as_markup()])
    else:
        await context.update_data(city=city)
        await context.set_state(LotteryStates.WISH_TO_JOIN)
        await event.message.answer("Хотите ли Вы вступить в партию ЛДПР?", attachments=[get_boolean_keyboard().as_markup()])


@router.message_created(LotteryStates.WISH_TO_JOIN)
async def get_wish(event: MessageCreated, context: MemoryContext, user_service: IUserService, participation_service: IParticipationService):
    text = event.message.body.text.lower().strip() if event.message.body.text else ""
    if text == "на главную":
        await context.clear()
        return await event.message.answer("Главное меню", attachments=[get_menu_kb().as_markup()])
    if text not in ['да', 'нет']:
        return await event.message.answer("Выберите вариант 'Да' или 'Нет':", attachments=[get_boolean_keyboard().as_markup()])
    wish_to_join = (text == 'да')
    data = await context.get_data()
    p = data.copy()
    if wish_to_join:
        await context.update_data(wish_to_join=wish_to_join)
        await context.set_state(LotteryStates.HOME_ADDRESS)
        await event.message.answer("Для возможности направления документов укажите свой домашний адрес:", attachments=[get_cancel_kb().as_markup()])
    else:
        await finish_lottery(event=event, state_payload={**p, 'wish_to_join': wish_to_join}, home_address=None, context=context, user_service=user_service, participation_service=participation_service)


@router.message_created(LotteryStates.HOME_ADDRESS)
async def get_home_address(event: MessageCreated, context: MemoryContext, user_service: IUserService, participation_service: IParticipationService):
    if not event.message.body.text: return
    if event.message.body.text.strip().lower() == "на главную":
        await context.clear()
        return await event.message.answer("Главное меню", attachments=[get_menu_kb().as_markup()])
    data = await context.get_data()
    p = data.copy()
    await finish_lottery(event=event, state_payload=p, home_address=event.message.body.text.strip(), context=context, user_service=user_service, participation_service=participation_service)
