from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService
from src.domain import exceptions

router = BotLabeler()


@router.message(state=RegistrationStates.PHONE)
async def get_phone(message: Message, user_service: IUserService,
                    state_dispenser: BuiltinStateDispenser):
    if not message.text: return

    try:
        phone = await user_service.validate_phone(message.text.strip())
        state = await state_dispenser.get(message.from_id)
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.EMAIL,
                                  **state.payload, phone=phone)
        await message.answer("Введите адрес вашей электронной почты:")
    except exceptions.PhoneBadFormatError:
        return "Некорректный формат. Пример: +79991234567"
    except exceptions.PhoneBadCountryError:
        return "К сожалению, мы поддерживаем работу только с российскими номерами. Попробуйте ввести другой номер телефона"
    except exceptions.PhoneAlreadyExistsError:
        return "Пользователь с данным номером телефона уже существует"
    except Exception as e:
        return "Неизвестная ошибка"
