import logging

from aiogram import types
from aiogram.fsm.context import FSMContext
from src.application.keyboards.menu_keyboard import get_role_menu_keyboard
from src.domain.entities import Sources
from src.services.interfaces import IUserService, IHeadlinerService


def normalize_fio(surname: str, name: str | None, patronymic: str | None) -> str:
    parts = [surname, name, patronymic]
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


def normalize_phone(phone_number: str | None) -> str:
    return "".join(symbol for symbol in (phone_number or "") if symbol.isdigit())


async def sync_headliner_role(
    user,
    user_service: IUserService,
    headliner_service: IHeadlinerService
):
    existing = await headliner_service.get_by_user(user.id, Sources.TG)
    if existing is not None:
        return await user_service.get_user_role(user.id, Sources.TG)

    user_fio = normalize_fio(user.surname, user.name, user.patronymic)
    user_phone = normalize_phone(user.phone_number)
    for headliner in await headliner_service.get_all():
        try:
            headliner_user = await user_service.get_user(headliner.user_id, headliner.user_source)
        except Exception:
            continue

        if normalize_phone(headliner_user.phone_number) != user_phone:
            continue
        if normalize_fio(headliner_user.surname, headliner_user.name, headliner_user.patronymic) != user_fio:
            continue

        await headliner_service.create_headliner(
            user_id=user.id,
            user_source=Sources.TG,
            fio=headliner.fio,
            position=headliner.position,
            topic=headliner.topic,
            group_link=headliner.group_link,
            photo=headliner.photo,
        )
        if headliner.welcome_message:
            await headliner_service.update_welcome_message_by_user(
                user.id,
                Sources.TG,
                headliner.welcome_message
            )
        return await user_service.get_user_role(user.id, Sources.TG)

    return user.role


async def finish_registration(
    user_service: IUserService, state: FSMContext, message: types.Message,
    log_chat: str, headliner_service: IHeadlinerService,
):
    data = await state.get_data()
    news_subscription = data['news_subscription']
    if await user_service.is_user_exists(message.from_user.id):
        await state.clear()
        return await message.reply(f"Вы уже зарегистрировались.")
    user = await user_service.create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        surname=data['surname'],
        name=data['name'],
        is_member=data['is_member'],
        patronymic=data.get('patronymic', None),
        birth_date=data['birth_date'],
        phone_number=data['phone'],
        region=data['region'],
        email=data['email'],
        gender=data['gender'],
        city=data['city'],
        wish_to_join=data.get('wish_to_join', False),
        home_address=data.get('home_address', None),
        news_subscription=data['news_subscription']
    )
    user_role = await sync_headliner_role(user, user_service, headliner_service)
    referral_headliner = None
    headliner_id: int | None = data.get("headliner_id", None)
    if headliner_id is not None and headliner_service is not None:
        try:
            await headliner_service.attach_follower(int(headliner_id), user.id, user.source)
            referral_headliner = await headliner_service.get_by_id(int(headliner_id))
        except Exception as e:
            logging.debug(f"Got Exception {e}")

    await message.answer_sticker(
        types.FSInputFile('docs/sokol_like.webp')
    )
    await message.answer(
        f"Поздравляем, вы успешно зарегистрированы.\n",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await message.answer("Приглашай друзей и получи 10 баллов за приглашённого пользователя.")
    if referral_headliner is not None and referral_headliner.welcome_message:
        await message.answer(
            f"Сообщение от хедлайнера {referral_headliner.fio}:\n\n"
            f"{referral_headliner.welcome_message}"
        )
    await message.answer("Меню", reply_markup=get_role_menu_keyboard(user_role))
    await state.clear()
    await message.bot.send_message(chat_id=log_chat, text=f"""
Новый пользователь {'@' + user.username if user.username else '<нет username>'} зарегистрировался.
Источник: ТГ
Является членом партии: {'Да' if user.is_member else 'Нет'}
ФИО: {user.surname} {user.name} {user.patronymic}
Пол: {user.gender}
Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}
Почта: {user.email}
Номер телефона: {user.phone_number}
Регион: {user.region}
Город: {user.city}
Хочет вступить в партию ЛДПР: {'Да' if user.wish_to_join else 'Нет'}
Домашний адрес: {user.home_address or 'не указан'}
Подписка на новости: {'Есть' if news_subscription else 'Нет'}
ID участника: {user.id}
Хедлайнер: {referral_headliner.fio if referral_headliner else 'Нет'}
""")
