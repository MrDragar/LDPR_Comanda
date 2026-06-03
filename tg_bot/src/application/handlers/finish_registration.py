from aiogram import types
from aiogram.fsm.context import FSMContext

from src.application.keyboards.menu_keyboard import get_menu_keyboard
from src.services.interfaces import IUserService, IParticipationService


async def finish_registration(
        user_service: IUserService, state: FSMContext, message: types.Message, 
        participation_service: IParticipationService, log_chat: str
):
    data = await state.get_data()
    is_member = data['is_member']
    surname = data['surname']
    name = data['name']
    patronymic = data['patronymic']
    gender = data['gender']
    birth_date = data['birth_date']
    phone = data['phone']
    email = data['email']
    region = data['region']
    city = data['city']
    wish_to_join = data.get('wish_to_join', False)
    home_address = data.get('home_address', None)
    news_subscription = data['news_subscription']

    if await user_service.is_user_exists(message.from_user.id):
        await state.clear()
        return await message.reply(f"Вы уже зарегистрировались.")

    user = await user_service.create_user(
        message.from_user.id, message.from_user.username,
        surname, name, is_member, patronymic, birth_date, phone, region, email,
        gender, city, wish_to_join, home_address, news_subscription
    )

    number = await participation_service.activate_participation(user.id, user.source)

    await message.answer_sticker(
        types.FSInputFile('docs/sokol_like.webp')
    )
    await message.answer(
        f"Поздравляем, вы успешно зарегистрированы.\n",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
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
""")




