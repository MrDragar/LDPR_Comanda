import logging
from datetime import datetime
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, Text
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import LotteryStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.keyboards.gender_keyboard import get_gender_keyboard
from src.domain.entities.user import Sources
from src.domain import exceptions
from src.services.interfaces import IUserService, IParticipationService

logger = logging.getLogger(__name__)
router = BotLabeler()


def get_cancel_kb():
    return Keyboard(one_time=True).add(Text("На главную")).get_json()


def get_menu_kb():
    return Keyboard(one_time=True).add(Text("Меню")).get_json()


async def finish_lottery(
        message: Message,
        state_payload: dict,
        home_address: str | None,
        state_dispenser: BuiltinStateDispenser,
        user_service: IUserService,
        participation_service: IParticipationService
):
    """Завершает анкету, обновляет профиль и регистрирует в розыгрыше."""
    try:
        # Обновляем профиль пользователя недостающими данными
        await user_service.update_user_profile(
            user_id=message.from_id,
            source=Sources.VK,
            birth_date=state_payload.get('birth_date'),
            email=state_payload.get('email'),
            gender=state_payload.get('gender'),
            city=state_payload.get('city'),
            wish_to_join=state_payload.get('wish_to_join', False),
            is_member=state_payload.get('is_member', False),
            home_address=home_address
        )

        # Активируем участие и получаем уникальный номер
        p_id = await participation_service.activate_participation(message.from_id, Sources.VK)
        await state_dispenser.delete(message.from_id)

        await message.answer(
            f"🎉 Поздравляем! Вы успешно зарегистрированы для участия в розыгрыше!\n\n"
            f"Ваш уникальный номер: {p_id}\n\n"
            f"Сохраните его для проверки результатов.",
            keyboard=get_menu_kb()
        )
    except Exception as e:
        logger.error(f"Lottery finish error: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.",
            keyboard=get_menu_kb()
        )


@router.message(text=["Участие в розыгрыше"])
async def lottery_intro(message: Message, participation_service: IParticipationService,
                        user_service: IUserService):
    user = await user_service.get_user(message.from_id, Sources.VK)
    is_participant = await participation_service.is_participant(message.from_id, Sources.VK)
    if user.city and not is_participant:
        await participation_service.activate_participation(message.from_id, Sources.VK)
        is_participant = True
    if is_participant:
        ids = await participation_service.get_all_participation_ids(message.from_id, Sources.VK)
        nums = "\n".join([f"- {i}" for i in ids])
        return await message.answer(
            f"✅ Вы уже участвуете в розыгрыше!\n\nВаши уникальные номера:\n{nums}",
            keyboard=get_menu_kb()
        )

    kb = Keyboard(one_time=True).add(Text("Пройти анкету")).add(Text("На главную")).get_json()
    await message.answer(
        "🎁 Хотите принять участие в розыгрыше призов?\n\n"
        "Для этого нужно ответить на несколько дополнительных вопросов.\n"
        "Это займёт не больше минуты.",
        keyboard=kb
    )


@router.message(text=["Пройти анкету"])
async def start_lottery(message: Message, state_dispenser: BuiltinStateDispenser,
                        participation_service: IParticipationService):
    is_participant = await participation_service.is_participant(message.from_id, Sources.VK)
    if is_participant:
        return await message.answer("Вы уже приняли участие в розыгрыше", keyboard=get_menu_kb())

    await state_dispenser.set(message.from_id, LotteryStates.IS_MEMBER)
    await message.answer("Вы являетесь членом ЛДПР?", keyboard=get_boolean_keyboard())


# ==================== ШАГИ АНКЕТЫ ====================

@router.message(state=LotteryStates.IS_MEMBER)
async def get_is_member(message: Message, state_dispenser: BuiltinStateDispenser):
    text = message.text.lower().strip() if message.text else ""
    if text == "на главную":
        await state_dispenser.delete(message.from_id)
        return await message.answer("Главное меню", keyboard=get_menu_kb())

    if text not in ['да', 'нет']:
        return await message.answer("Пожалуйста, выберите вариант на клавиатуре:",
                                    keyboard=get_boolean_keyboard())

    is_member = (text == 'да')
    await state_dispenser.set(message.from_id, LotteryStates.BIRTH_DATE, is_member=is_member)
    await message.answer("Введите вашу дату рождения в формате ДД.ММ.ГГГГ:",
                         keyboard=get_cancel_kb())


@router.message(state=LotteryStates.BIRTH_DATE)
async def get_birth_date(message: Message, state_dispenser: BuiltinStateDispenser):
    if not message.text: return
    if message.text.strip().lower() == "на главную":
        await state_dispenser.delete(message.from_id)
        return await message.answer("Главное меню", keyboard=get_menu_kb())

    try:
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        now = datetime.now().date()
        age = now.year - birth_date.year - (
                (now.month, now.day) < (birth_date.month, birth_date.day)
        )
        if birth_date > now:
            return await message.answer("Дата рождения не может быть в будущем.")
        if age > 120:
            return await message.answer("Введите корректную дату рождения.")
        state = await state_dispenser.get(message.from_id)
        await state_dispenser.set(message.from_id, LotteryStates.EMAIL, **state.payload,
                                  birth_date=birth_date)
        await message.answer("Введите адрес электронной почты (или '-' если нет):",
                             keyboard=get_cancel_kb())
    except ValueError:
        await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ", keyboard=get_cancel_kb())


@router.message(state=LotteryStates.EMAIL)
async def get_email(message: Message, user_service: IUserService,
                    state_dispenser: BuiltinStateDispenser):
    if not message.text: return
    val = message.text.strip()
    if val.lower() == "на главную":
        await state_dispenser.delete(message.from_id)
        return await message.answer("Главное меню", keyboard=get_menu_kb())

    email = None
    if val.lower() not in ['-', 'нет', 'нету', 'отсутствует']:
        try:
            email = await user_service.validate_email(val)
        except exceptions.EmailBadFormatError:
            return await message.answer("Некорректный формат email.", keyboard=get_cancel_kb())
        except exceptions.EmailAlreadyExistsError:
            return await message.answer("Почта уже зарегистрирована в системе.",
                                        keyboard=get_cancel_kb())

    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(message.from_id, LotteryStates.GENDER, **state.payload, email=email)
    await message.answer("Укажите ваш пол:", keyboard=get_gender_keyboard())


@router.message(state=LotteryStates.GENDER)
async def get_gender(message: Message, state_dispenser: BuiltinStateDispenser):
    gender = message.text.strip().lower() if message.text else ""
    if gender == "на главную":
        await state_dispenser.delete(message.from_id)
        return await message.answer("Главное меню", keyboard=get_menu_kb())

    if gender not in ["мужской", "женский"]:
        return await message.answer("Выберите пол на клавиатуре:", keyboard=get_gender_keyboard())

    state = await state_dispenser.get(message.from_id)
    await state_dispenser.set(message.from_id, LotteryStates.CITY, **state.payload,
                              gender=message.text)
    await message.answer("Укажите ваш город или населённый пункт:", keyboard=get_cancel_kb())


@router.message(state=LotteryStates.CITY)
async def get_city(message: Message, state_dispenser: BuiltinStateDispenser):
    if not message.text: return
    if message.text.strip().lower() == "на главную":
        await state_dispenser.delete(message.from_id)
        return await message.answer("Главное меню", keyboard=get_menu_kb())

    city = message.text.strip()
    if len(city) < 2:
        return await message.answer("Введите корректное название города.", keyboard=get_cancel_kb())

    state = await state_dispenser.get(message.from_id)
    p = state.payload

    if p.get('is_member'):
        await state_dispenser.set(message.from_id, LotteryStates.HOME_ADDRESS, **p, city=city,
                                  wish_to_join=False)
        await message.answer("Укажите свой домашний адрес:", keyboard=get_cancel_kb())
    else:
        await state_dispenser.set(message.from_id, LotteryStates.WISH_TO_JOIN, **p, city=city)
        await message.answer("Хотите ли Вы вступить в партию ЛДПР?",
                             keyboard=get_boolean_keyboard())


@router.message(state=LotteryStates.WISH_TO_JOIN)
async def get_wish(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
        user_service: IUserService,
        participation_service: IParticipationService
):
    text = message.text.lower().strip() if message.text else ""
    if text == "на главную":
        await state_dispenser.delete(message.from_id)
        return await message.answer("Главное меню", keyboard=get_menu_kb())

    if text not in ['да', 'нет']:
        return await message.answer("Выберите вариант 'Да' или 'Нет':",
                                    keyboard=get_boolean_keyboard())

    wish_to_join = (text == 'да')
    state = await state_dispenser.get(message.from_id)
    p = state.payload

    if wish_to_join:
        await state_dispenser.set(message.from_id, LotteryStates.HOME_ADDRESS, **p,
                                  wish_to_join=wish_to_join)
        await message.answer("Для возможности направления документов укажите свой домашний адрес:",
                             keyboard=get_cancel_kb())
    else:
        await finish_lottery(
            message=message,
            state_payload={**p, 'wish_to_join': wish_to_join},
            home_address=None,
            state_dispenser=state_dispenser,
            user_service=user_service,
            participation_service=participation_service
        )


@router.message(state=LotteryStates.HOME_ADDRESS)
async def get_home_address(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
        user_service: IUserService,
        participation_service: IParticipationService
):
    if not message.text: return
    if message.text.strip().lower() == "на главную":
        await state_dispenser.delete(message.from_id)
        return await message.answer("Главное меню", keyboard=get_menu_kb())

    state = await state_dispenser.get(message.from_id)
    p = state.payload

    # Завершаем анкету с передачей всех сервисов
    await finish_lottery(
        message=message,
        state_payload=p,
        home_address=message.text.strip(),
        state_dispenser=state_dispenser,
        user_service=user_service,
        participation_service=participation_service
    )