import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from src.application.states import RegistrationStates
from src.application.handlers.auth_confirmation import request_auth_confirmation
from src.domain import exceptions
from src.domain.entities import Sources
from src.application.keyboards.boolean_keyboard import get_boolean_keyboard
from src.services.interfaces import INotificationService, IUserService

router = Router(name=__name__)
logger = logging.getLogger(__name__)


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
    users = [user for user in users if user.source != Sources.TG]
    users.sort(key=lambda user: str(user.created_at or ""))
    return users[0] if users else None


@router.message(RegistrationStates.phone)
async def get_phone_number(message: types.Message, state: FSMContext, user_service: IUserService):
    phone = message.text
    if not phone:
        return
    logger.debug(f"Got phone number {phone}")
    try:
        phone = await user_service.validate_phone(phone)
    except exceptions.PhoneBadFormatError:
        return message.reply("Некорректный формат телефона. Введите номер телефона в следующем формате: +79876543210")
    except exceptions.PhoneBadCountryError:
        return message.reply("К сожалению, мы поддерживаем работу только с российскими номерами. Попробуйте ввести другой номер телефона")
    except exceptions.PhoneAlreadyExistsError:
        return message.reply("Пользователь с данным номером телефона уже существует")
    except:
        return message.reply("Произошла неизвестная ошибка")
    await state.update_data(phone=phone)
    same_phone_user = await _find_same_phone(user_service, phone)
    if same_phone_user is not None:
        await state.update_data(merge_user_id=same_phone_user.id, merge_source=same_phone_user.source.name)
        await state.set_state(RegistrationStates.merge_confirm)
        await message.reply(
            f"Найден профиль {_fio(same_phone_user)} с таким же номером.\n"
            "Хотите объединить профили? Ответьте Да или Нет.",
            reply_markup=get_boolean_keyboard()
        )
        return
    await message.reply("Вы являетесь членом ЛДПР?", reply_markup=get_boolean_keyboard())
    await state.set_state(RegistrationStates.membership)


@router.message(RegistrationStates.merge_confirm)
async def merge_confirm(
        message: types.Message,
        state: FSMContext,
        user_service: IUserService,
        notification_service: INotificationService
):
    text = message.text.lower().strip() if message.text else ""
    if text not in ['да', 'нет']:
        await message.reply("Ответьте Да или Нет.", reply_markup=get_boolean_keyboard())
        return
    if text == "нет":
        await message.reply("Введите другой номер телефона:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(RegistrationStates.phone)
        return
    data = await state.get_data()
    try:
        user = await user_service.get_user(int(data["merge_user_id"]), Sources[data["merge_source"]])
    except Exception:
        await message.reply("Профиль не найден. Введите другой номер телефона:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(RegistrationStates.phone)
        return
    if await request_auth_confirmation(
            user_service,
            notification_service,
            message.from_user.id,
            Sources.TG,
            _merge_data(user, data, message.from_user.username)
    ):
        await state.set_state(RegistrationStates.auth_code)
        await message.reply(
            "Мы отправили код на найденный профиль. Введите его здесь, чтобы привязать эту площадку.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    await message.reply("Не удалось отправить подтверждение. Введите другой номер телефона:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(RegistrationStates.phone)
