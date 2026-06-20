from maxapi import Router
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from src.application.states import RegistrationStates
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.application.handlers.auth_confirmation import request_auth_confirmation
from src.services.interfaces import INotificationService, IUserService
from src.domain import exceptions
from src.domain.entities import Sources

router = Router()


def _fio(user) -> str:
    return " ".join(part for part in [user.surname, user.name, user.patronymic] if part)


def _merge_data(user, state_data: dict, username: str | None = None) -> dict:
    return {
        **state_data,
        "username": username,
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
    users = [user for user in users if user.source != Sources.MAX]
    users.sort(key=lambda user: str(user.created_at or ""))
    return users[0] if users else None


@router.message_created(RegistrationStates.PHONE)
async def get_phone(event: MessageCreated, context: MemoryContext, user_service: IUserService):
    if not event.message.body.text: return
    try:
        phone = await user_service.validate_phone(event.message.body.text.strip())
        await context.update_data(phone=phone)
        same_phone_user = await _find_same_phone(user_service, phone)
        if same_phone_user is not None:
            await context.update_data(merge_user_id=same_phone_user.id, merge_source=same_phone_user.source.name)
            await context.set_state(RegistrationStates.MERGE_CONFIRM)
            await event.message.answer(
                f"Найден профиль {_fio(same_phone_user)} с таким же номером.\n"
                "Хотите объединить профили?",
                attachments=[get_boolean_keyboard().as_markup()]
            )
            return
        await context.set_state(RegistrationStates.SURNAME)
        await event.message.answer("Введите вашу фамилию:")
    except exceptions.PhoneBadFormatError:
        await event.message.answer("Некорректный формат. Пример: +79991234567")
    except exceptions.PhoneBadCountryError:
        await event.message.answer("К сожалению, мы поддерживаем работу только с российскими номерами. Попробуйте ввести другой номер телефона")
    except exceptions.PhoneAlreadyExistsError:
        await event.message.answer("Пользователь с данным номером телефона уже существует")
    except Exception:
        await event.message.answer("Неизвестная ошибка")


@router.message_created(RegistrationStates.MERGE_CONFIRM)
async def merge_confirm(
        event: MessageCreated,
        context: MemoryContext,
        user_service: IUserService,
        notification_service: INotificationService
):
    text = event.message.body.text.lower().strip() if event.message.body.text else ""
    if text not in ["да", "нет"]:
        await event.message.answer("Ответьте Да или Нет.", attachments=[get_boolean_keyboard().as_markup()])
        return
    if text == "нет":
        await context.set_state(RegistrationStates.PHONE)
        await event.message.answer("Введите другой номер телефона:")
        return
    data = await context.get_data()
    try:
        user = await user_service.get_user(int(data["merge_user_id"]), Sources[data["merge_source"]])
    except Exception:
        await context.set_state(RegistrationStates.PHONE)
        await event.message.answer("Профиль не найден. Введите другой номер телефона:")
        return
    if await request_auth_confirmation(
            user_service,
            notification_service,
            event.from_user.user_id,
            Sources.MAX,
            _merge_data(user, data, event.from_user.username if hasattr(event.from_user, 'username') else None)
    ):
        await context.set_state(RegistrationStates.AUTH_CODE)
        await event.message.answer(
            "Мы отправили код на найденный профиль. Введите его здесь, чтобы привязать эту площадку."
        )
        return
    await context.set_state(RegistrationStates.PHONE)
    await event.message.answer("Не удалось отправить подтверждение. Введите другой номер телефона:")
