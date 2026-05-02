from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import RegistrationStates
from src.services.interfaces import IUserService
from src.domain import exceptions

router = BotLabeler()


@router.message(state=RegistrationStates.EMAIL)
async def get_email(message: Message, user_service: IUserService,
                    state_dispenser: BuiltinStateDispenser):
    if not message.text: return

    try:
        email = await user_service.validate_email(message.text.strip())
        state = await state_dispenser.get(message.from_id)
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.REGION_BY_TEXT,
                                  **state.payload, email=email)
        await message.answer(
            "Укажите регион вашего проживания (начните вводить название):")
    except exceptions.EmailBadFormatError:
        return "Некорректный формат email. Введите почту заново"
    except exceptions.EmailAlreadyExistsError:
        return "Данный почтовый адрес уже зарегистрирован в системе"
    except:
        return "Неизвестная ошибка"
