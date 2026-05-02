from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.keyboards.gender_keyboard import get_gender_keyboard
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService
from src.domain import exceptions

router = BotLabeler()


@router.message(state=RegistrationStates.SURNAME)
async def get_surname(message: Message, user_service: IUserService,
                      state_dispenser: BuiltinStateDispenser):
    try:
        surname = await user_service.validate_fio_part(message.text.strip(),
                                                       'Фамилия')
        state = await state_dispenser.get(message.from_id)
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.NAME,
                                  **state.payload, surname=surname)
        await message.answer("Теперь введите ваше имя:")
    except exceptions.FioFormatError as e:
        return str(e)


@router.message(state=RegistrationStates.NAME)
async def get_name(message: Message, user_service: IUserService,
                   state_dispenser: BuiltinStateDispenser):
    try:
        name = await user_service.validate_fio_part(message.text.strip(), 'Имя')
        state = await state_dispenser.get(message.from_id)
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.PATRONYMIC,
                                  **state.payload, name=name)
        await message.answer(
            "Введите ваше отчество (если нет, отправьте '-' или 'нет'):")
    except exceptions.FioFormatError as e:
        return str(e)


@router.message(state=RegistrationStates.PATRONYMIC)
async def get_patronymic(message: Message, user_service: IUserService,
                         state_dispenser: BuiltinStateDispenser):
    val = message.text.strip()
    patronymic = None if val.lower() in ['-', 'нет', 'нету'] else val
    try:
        if patronymic:
            patronymic = await user_service.validate_fio_part(patronymic,
                                                              'Отчество')

        state = await state_dispenser.get(message.from_id)
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.GENDER,
                                  **state.payload,
                                  patronymic=patronymic)
        await message.answer("Укажите ваш пол:", keyboard=get_gender_keyboard())
    except exceptions.FioFormatError as e:
        await message.answer(str(e))
