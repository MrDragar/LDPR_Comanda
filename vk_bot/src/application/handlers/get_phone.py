from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch import BuiltinStateDispenser
from src.application.states import RegistrationStates
from src.application.handlers.auth_confirmation import request_auth_confirmation
from src.services.interfaces import INotificationService, IUserService
from src.domain import exceptions
from src.domain.entities import Sources
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard

router = BotLabeler()


def _fio(user) -> str:
    return " ".join(part for part in [user.surname, user.name, user.patronymic] if part)


def _merge_data(user, state_data: dict) -> dict:
    return {
        **state_data,
        "username": None,
        "surname": user.surname,
        "name": user.name,
        "patronymic": user.patronymic,
        "is_member": user.is_member,
        "birth_date": user.birth_date,
        "phone": user.phone_number,
        "region": user.region,
        "email": user.email,
        "gender": user.gender,
        "city": user.city,
        "wish_to_join": user.wish_to_join,
        "home_address": user.home_address,
        "news_subscription": user.news_subscription,
        "merge_allowed": True,
        "merge_user_id": user.id,
        "merge_source": user.source.name,
    }


async def _find_same_phone(user_service: IUserService, phone: str):
    users = await user_service.search_users_by_phone(phone)
    users = [user for user in users if user.source != Sources.VK]
    users.sort(key=lambda user: str(user.created_at or ""))
    return users[0] if users else None


@router.message(state=RegistrationStates.PHONE)
async def get_phone(message: Message, user_service: IUserService,
                    state_dispenser: BuiltinStateDispenser):
    if not message.text: return

    try:
        phone = await user_service.validate_phone(message.text.strip())
        state = await state_dispenser.get(message.from_id)
        same_phone_user = await _find_same_phone(user_service, phone)
        if same_phone_user is not None:
            await state_dispenser.set(
                message.from_id,
                RegistrationStates.MERGE_CONFIRM,
                **state.payload,
                phone=phone,
                merge_user_id=same_phone_user.id,
                merge_source=same_phone_user.source.name
            )
            await message.answer(
                f"Найден профиль {_fio(same_phone_user)} с таким же номером.\n"
                "Хотите объединить профили? Ответьте Да или Нет.",
                keyboard=get_boolean_keyboard()
            )
            return
        await state_dispenser.set(message.from_id,
                                  RegistrationStates.MEMBERSHIP,
                                  **state.payload, phone=phone)
        await message.answer("Вы являетесь членом ЛДПР?", keyboard=get_boolean_keyboard())
    except exceptions.PhoneBadFormatError:
        return "Некорректный формат. Пример: +79991234567"
    except exceptions.PhoneBadCountryError:
        return "К сожалению, мы поддерживаем работу только с российскими номерами. Попробуйте ввести другой номер телефона"
    except exceptions.PhoneAlreadyExistsError:
        return "Пользователь с данным номером телефона уже существует"
    except Exception as e:
        return "Неизвестная ошибка"


@router.message(state=RegistrationStates.MERGE_CONFIRM)
async def merge_confirm(
        message: Message,
        state_dispenser: BuiltinStateDispenser,
        user_service: IUserService,
        notification_service: INotificationService
):
    text = message.text.lower().strip() if message.text else ""
    if text not in ['да', 'нет']:
        await message.answer("Ответьте Да или Нет.", keyboard=get_boolean_keyboard())
        return
    state = await state_dispenser.get(message.from_id)
    if text == "нет":
        await state_dispenser.set(message.from_id, RegistrationStates.PHONE, **state.payload)
        await message.answer("Введите другой номер телефона:")
        return
    try:
        user = await user_service.get_user(int(state.payload["merge_user_id"]), Sources[state.payload["merge_source"]])
    except Exception:
        await state_dispenser.set(message.from_id, RegistrationStates.PHONE, **state.payload)
        await message.answer("Профиль не найден. Введите другой номер телефона:")
        return
    if await request_auth_confirmation(
            user_service,
            notification_service,
            message.from_id,
            Sources.VK,
            _merge_data(user, state.payload)
    ):
        await state_dispenser.set(message.from_id, RegistrationStates.AUTH_CODE, **state.payload)
        await message.answer(
            "Мы отправили код на найденный профиль. Введите его здесь, чтобы привязать эту площадку."
        )
        return
    await state_dispenser.set(message.from_id, RegistrationStates.PHONE, **state.payload)
    await message.answer("Не удалось отправить подтверждение. Введите другой номер телефона:")
